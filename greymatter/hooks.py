#!/usr/bin/env python3
"""
Hooks System - Lifecycle hooks for AI sessions

Hook Types:
- session_start: When a new session begins
- session_end: When session ends
- pre_prompt: Before sending prompt to AI
- post_response: After receiving AI response
- pre_tool: Before a tool is executed
- post_tool: After a tool executes
- pre_compact: Before context compaction (save state!)
- on_error: When an error occurs
- on_learning: When a learning is detected
- on_handoff: When creating a handoff
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class HookContext:
    """Context passed to hooks"""
    session_id: str
    ai_type: str
    working_dir: str
    phase: str  # session_start, working, pre_compact, session_end
    prompt: Optional[str] = None
    response: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args: Optional[Dict] = None
    tool_result: Optional[str] = None
    error: Optional[Exception] = None
    metadata: Dict = field(default_factory=dict)


class HookRegistry:
    """Registry for all hooks"""

    HOOK_TYPES = [
        'session_start',
        'session_end',
        'pre_prompt',
        'post_response',
        'pre_tool',
        'post_tool',
        'pre_compact',
        'on_error',
        'on_learning',
        'on_handoff',
    ]

    def __init__(self):
        self.hooks: Dict[str, List[Callable]] = {h: [] for h in self.HOOK_TYPES}
        self.shell_hooks: Dict[str, List[str]] = {h: [] for h in self.HOOK_TYPES}
        self._load_config_hooks()

    def _load_config_hooks(self):
        """Load hooks from config file"""
        config_path = Path.home() / '.ai-plus-plus' / 'hooks.json'
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text())
                for hook_type, commands in config.get('shell_hooks', {}).items():
                    if hook_type in self.HOOK_TYPES:
                        if isinstance(commands, str):
                            commands = [commands]
                        self.shell_hooks[hook_type].extend(commands)
            except Exception as e:
                print(f"Warning: Failed to load hooks config: {e}")

    def register(self, hook_type: str, callback: Callable):
        """Register a Python hook"""
        if hook_type not in self.HOOK_TYPES:
            raise ValueError(f"Unknown hook type: {hook_type}")
        self.hooks[hook_type].append(callback)

    def register_shell(self, hook_type: str, command: str):
        """Register a shell command hook"""
        if hook_type not in self.HOOK_TYPES:
            raise ValueError(f"Unknown hook type: {hook_type}")
        self.shell_hooks[hook_type].append(command)

    def trigger(self, hook_type: str, context: HookContext) -> List[Any]:
        """Trigger all hooks of a type"""
        results = []

        # Python hooks
        for hook in self.hooks[hook_type]:
            try:
                result = hook(context)
                results.append(result)
            except Exception as e:
                print(f"Hook error ({hook_type}): {e}")

        # Shell hooks
        for command in self.shell_hooks[hook_type]:
            try:
                env = os.environ.copy()
                env.update({
                    'AI_SESSION_ID': context.session_id,
                    'AI_TYPE': context.ai_type,
                    'AI_PHASE': context.phase,
                    'AI_WORKING_DIR': context.working_dir,
                })
                if context.prompt:
                    env['AI_PROMPT'] = context.prompt[:1000]
                if context.response:
                    env['AI_RESPONSE'] = context.response[:1000]

                result = subprocess.run(
                    command,
                    shell=True,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                results.append(result.stdout)
            except Exception as e:
                print(f"Shell hook error ({hook_type}): {e}")

        return results


# Global registry
_registry = None

def get_registry() -> HookRegistry:
    global _registry
    if _registry is None:
        _registry = HookRegistry()
    return _registry


# Decorator for easy hook registration
def hook(hook_type: str):
    """Decorator to register a function as a hook"""
    def decorator(func: Callable):
        get_registry().register(hook_type, func)
        return func
    return decorator


# === Built-in Hooks ===

@hook('session_start')
def load_context_hook(ctx: HookContext):
    """Load memory context at session start"""
    from .memory import get_memory
    memory = get_memory()
    context = memory.build_context()
    ctx.metadata['injected_context'] = context
    return context


@hook('pre_compact')
def auto_save_hook(ctx: HookContext):
    """Auto-save state before compaction"""
    from .memory import get_memory
    memory = get_memory()

    # Save current state to ledger
    memory.ledger_set(ctx.session_id, 'last_phase', ctx.phase)
    memory.ledger_set(ctx.session_id, 'working_dir', ctx.working_dir)
    memory.ledger_set(ctx.session_id, 'timestamp', datetime.now().isoformat())

    # Auto-create handoff
    if ctx.response:
        summary = f"Auto-saved before compaction. Last response preview: {ctx.response[:200]}..."
        memory.create_handoff(ctx.session_id, summary)

    return True


@hook('on_learning')
def save_learning_hook(ctx: HookContext):
    """Save detected learnings to memory"""
    from .memory import get_memory
    memory = get_memory()

    learning = ctx.metadata.get('learning')
    if learning:
        memory.save(learning, type='learning', source=ctx.ai_type, importance=7)

    return True


@hook('session_end')
def finalize_session_hook(ctx: HookContext):
    """Finalize session and create handoff"""
    from .memory import get_memory
    memory = get_memory()

    # End the session
    outcome = ctx.metadata.get('outcome', 'completed')
    memory.end_session(ctx.session_id, outcome)

    return True
