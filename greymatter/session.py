#!/usr/bin/env python3
"""
Session Lifecycle Manager - 4-phase session management

Phases:
1. SessionStart - Load ledger, handoff, surface learnings
2. Working - Process prompts, track tools, collect learnings
3. PreCompact - Auto-handoff creation, save state before context loss
4. SessionEnd - Mark outcomes, extract learnings, cleanup

This ensures continuity across sessions by explicitly managing state
rather than relying on lossy context compaction.
"""

import os
import re
from pathlib import Path
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SessionPhase(Enum):
    """Session lifecycle phases"""
    SESSION_START = "session_start"
    WORKING = "working"
    PRE_COMPACT = "pre_compact"
    SESSION_END = "session_end"


@dataclass
class SessionState:
    """Current session state"""
    session_id: str
    ai_type: str
    phase: SessionPhase
    working_dir: str
    started_at: datetime
    prompt_count: int = 0
    tool_count: int = 0
    learnings: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    artifacts: List[Dict] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


class SessionManager:
    """Manages session lifecycle"""

    # Patterns for extracting learnings from AI output
    LEARNING_PATTERNS = [
        r"(?:Key )?[Ll]earning[s]?:\s*(.+?)(?:\n|$)",
        r"(?:Key )?[Ii]nsight[s]?:\s*(.+?)(?:\n|$)",
        r"[Dd]iscovered[:\s]+(.+?)(?:\n|$)",
        r"[Nn]ot(?:ed?|ing)[:\s]+(.+?)(?:\n|$)",
        r"[Rr]emember(?:ing)?[:\s]+(.+?)(?:\n|$)",
        r"I(?:'ll| will) remember[:\s]+(.+?)(?:\n|$)",
        r"[Ss]aving to memory[:\s]+(.+?)(?:\n|$)",
        r"[Ii]mportant[:\s]+(.+?)(?:\n|$)",
    ]

    # Patterns for extracting decisions
    DECISION_PATTERNS = [
        r"[Dd]ecided to[:\s]+(.+?)(?:\n|$)",
        r"[Cc]hose to[:\s]+(.+?)(?:\n|$)",
        r"[Oo]pted for[:\s]+(.+?)(?:\n|$)",
        r"[Gg]oing with[:\s]+(.+?)(?:\n|$)",
        r"[Ss]elected[:\s]+(.+?)(?:\n|$)",
    ]

    def __init__(self):
        self.current_session: Optional[SessionState] = None
        self.phase_handlers: Dict[SessionPhase, List[Callable]] = {
            phase: [] for phase in SessionPhase
        }

    def start_session(self, ai_type: str, working_dir: str = None) -> SessionState:
        """Start a new session - Phase 1: SessionStart"""
        from .memory import get_memory
        from .hooks import get_registry, HookContext

        memory = get_memory()
        working_dir = working_dir or os.getcwd()

        # Create session
        session_id = memory.start_session(ai_type, working_dir)

        self.current_session = SessionState(
            session_id=session_id,
            ai_type=ai_type,
            phase=SessionPhase.SESSION_START,
            working_dir=working_dir,
            started_at=datetime.now()
        )

        # Trigger session_start hooks
        hook_ctx = HookContext(
            session_id=session_id,
            ai_type=ai_type,
            working_dir=working_dir,
            phase=SessionPhase.SESSION_START.value
        )
        get_registry().trigger('session_start', hook_ctx)

        # Load previous context
        self.current_session.metadata['previous_handoff'] = memory.get_last_handoff()
        self.current_session.metadata['previous_ledger'] = memory.ledger_get_latest()
        self.current_session.metadata['context'] = memory.build_context()

        # Transition to working phase
        self.current_session.phase = SessionPhase.WORKING

        return self.current_session

    def process_prompt(self, prompt: str) -> Dict:
        """Process a user prompt - Phase 2: Working"""
        from .triggers import process_triggers, execute_trigger

        if not self.current_session:
            raise RuntimeError("No active session. Call start_session first.")

        self.current_session.prompt_count += 1

        # Check for triggers
        triggers = process_triggers(prompt)
        trigger_results = []
        for match, action in triggers:
            result = execute_trigger(match, action, {
                'session_id': self.current_session.session_id,
                'prompt': prompt
            })
            trigger_results.append({
                'trigger': match.trigger_name,
                'result': result
            })

        return {
            'session_id': self.current_session.session_id,
            'prompt_number': self.current_session.prompt_count,
            'triggers_activated': trigger_results
        }

    def process_response(self, response: str) -> Dict:
        """Process AI response and extract learnings"""
        from .memory import get_memory
        from .hooks import get_registry, HookContext

        if not self.current_session:
            return {}

        # Extract learnings
        learnings = self._extract_patterns(response, self.LEARNING_PATTERNS)
        for learning in learnings:
            self.current_session.learnings.append(learning)

        # Extract decisions
        decisions = self._extract_patterns(response, self.DECISION_PATTERNS)
        for decision in decisions:
            self.current_session.decisions.append(decision)

        # Trigger post_response hook
        hook_ctx = HookContext(
            session_id=self.current_session.session_id,
            ai_type=self.current_session.ai_type,
            working_dir=self.current_session.working_dir,
            phase=self.current_session.phase.value,
            response=response
        )
        get_registry().trigger('post_response', hook_ctx)

        # Trigger on_learning hooks for each learning
        memory = get_memory()
        for learning in learnings:
            hook_ctx.metadata['learning'] = learning
            get_registry().trigger('on_learning', hook_ctx)
            memory.save(learning, type='auto-learning', source=self.current_session.ai_type, importance=6)

        return {
            'learnings_extracted': len(learnings),
            'decisions_extracted': len(decisions),
            'learnings': learnings,
            'decisions': decisions
        }

    def prepare_for_compact(self) -> Dict:
        """Prepare for context compaction - Phase 3: PreCompact"""
        from .memory import get_memory
        from .hooks import get_registry, HookContext

        if not self.current_session:
            return {}

        self.current_session.phase = SessionPhase.PRE_COMPACT

        memory = get_memory()

        # Save current state to ledger
        memory.ledger_set(self.current_session.session_id, 'phase', 'pre_compact')
        memory.ledger_set(self.current_session.session_id, 'prompt_count', self.current_session.prompt_count)
        memory.ledger_set(self.current_session.session_id, 'learnings', self.current_session.learnings)
        memory.ledger_set(self.current_session.session_id, 'decisions', self.current_session.decisions)

        # Create auto-handoff
        summary = self._generate_handoff_summary()
        memory.create_handoff(
            self.current_session.session_id,
            summary,
            next_steps='\n'.join(self.current_session.metadata.get('next_steps', [])),
            artifacts=self.current_session.artifacts
        )

        # Trigger pre_compact hooks
        hook_ctx = HookContext(
            session_id=self.current_session.session_id,
            ai_type=self.current_session.ai_type,
            working_dir=self.current_session.working_dir,
            phase=SessionPhase.PRE_COMPACT.value
        )
        get_registry().trigger('pre_compact', hook_ctx)

        # Back to working
        self.current_session.phase = SessionPhase.WORKING

        return {
            'state_saved': True,
            'handoff_created': True,
            'summary': summary
        }

    def end_session(self, outcome: str = 'completed') -> Dict:
        """End the session - Phase 4: SessionEnd"""
        from .memory import get_memory
        from .hooks import get_registry, HookContext
        from .git_integration import get_git_integration

        if not self.current_session:
            return {}

        self.current_session.phase = SessionPhase.SESSION_END

        memory = get_memory()
        git = get_git_integration(self.current_session.working_dir)

        # Save final learnings
        for learning in self.current_session.learnings:
            memory.save(learning, type='session-learning',
                       source=self.current_session.ai_type, importance=7)

        # Create final handoff
        summary = self._generate_handoff_summary()
        memory.create_handoff(
            self.current_session.session_id,
            summary,
            next_steps='\n'.join(self.current_session.metadata.get('next_steps', [])),
            artifacts=self.current_session.artifacts
        )

        # Save to git reasoning if in a repo
        if git.is_git_repo():
            git.add_uncommitted_reasoning({
                'session_id': self.current_session.session_id,
                'summary': summary,
                'learnings': self.current_session.learnings,
                'decisions': self.current_session.decisions
            })

        # End session in memory
        memory.end_session(self.current_session.session_id, outcome)

        # Trigger session_end hooks
        hook_ctx = HookContext(
            session_id=self.current_session.session_id,
            ai_type=self.current_session.ai_type,
            working_dir=self.current_session.working_dir,
            phase=SessionPhase.SESSION_END.value,
            metadata={'outcome': outcome}
        )
        get_registry().trigger('session_end', hook_ctx)

        result = {
            'session_id': self.current_session.session_id,
            'duration_seconds': (datetime.now() - self.current_session.started_at).total_seconds(),
            'prompt_count': self.current_session.prompt_count,
            'learnings_count': len(self.current_session.learnings),
            'outcome': outcome
        }

        self.current_session = None
        return result

    def _extract_patterns(self, text: str, patterns: List[str]) -> List[str]:
        """Extract matches from text using patterns"""
        matches = []
        for pattern in patterns:
            found = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            matches.extend(found)
        return [m.strip() for m in matches if m.strip()][:20]  # Limit

    def _generate_handoff_summary(self) -> str:
        """Generate a handoff summary"""
        parts = [
            f"Session: {self.current_session.session_id}",
            f"Duration: {(datetime.now() - self.current_session.started_at).total_seconds():.0f}s",
            f"Prompts: {self.current_session.prompt_count}",
        ]

        if self.current_session.learnings:
            parts.append(f"\nLearnings:\n- " + "\n- ".join(self.current_session.learnings[:5]))

        if self.current_session.decisions:
            parts.append(f"\nDecisions:\n- " + "\n- ".join(self.current_session.decisions[:5]))

        return "\n".join(parts)

    def get_injection_context(self) -> str:
        """Get context to inject into AI prompt"""
        from .memory import get_memory

        if not self.current_session:
            return ""

        memory = get_memory()
        return memory.build_context()


# Singleton
_manager = None

def get_session_manager() -> SessionManager:
    global _manager
    if _manager is None:
        _manager = SessionManager()
    return _manager
