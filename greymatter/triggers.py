#!/usr/bin/env python3
"""
Natural Language Triggers - Detect keywords and activate features

Triggers listen for natural language patterns and activate appropriate
actions like saving state, creating handoffs, spawning agents, etc.

Examples:
- "save state" → Updates ledger with current state
- "done for today" → Creates comprehensive handoff
- "create plan" → Spawns plan-agent
- "implement" → Activates TDD workflow
- "research" → Spawns research-agent
- "debug this" → Spawns debug-agent
- "remember this" → Saves to memory
"""

import re
from typing import Optional, Callable, Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class TriggerMatch:
    """Result of a trigger match"""
    trigger_name: str
    matched_text: str
    extracted: Dict[str, str]  # Extracted values from the match
    confidence: float  # 0-1


@dataclass
class TriggerAction:
    """Action to take when trigger fires"""
    action_type: str  # 'skill', 'agent', 'memory', 'handoff', 'ledger', 'custom'
    action_name: str
    params: Dict


class Trigger:
    """A single trigger definition"""

    def __init__(self, name: str, patterns: List[str], action: TriggerAction,
                 description: str = "", priority: int = 5):
        self.name = name
        self.patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
        self.action = action
        self.description = description
        self.priority = priority  # Higher = checked first

    def match(self, text: str) -> Optional[TriggerMatch]:
        """Check if text matches this trigger"""
        for pattern in self.patterns:
            match = pattern.search(text)
            if match:
                return TriggerMatch(
                    trigger_name=self.name,
                    matched_text=match.group(0),
                    extracted=match.groupdict() if match.groupdict() else {},
                    confidence=0.9 if match.group(0).lower() in text.lower() else 0.7
                )
        return None


