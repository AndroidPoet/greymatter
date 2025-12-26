#!/usr/bin/env python3
"""
Context Manager - Real-time "Clear, Don't Compact" Implementation

This module implements the Continuous-Claude philosophy:
1. Detect when context is getting full
2. Create handoff with all important state
3. Signal to CLEAR (not compact)
4. Resume seamlessly where we left off

The key insight: Compaction loses information. Clear + Handoff preserves it.
"""

import os
import time
import json
from pathlib import Path
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ContextState(Enum):
    """Context fullness states"""
    FRESH = "fresh"           # Just started, plenty of room
    NORMAL = "normal"         # Working normally
    FILLING = "filling"       # Getting full, start preparing
    CRITICAL = "critical"     # About to overflow, must clear NOW
    CLEARED = "cleared"       # Just cleared, loading handoff


@dataclass
class ContextMetrics:
    """Track context usage"""
    message_count: int = 0
    estimated_tokens: int = 0
    user_messages: int = 0
    ai_responses: int = 0
    tool_calls: int = 0
    last_activity: float = field(default_factory=time.time)

    # Thresholds (configurable per AI)
    max_messages: int = 50        # ~50 back-and-forth before context issues
    max_tokens: int = 100000      # Conservative estimate
    filling_threshold: float = 0.7   # 70% = start preparing
    critical_threshold: float = 0.9  # 90% = must clear


