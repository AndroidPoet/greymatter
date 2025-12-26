#!/usr/bin/env python3
"""
Skills System - Quick, focused utilities that run in current context

Skills are lightweight operations that don't need a fresh context window.
They run quickly and return results directly.

Built-in Skills:
- save_state: Save current session state
- create_handoff: Create session handoff
- resume_handoff: Resume from previous session
- tdd_workflow: Red-green-refactor cycle
- commit: Git commit with context
- search_memory: Search persistent memory
- list_memories: List recent memories
- save_artifact: Save code/file artifact
"""

import subprocess
import os
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SkillResult:
    """Result from a skill execution"""
    success: bool
    output: str
    data: Optional[Dict] = None
    error: Optional[str] = None


class Skill:
    """Base skill class"""

    def __init__(self, name: str, description: str, func: Callable):
        self.name = name
        self.description = description
        self.func = func

    def run(self, context: Dict = None) -> SkillResult:
        """Execute the skill"""
        try:
            result = self.func(context or {})
            if isinstance(result, SkillResult):
                return result
            return SkillResult(success=True, output=str(result), data=result if isinstance(result, dict) else None)
        except Exception as e:
            return SkillResult(success=False, output="", error=str(e))


# Skill registry
_skills: Dict[str, Skill] = {}


def skill(name: str, description: str = ""):
    """Decorator to register a skill"""
    def decorator(func: Callable):
        _skills[name] = Skill(name, description or func.__doc__ or "", func)
        return func
    return decorator


def run_skill(name: str, context: Dict = None) -> SkillResult:
    """Run a skill by name"""
    if name not in _skills:
        return SkillResult(success=False, output="", error=f"Unknown skill: {name}")
    return _skills[name].run(context)


def list_skills() -> Dict[str, str]:
    """List all available skills"""
    return {name: skill.description for name, skill in _skills.items()}


# === Built-in Skills ===

@skill("save_state", "Save current session state to ledger")
def save_state(ctx: Dict) -> Dict:
    from .memory import get_memory
    memory = get_memory()

    session_id = ctx.get('session_id', f"manual-{int(datetime.now().timestamp())}")

    state = {
        'working_dir': ctx.get('working_dir', os.getcwd()),
        'timestamp': datetime.now().isoformat(),
        'context': ctx.get('context', {}),
    }

    for key, value in state.items():
        memory.ledger_set(session_id, key, value)

    return {'session_id': session_id, 'state': state}


@skill("create_handoff", "Create a session handoff document")
def create_handoff(ctx: Dict) -> Dict:
    from .memory import get_memory
    memory = get_memory()

    session_id = ctx.get('session_id', f"manual-{int(datetime.now().timestamp())}")
    summary = ctx.get('summary', "Session ended")
    next_steps = ctx.get('next_steps')
    open_questions = ctx.get('open_questions')

    handoff_id = memory.create_handoff(
        session_id,
        summary,
        next_steps=next_steps,
        open_questions=open_questions
    )

    return {'handoff_id': handoff_id, 'session_id': session_id}


@skill("resume_handoff", "Resume from the last session handoff")
def resume_handoff(ctx: Dict) -> Dict:
    from .memory import get_memory
    memory = get_memory()

    handoff = memory.get_last_handoff()
    if not handoff:
        return {'resumed': False, 'message': 'No previous handoff found'}

    ledger = memory.ledger_get_latest()

    return {
        'resumed': True,
        'handoff': handoff,
        'ledger': ledger,
        'context': memory.build_context()
    }


@skill("tdd_workflow", "Activate Test-Driven Development workflow")
def tdd_workflow(ctx: Dict) -> str:
    """
    TDD Workflow:
    1. RED: Write a failing test first
    2. GREEN: Write minimal code to pass
    3. REFACTOR: Clean up while keeping tests green
    """
    return """TDD Workflow Activated!

Follow this cycle:
1. 🔴 RED: Write a failing test that defines the expected behavior
2. 🟢 GREEN: Write the minimum code to make the test pass
3. 🔵 REFACTOR: Clean up the code while keeping tests green

Tips:
- Start with the simplest test case
- Only write enough code to pass the current test
- Refactor only when tests are passing
- Keep commits small and focused

Say "test passes" or "tests green" when ready to move to next phase.
"""