class TriggerEngine:
    """Engine for processing triggers"""

    def __init__(self):
        self.triggers: List[Trigger] = []
        self._register_default_triggers()

    def _register_default_triggers(self):
        """Register built-in triggers"""

        # State management
        self.register(Trigger(
            name="save_state",
            patterns=[
                r"save (?:the )?state",
                r"persist (?:the )?state",
                r"remember (?:the )?state",
                r"update ledger",
            ],
            action=TriggerAction('ledger', 'save_current', {}),
            description="Save current session state to ledger",
            priority=8
        ))

        self.register(Trigger(
            name="done_for_today",
            patterns=[
                r"done for (?:the )?(?:day|today|now)",
                r"(?:let's )?wrap up",
                r"end (?:the )?session",
                r"that's (?:all|it) for (?:today|now)",
                r"signing off",
            ],
            action=TriggerAction('handoff', 'create_comprehensive', {}),
            description="Create comprehensive handoff and end session",
            priority=9
        ))

        # Agent triggers
        self.register(Trigger(
            name="create_plan",
            patterns=[
                r"(?:create|make|design) (?:a |an )?(?:implementation )?plan",
                r"plan (?:the )?implementation",
                r"how should (?:we|I) implement",
                r"let's plan",
            ],
            action=TriggerAction('agent', 'plan', {}),
            description="Spawn plan-agent to design implementation",
            priority=7
        ))

        self.register(Trigger(
            name="research",
            patterns=[
                r"research (?:this|that|about)",
                r"investigate (?:this|that)",
                r"look into (?:this|that)",
                r"find out (?:about|how|why|what)",
                r"dig into",
            ],
            action=TriggerAction('agent', 'research', {}),
            description="Spawn research-agent for investigation",
            priority=7
        ))

        self.register(Trigger(
            name="debug",
            patterns=[
                r"debug (?:this|that|it)",
                r"(?:help me )?fix (?:this|that) (?:bug|error|issue)",
                r"why (?:is|isn't) (?:this|it) (?:working|broken)",
                r"troubleshoot",
                r"what's (?:wrong|broken)",
            ],
            action=TriggerAction('agent', 'debug', {}),
            description="Spawn debug-agent for debugging",
            priority=7
        ))

        self.register(Trigger(
            name="validate",
            patterns=[
                r"validate (?:this|that|it)",
                r"verify (?:this|that|it)",
                r"check (?:if )?(?:this|that|it) (?:is )?(?:correct|right|works)",
                r"does this (?:look )?(?:correct|right|good)",
            ],
            action=TriggerAction('agent', 'validate', {}),
            description="Spawn validate-agent for verification",
            priority=7
        ))

        self.register(Trigger(
            name="review_code",
            patterns=[
                r"review (?:this|that|the) (?:code|changes|pr)",
                r"code review",
                r"(?:can you )?look (?:over|at) (?:this|my) code",
            ],
            action=TriggerAction('agent', 'review', {}),
            description="Spawn review-agent for code review",
            priority=7
        ))

        self.register(Trigger(
            name="explore_codebase",
            patterns=[
                r"explore (?:the )?(?:codebase|project|repo)",
                r"understand (?:the )?(?:codebase|structure|architecture)",
                r"how does (?:this|the) (?:project|codebase) work",
                r"map (?:out )?(?:the )?(?:codebase|structure)",
            ],
            action=TriggerAction('agent', 'explorer', {}),
            description="Spawn explorer-agent to understand codebase",
            priority=7
        ))

        # Memory triggers
        self.register(Trigger(
            name="remember",
            patterns=[
                r"remember (?:that |this: ?)?(?P<content>.+)",
                r"save (?:to memory|this): ?(?P<content>.+)",
                r"note (?:that |this: ?)?(?P<content>.+)",
                r"don't forget: ?(?P<content>.+)",
            ],
            action=TriggerAction('memory', 'save', {}),
            description="Save something to memory",
            priority=6
        ))

        self.register(Trigger(
            name="recall",
            patterns=[
                r"(?:do you )?remember (?:anything about )?(?P<query>.+)\?",
                r"what do you (?:know|remember) about (?P<query>.+)\?",
                r"recall (?P<query>.+)",
                r"search memory (?:for )?(?P<query>.+)",
            ],
            action=TriggerAction('memory', 'search', {}),
            description="Search memory for something",
            priority=6
        ))

        # TDD workflow
        self.register(Trigger(
            name="implement_tdd",
            patterns=[
                r"implement (?:using )?tdd",
                r"(?:let's )?(?:do |use )?test[- ]driven",
                r"write (?:the )?test first",
                r"red[- ]green[- ]refactor",
            ],
            action=TriggerAction('skill', 'tdd_workflow', {}),
            description="Activate TDD workflow",
            priority=8
        ))

        # Skill triggers
        self.register(Trigger(
            name="commit",
            patterns=[
                r"(?:create|make) (?:a )?commit",
                r"commit (?:the )?changes",
                r"git commit",
            ],
            action=TriggerAction('skill', 'commit', {}),
            description="Create a git commit",
            priority=6
        ))

    def register(self, trigger: Trigger):
        """Register a trigger"""
        self.triggers.append(trigger)
        self.triggers.sort(key=lambda t: -t.priority)  # Higher priority first

    def process(self, text: str) -> List[Tuple[TriggerMatch, TriggerAction]]:
        """Process text and return all matching triggers with actions"""
        matches = []
        for trigger in self.triggers:
            match = trigger.match(text)
            if match:
                matches.append((match, trigger.action))
        return matches

    def process_first(self, text: str) -> Optional[Tuple[TriggerMatch, TriggerAction]]:
        """Process text and return first (highest priority) match"""
        matches = self.process(text)
        return matches[0] if matches else None


# Global engine
_engine = None

def get_engine() -> TriggerEngine:
    global _engine
    if _engine is None:
        _engine = TriggerEngine()
    return _engine


def process_triggers(text: str) -> List[Tuple[TriggerMatch, TriggerAction]]:
    """Convenience function to process triggers"""
    return get_engine().process(text)


def execute_trigger(match: TriggerMatch, action: TriggerAction,
                    context: Dict = None) -> any:
    """Execute a trigger action"""
    from .memory import get_memory
    from .agents import run_agent

    memory = get_memory()
    context = context or {}

    if action.action_type == 'memory':
        if action.action_name == 'save':
            content = match.extracted.get('content', '')
            if content:
                return memory.save(content, type='user-note', importance=7)
        elif action.action_name == 'search':
            query = match.extracted.get('query', '')
            if query:
                return memory.search(query)

    elif action.action_type == 'agent':
        task = context.get('task', match.matched_text)
        return run_agent(action.action_name, task, context=context)

    elif action.action_type == 'ledger':
        session_id = context.get('session_id', 'manual')
        memory.ledger_set(session_id, 'last_action', match.matched_text)
        return True

    elif action.action_type == 'handoff':
        session_id = context.get('session_id', 'manual')
        summary = context.get('summary', f"Session ended: {match.matched_text}")
        return memory.create_handoff(session_id, summary)

    elif action.action_type == 'skill':
        from .skills import run_skill
        return run_skill(action.action_name, context)

    return None