class ContextManager:
    """
    Manages context lifecycle with "Clear, Don't Compact" philosophy

    Flow:
    1. Monitor context usage in real-time
    2. When FILLING: Prepare handoff, warn user
    3. When CRITICAL: Force handoff, signal clear
    4. On restart: Detect previous handoff, auto-resume
    """

    # Token estimates per content type
    TOKEN_ESTIMATES = {
        'user_message': 50,      # Average user message
        'ai_response': 200,      # Average AI response
        'tool_call': 100,        # Tool invocation
        'tool_result': 150,      # Tool result
        'system_prompt': 500,    # System prompt injection
        'memory_context': 300,   # Memory context block
    }

    def __init__(self, ai_type: str = 'claude'):
        self.ai_type = ai_type
        self.metrics = ContextMetrics()
        self.state = ContextState.FRESH
        self.session_id: Optional[str] = None
        self.handoff_ready = False
        self.pending_handoff: Optional[Dict] = None

        # Callbacks
        self.on_filling: Optional[Callable] = None
        self.on_critical: Optional[Callable] = None
        self.on_clear_needed: Optional[Callable] = None

        # Configure thresholds per AI
        self._configure_for_ai(ai_type)

    def _configure_for_ai(self, ai_type: str):
        """Configure thresholds based on AI type"""
        configs = {
            'claude': {
                'max_messages': 60,
                'max_tokens': 150000,  # Claude has ~200k context
            },
            'gemini': {
                'max_messages': 40,
                'max_tokens': 100000,  # Gemini varies
            },
            'ollama': {
                'max_messages': 30,
                'max_tokens': 8000,    # Local models have less
            },
        }
        config = configs.get(ai_type, configs['claude'])
        self.metrics.max_messages = config['max_messages']
        self.metrics.max_tokens = config['max_tokens']

    def start_session(self, session_id: str):
        """Start tracking a new session"""
        from .memory import get_memory

        self.session_id = session_id
        self.metrics = ContextMetrics()
        self.state = ContextState.FRESH

        # Check for previous handoff to resume
        memory = get_memory()
        last_handoff = memory.get_last_handoff()

        if last_handoff:
            # Check if it's recent (within last 24 hours)
            created = datetime.fromisoformat(last_handoff['created_at'].replace('Z', '+00:00'))
            age_hours = (datetime.now() - created.replace(tzinfo=None)).total_seconds() / 3600

            if age_hours < 24:
                self.pending_handoff = last_handoff
                self.state = ContextState.CLEARED
                return {
                    'resuming': True,
                    'handoff': last_handoff,
                    'age_hours': age_hours
                }

        return {'resuming': False}

    def record_user_message(self, message: str):
        """Record a user message"""
        self.metrics.user_messages += 1
        self.metrics.message_count += 1
        self.metrics.estimated_tokens += max(
            len(message) // 4,  # Rough token estimate
            self.TOKEN_ESTIMATES['user_message']
        )
        self.metrics.last_activity = time.time()
        self._update_state()

    def record_ai_response(self, response: str):
        """Record an AI response"""
        self.metrics.ai_responses += 1
        self.metrics.message_count += 1
        self.metrics.estimated_tokens += max(
            len(response) // 4,
            self.TOKEN_ESTIMATES['ai_response']
        )
        self.metrics.last_activity = time.time()
        self._update_state()

    def record_tool_call(self, tool_name: str, result_size: int = 0):
        """Record a tool invocation"""
        self.metrics.tool_calls += 1
        self.metrics.estimated_tokens += self.TOKEN_ESTIMATES['tool_call']
        self.metrics.estimated_tokens += max(
            result_size // 4,
            self.TOKEN_ESTIMATES['tool_result']
        )
        self._update_state()

    def _update_state(self):
        """Update context state based on metrics"""
        # Calculate fullness (use the higher of message or token ratio)
        message_ratio = self.metrics.message_count / self.metrics.max_messages
        token_ratio = self.metrics.estimated_tokens / self.metrics.max_tokens
        fullness = max(message_ratio, token_ratio)

        old_state = self.state

        if fullness >= self.metrics.critical_threshold:
            self.state = ContextState.CRITICAL
        elif fullness >= self.metrics.filling_threshold:
            self.state = ContextState.FILLING
        elif fullness > 0.1:
            self.state = ContextState.NORMAL
        else:
            self.state = ContextState.FRESH

        # Trigger callbacks on state change
        if old_state != self.state:
            if self.state == ContextState.FILLING and self.on_filling:
                self.on_filling(self.get_status())
            elif self.state == ContextState.CRITICAL and self.on_critical:
                self.on_critical(self.get_status())

    def get_status(self) -> Dict:
        """Get current context status"""
        message_ratio = self.metrics.message_count / self.metrics.max_messages
        token_ratio = self.metrics.estimated_tokens / self.metrics.max_tokens

        return {
            'state': self.state.value,
            'message_count': self.metrics.message_count,
            'max_messages': self.metrics.max_messages,
            'estimated_tokens': self.metrics.estimated_tokens,
            'max_tokens': self.metrics.max_tokens,
            'message_fullness': f"{message_ratio * 100:.1f}%",
            'token_fullness': f"{token_ratio * 100:.1f}%",
            'overall_fullness': f"{max(message_ratio, token_ratio) * 100:.1f}%",
            'handoff_ready': self.handoff_ready,
        }

    def should_prepare_handoff(self) -> bool:
        """Check if we should start preparing a handoff"""
        return self.state in (ContextState.FILLING, ContextState.CRITICAL)

    def should_clear_now(self) -> bool:
        """Check if we need to clear immediately"""
        return self.state == ContextState.CRITICAL

    def prepare_handoff(self,
                       current_task: str = None,
                       learnings: List[str] = None,
                       decisions: List[str] = None,
                       next_steps: List[str] = None,
                       open_questions: List[str] = None) -> Dict:
        """
        Prepare a handoff document for context clearing

        This captures everything needed to resume seamlessly:
        - What we were doing
        - What we learned
        - What decisions were made
        - What to do next
        - What questions remain
        """
        from .memory import get_memory
        from .brain import get_brain

        memory = get_memory()
        brain = get_brain()

        # Build comprehensive handoff
        handoff_data = {
            'session_id': self.session_id,
            'created_at': datetime.now().isoformat(),
            'context_state': self.get_status(),

            # Current state
            'current_task': current_task or 'Unknown task',
            'working_directory': os.getcwd(),

            # Accumulated knowledge
            'learnings': learnings or [],
            'decisions': decisions or [],

            # Next actions
            'next_steps': next_steps or [],
            'open_questions': open_questions or [],

            # Brain state (working memory)
            'working_memory': brain.get_state()['working_memory'],
        }

        # Generate summary
        summary_parts = []

        if current_task:
            summary_parts.append(f"## Current Task\n{current_task}")

        if learnings:
            summary_parts.append(f"## Learnings\n" + "\n".join(f"- {l}" for l in learnings[:10]))

        if decisions:
            summary_parts.append(f"## Decisions Made\n" + "\n".join(f"- {d}" for d in decisions[:10]))

        if next_steps:
            summary_parts.append(f"## Next Steps (IMPORTANT)\n" + "\n".join(f"1. {s}" for s in next_steps[:5]))

        if open_questions:
            summary_parts.append(f"## Open Questions\n" + "\n".join(f"? {q}" for q in open_questions[:5]))

        summary = "\n\n".join(summary_parts)

        # Save to database
        handoff_id = memory.create_handoff(
            session_id=self.session_id,
            summary=summary,
            next_steps="\n".join(next_steps or []),
            open_questions="\n".join(open_questions or []),
            artifacts=[handoff_data]
        )

        self.handoff_ready = True
        handoff_data['id'] = handoff_id
        handoff_data['summary'] = summary

        return handoff_data

    def get_clear_instructions(self) -> str:
        """Get instructions for the AI on how to clear and resume"""
        if not self.handoff_ready:
            return ""

        return """
⚠️ CONTEXT LIMIT APPROACHING - CLEAR RECOMMENDED

I've saved all important context to memory. To continue efficiently:

1. **Use /clear** - This clears the context window
2. **I'll auto-resume** - On restart, I'll load the handoff and continue

**What's been saved:**
- Current task and progress
- All learnings and decisions
- Next steps to continue
- Open questions

**To clear now:** Just say "clear" or use your AI's clear command.
After clearing, simply start a new message and I'll resume automatically.
"""

    def get_resume_context(self) -> str:
        """Get context to inject when resuming from a handoff"""
        if not self.pending_handoff:
            return ""

        handoff = self.pending_handoff

        context = f"""
## 🔄 RESUMING FROM PREVIOUS SESSION

{handoff.get('summary', 'No summary available')}

---
**Session was cleared to save context. Continuing where we left off.**
**All memories and learnings have been preserved.**
"""

        # Clear pending handoff after use
        self.pending_handoff = None
        self.state = ContextState.FRESH

        return context

    def get_context_indicator(self) -> str:
        """Get a visual indicator of context fullness for display"""
        status = self.get_status()
        fullness = max(
            self.metrics.message_count / self.metrics.max_messages,
            self.metrics.estimated_tokens / self.metrics.max_tokens
        )

        # Create visual bar
        bar_width = 20
        filled = int(fullness * bar_width)
        empty = bar_width - filled

        if self.state == ContextState.CRITICAL:
            color = "🔴"
            bar = "█" * filled + "░" * empty
        elif self.state == ContextState.FILLING:
            color = "🟡"
            bar = "█" * filled + "░" * empty
        elif self.state == ContextState.NORMAL:
            color = "🟢"
            bar = "█" * filled + "░" * empty
        else:
            color = "⚪"
            bar = "░" * bar_width

        return f"{color} Context [{bar}] {fullness * 100:.0f}%"


# Singleton
_manager = None

def get_context_manager(ai_type: str = 'claude') -> ContextManager:
    """Get singleton context manager"""
    global _manager
    if _manager is None or _manager.ai_type != ai_type:
        _manager = ContextManager(ai_type)
    return _manager


def auto_handoff_check(response: str) -> Optional[str]:
    """
    Check if we should inject handoff warning into response
    Call this after each AI response
    """
    manager = get_context_manager()
    manager.record_ai_response(response)

    if manager.should_clear_now():
        return manager.get_clear_instructions()
    elif manager.should_prepare_handoff() and not manager.handoff_ready:
        # Prepare handoff in background
        manager.prepare_handoff(
            current_task="Task in progress (auto-detected)",
            next_steps=["Continue from where we left off"]
        )
        return f"\n\n---\n⚡ Context at {manager.get_status()['overall_fullness']} - Handoff ready. Use /clear when needed."

    return None