@skill("commit", "Create a git commit with context")
def commit_skill(ctx: Dict) -> Dict:
    from .memory import get_memory
    memory = get_memory()

    message = ctx.get('message', '')
    if not message:
        return {'success': False, 'error': 'Commit message required'}

    # Get git status
    status = subprocess.run(['git', 'status', '--porcelain'],
                          capture_output=True, text=True, cwd=ctx.get('cwd'))

    if not status.stdout.strip():
        return {'success': False, 'error': 'Nothing to commit'}

    # Stage all changes
    subprocess.run(['git', 'add', '-A'], cwd=ctx.get('cwd'))

    # Commit
    result = subprocess.run(
        ['git', 'commit', '-m', message],
        capture_output=True, text=True, cwd=ctx.get('cwd')
    )

    if result.returncode == 0:
        # Save to memory
        memory.save(f"Committed: {message}", type='git-commit', importance=5)

        # Get commit hash
        hash_result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True, text=True, cwd=ctx.get('cwd')
        )

        return {
            'success': True,
            'message': message,
            'hash': hash_result.stdout.strip()[:8]
        }

    return {'success': False, 'error': result.stderr}


@skill("search_memory", "Search persistent memory")
def search_memory(ctx: Dict) -> Dict:
    from .memory import get_memory
    memory = get_memory()

    query = ctx.get('query', '')
    if not query:
        return {'results': [], 'error': 'Query required'}

    results = memory.search(query, limit=ctx.get('limit', 10))
    return {'results': results, 'count': len(results)}


@skill("list_memories", "List recent memories")
def list_memories(ctx: Dict) -> Dict:
    from .memory import get_memory
    memory = get_memory()

    recent = memory.get_recent(limit=ctx.get('limit', 20))
    important = memory.get_important(min_importance=7)

    return {
        'recent': recent,
        'important': important,
        'stats': memory.stats()
    }


@skill("save_artifact", "Save a code or file artifact")
def save_artifact(ctx: Dict) -> Dict:
    from .memory import get_memory
    memory = get_memory()

    artifact_type = ctx.get('type', 'code')
    name = ctx.get('name', 'unnamed')
    content = ctx.get('content', '')
    file_path = ctx.get('file_path')

    if not content:
        return {'success': False, 'error': 'Content required'}

    session_id = ctx.get('session_id', 'manual')
    artifact_id = memory.save_artifact(session_id, artifact_type, name, content, file_path)

    return {'artifact_id': artifact_id, 'name': name}


@skill("get_context", "Get current memory context for injection")
def get_context(ctx: Dict) -> Dict:
    from .memory import get_memory
    memory = get_memory()

    query = ctx.get('query')
    context = memory.build_context(query=query)

    return {
        'context': context,
        'handoff': memory.get_last_handoff(),
        'ledger': memory.ledger_get_latest()
    }


@skill("clear_session", "Clear current session and start fresh")
def clear_session(ctx: Dict) -> Dict:
    from .memory import get_memory
    memory = get_memory()

    session_id = ctx.get('session_id')
    if session_id:
        memory.end_session(session_id, 'cleared')

    # Create handoff before clearing
    if ctx.get('create_handoff', True):
        memory.create_handoff(
            session_id or 'clear',
            summary="Session cleared by user",
            next_steps=ctx.get('next_steps')
        )

    return {'cleared': True, 'message': 'Session cleared. Memory persisted.'}


@skill("stats", "Get memory statistics")
def stats_skill(ctx: Dict) -> Dict:
    from .memory import get_memory
    memory = get_memory()
    return memory.stats()
