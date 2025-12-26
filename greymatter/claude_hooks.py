#!/usr/bin/env python3
"""
Claude Code Hook Integration

Integrates Grey Matter with Claude Code's native hooks:
- PreCompact: Save context before Claude auto-compacts
- SessionStart: Resume from last memory state

This allows Grey Matter to work seamlessly with Claude Code's
automatic context management.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict


def get_claude_settings_path() -> Path:
    """Get path to Claude settings file"""
    return Path.home() / ".claude" / "settings.json"


def get_claude_local_settings_path() -> Path:
    """Get path to Claude local settings file"""
    return Path.home() / ".claude" / "settings.local.json"


def save_precompact_state() -> Dict:
    """
    Called when Claude is about to compact context.
    Saves current state to Grey Matter memory.

    Returns status dict with what was saved.
    """
    from .memory import get_memory
    from .brain import get_brain
    from .context_manager import get_context_manager

    memory = get_memory()
    brain = get_brain()
    manager = get_context_manager('claude')

    # Get current brain state
    brain_state = brain.get_state()
    recent_learnings = brain_state.get('recent_learnings', [])
    working_memory_count = brain_state.get('working_memory', 0)

    # Get recent memories for context
    recent = memory.search("", limit=10)
    recent_list = recent if isinstance(recent, list) else []

    # Build precompact snapshot
    snapshot = {
        'timestamp': datetime.now().isoformat(),
        'working_directory': os.getcwd(),
        'working_memory_count': working_memory_count,
        'recent_learnings': recent_learnings,
        'context_state': manager.get_status(),
        'recent_memories': [m['content'] for m in recent_list] if recent_list else [],
    }

    # Create handoff document
    handoff_summary = []

    if recent_learnings:
        handoff_summary.append("## Recent Learnings (Active Thoughts)")
        for item in recent_learnings[:7]:  # Top 7 items
            handoff_summary.append(f"- {item}")

    if recent_list:
        handoff_summary.append("\n## Recent Context")
        for m in recent_list[:5]:
            handoff_summary.append(f"- {m['content'][:100]}...")

    summary = "\n".join(handoff_summary) if handoff_summary else "No active context"

    # Save as handoff
    session_id = f"claude-precompact-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    handoff_id = memory.create_handoff(
        session_id=session_id,
        summary=summary,
        next_steps="Continue from precompact state",
        open_questions="",
        artifacts=[snapshot]
    )

    # Also save to a quick-access file for fast resume
    cache_file = Path.home() / ".greymatter" / "last_precompact.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)

    cache_data = {
        'handoff_id': handoff_id,
        'timestamp': snapshot['timestamp'],
        'summary_preview': summary[:500],
        'working_dir': snapshot['working_directory'],
    }

    with open(cache_file, 'w') as f:
        json.dump(cache_data, f, indent=2)

    return {
        'status': 'saved',
        'handoff_id': handoff_id,
        'items_saved': len(recent_learnings) + len(recent_list),
        'working_dir': os.getcwd(),
    }


def get_resume_context() -> str:
    """
    Get context to resume from after compaction.
    Called on SessionStart or when resuming.

    Returns formatted context string to inject.
    """
    from .memory import get_memory
    from .brain import get_brain

    memory = get_memory()

    # Check for precompact cache
    cache_file = Path.home() / ".greymatter" / "last_precompact.json"

    context_parts = []

    # Try to get last handoff
    last_handoff = memory.get_last_handoff()

    if last_handoff:
        created = datetime.fromisoformat(last_handoff['created_at'].replace('Z', '+00:00'))
        age_hours = (datetime.now() - created.replace(tzinfo=None)).total_seconds() / 3600

        if age_hours < 2:  # Within 2 hours = recent context clear
            context_parts.append("## Resuming from Context Clear")
            context_parts.append(f"*Cleared {age_hours:.1f} hours ago*\n")

            if last_handoff.get('summary'):
                context_parts.append(last_handoff['summary'])

    # Get relevant memories for current directory
    cwd = os.getcwd()
    project_memories = memory.search(cwd, limit=5)

    if project_memories:
        context_parts.append("\n## Project Memories")
        for m in project_memories:
            context_parts.append(f"- {m['content'][:150]}")

    # Get recent important memories
    recent_important = memory.search("important", limit=3)
    if recent_important:
        context_parts.append("\n## Important Context")
        for m in recent_important:
            if m.get('importance', 0) >= 0.7:
                context_parts.append(f"- {m['content'][:150]}")

    if not context_parts:
        return ""

    return "\n".join(context_parts)


def install_claude_hooks(force: bool = False) -> Dict:
    """
    Install Grey Matter hooks into Claude Code settings.

    Adds:
    - PreCompact hook: Calls gm-precompact to save state
    - SessionStart hook: Adds context note

    Returns status dict.
    """
    settings_path = get_claude_settings_path()

    if not settings_path.parent.exists():
        return {'status': 'error', 'message': 'Claude config directory not found'}

    # Load existing settings
    settings = {}
    if settings_path.exists():
        with open(settings_path, 'r') as f:
            settings = json.load(f)

    # Ensure hooks section exists
    if 'hooks' not in settings:
        settings['hooks'] = {}

    # Add PreCompact hook
    precompact_hook = {
        "matcher": "auto",
        "hooks": [
            {
                "type": "command",
                "command": "gm-precompact"
            }
        ]
    }

    # Check if already installed
    existing_precompact = settings['hooks'].get('PreCompact', [])
    gm_installed = any(
        'gm-precompact' in str(h.get('hooks', []))
        for h in existing_precompact
    )

    if not gm_installed or force:
        if not existing_precompact:
            settings['hooks']['PreCompact'] = [precompact_hook]
        else:
            # Append to existing
            settings['hooks']['PreCompact'].append(precompact_hook)

    # Save settings
    with open(settings_path, 'w') as f:
        json.dump(settings, f, indent=2)

    return {
        'status': 'installed',
        'settings_path': str(settings_path),
        'hooks_added': ['PreCompact -> gm-precompact'],
    }


def uninstall_claude_hooks() -> Dict:
    """Remove Grey Matter hooks from Claude Code settings."""
    settings_path = get_claude_settings_path()

    if not settings_path.exists():
        return {'status': 'not_found'}

    with open(settings_path, 'r') as f:
        settings = json.load(f)

    # Remove our hooks
    if 'hooks' in settings and 'PreCompact' in settings['hooks']:
        settings['hooks']['PreCompact'] = [
            h for h in settings['hooks']['PreCompact']
            if 'gm-precompact' not in str(h.get('hooks', []))
        ]

        # Clean up empty lists
        if not settings['hooks']['PreCompact']:
            del settings['hooks']['PreCompact']

    with open(settings_path, 'w') as f:
        json.dump(settings, f, indent=2)

    return {'status': 'uninstalled'}


def check_hook_status() -> Dict:
    """Check if Grey Matter hooks are installed in Claude."""
    settings_path = get_claude_settings_path()

    if not settings_path.exists():
        return {'installed': False, 'reason': 'settings_not_found'}

    with open(settings_path, 'r') as f:
        settings = json.load(f)

    precompact_installed = False

    if 'hooks' in settings and 'PreCompact' in settings['hooks']:
        precompact_installed = any(
            'gm-precompact' in str(h.get('hooks', []))
            for h in settings['hooks']['PreCompact']
        )

    return {
        'installed': precompact_installed,
        'precompact': precompact_installed,
    }


# CLI entry points

def precompact_main():
    """CLI entry point for gm-precompact command"""
    try:
        result = save_precompact_state()
        print(f"Grey Matter: Saved {result['items_saved']} items before compaction")
        return 0
    except Exception as e:
        print(f"Grey Matter: PreCompact error - {e}", file=sys.stderr)
        return 1


def resume_main():
    """CLI entry point for gm-resume command"""
    try:
        context = get_resume_context()
        if context:
            print(context)
        else:
            print("Grey Matter: No recent context to resume")
        return 0
    except Exception as e:
        print(f"Grey Matter: Resume error - {e}", file=sys.stderr)
        return 1


def hooks_main():
    """CLI entry point for gm-hooks command"""
    import argparse

    parser = argparse.ArgumentParser(description='Manage Grey Matter Claude hooks')
    parser.add_argument('action', choices=['install', 'uninstall', 'status'],
                       help='Hook management action')
    parser.add_argument('--force', action='store_true',
                       help='Force reinstall hooks')

    args = parser.parse_args()

    if args.action == 'install':
        result = install_claude_hooks(force=args.force)
        print(f"Hooks installed: {result}")
    elif args.action == 'uninstall':
        result = uninstall_claude_hooks()
        print(f"Hooks removed: {result}")
    elif args.action == 'status':
        result = check_hook_status()
        if result['installed']:
            print("Grey Matter hooks: INSTALLED")
            print(f"  - PreCompact: {'Yes' if result['precompact'] else 'No'}")
        else:
            print("Grey Matter hooks: NOT INSTALLED")
            print("Run: gm-hooks install")

    return 0


if __name__ == '__main__':
    hooks_main()
