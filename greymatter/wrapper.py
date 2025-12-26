#!/usr/bin/env python3
"""
Grey Matter Wrapper - Ultimate AI CLI with Human-Like Memory

FULLY AUTOMATIC with "Clear, Don't Compact" Philosophy!
- Automatically remembers important things
- Automatically recalls relevant context (semantic search)
- Automatically switches project context
- Tracks context fullness in real-time
- Creates handoffs before context overflow
- Resumes seamlessly after /clear
- Just like human memory!

Usage:
    claude++          # Just run it - EVERYTHING is automatic
    gemini++          # Same for Gemini
    ollama++ llama3   # Same for Ollama
"""

import subprocess
import sys
import os
import signal
import atexit
import pty
import select
import time
from pathlib import Path
from typing import Optional

from .brain import get_brain
from .projects import get_project_memory, ProjectDetector
from .prediction import get_prefetch
from .embeddings import get_semantic_search
from .context_manager import get_context_manager, ContextState
from .session import get_session_manager


# Global state
_ai_type = 'claude'
_session_id = None


def detect_ai_cli() -> str:
    """Detect which AI CLI to use"""
    script_name = Path(sys.argv[0]).stem

    if 'claude' in script_name:
        return 'claude'
    elif 'gemini' in script_name:
        return 'gemini'
    elif 'ollama' in script_name:
        return 'ollama'
    elif 'gpt' in script_name:
        return 'gpt'
    elif len(sys.argv) > 1 and sys.argv[1] in ('claude', 'gemini', 'ollama', 'gpt'):
        return sys.argv.pop(1)
    return 'claude'


def check_cli_exists(cli_name: str) -> bool:
    """Check if CLI exists"""
    try:
        subprocess.run([cli_name, '--version'], capture_output=True, timeout=5)
        return True
    except (subprocess.SubprocessError, FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False


def build_auto_context(include_resume: bool = True) -> str:
    """Build context automatically - ALL features combined"""
    global _ai_type

    parts = []

    # 0. CHECK FOR RESUME FROM HANDOFF
    if include_resume:
        ctx_mgr = get_context_manager(_ai_type)
        resume_context = ctx_mgr.get_resume_context()
        if resume_context:
            parts.append(resume_context)

    # 1. AUTO PROJECT DETECTION
    project = ProjectDetector.detect()
    if project:
        parts.append(f"## Current Project: {project.name}")
        parts.append(f"Path: {project.root}")

    # 2. AUTO PROJECT MEMORY (switches automatically per folder!)
    project_mem = get_project_memory()
    project_context = project_mem.build_context()
    if project_context:
        parts.append(project_context)

    # 3. AUTO BRAIN RECALL (semantic understanding)
    brain = get_brain()
    brain_context = brain.recall()
    if brain_context:
        parts.append(brain_context)

    # 4. AUTO PREDICTION (pre-fetched relevant memories)
    prefetch = get_prefetch()
    prefetch.prefetch({'directory': os.getcwd()})
    predicted = prefetch.get_predicted_context({'directory': os.getcwd()})
    if predicted:
        parts.append(predicted)

    if not parts:
        return ""

    context = "\n\n".join(parts)

    return f"""<memory>
{context}

---
Memory is FULLY AUTOMATIC:
- Project context auto-switches when you change folders
- Semantic search finds related memories (not just keywords)
- Important things are remembered automatically
- Context tracked in real-time (warns before overflow)
- Use /clear when context is full - I'll resume seamlessly!
- Just talk naturally - no commands needed!
</memory>
"""


def show_brain_status(resuming: bool = False):
    """Show brain status on startup"""
    global _ai_type

    brain = get_brain()
    state = brain.get_state()
    ctx_mgr = get_context_manager(_ai_type)

    # Project detection
    project = ProjectDetector.detect()

    print("=" * 60)
    print("🧠 Grey Matter - Human-Like Memory with Clear/Resume Support")
    print("=" * 60)

    # Resume indicator
    if resuming:
        print("\n  🔄 RESUMING FROM PREVIOUS SESSION")
        print("     All context and memories preserved!")

    # Context status
    ctx_status = ctx_mgr.get_status()
    print(f"\n  {ctx_mgr.get_context_indicator()}")

    # Project info
    if project:
        print(f"\n  📁 Project: {project.name}")
        types = []
        if project.is_git: types.append("Git")
        if project.is_npm: types.append("Node")
        if project.is_python: types.append("Python")
        if types:
            print(f"     Type: {', '.join(types)}")

    # Memory stats
    print(f"\n  🧠 Working memory: {state['working_memory']} items")
    print(f"  💾 Long-term: {state['long_term_memories']} memories")

    if state['long_term_memories'] > 0:
        print(f"\n  Health: 🔥{state['memory_health']['active']} "
              f"🌡️{state['memory_health']['fading']} "
              f"❄️{state['memory_health']['old']}")

    print("\n" + "=" * 60)
    print("  ✨ FEATURES (All Automatic):")
    print("  • Memory auto-switches per project")
    print("  • Semantic search (meaning, not keywords)")
    print("  • Context tracking (warns before overflow)")
    print("  • Clear/Resume (use /clear, I'll remember)")
    print("=" * 60 + "\n")


def create_exit_handoff():
    """Create handoff on exit for seamless resume"""
    global _session_id

    ctx_mgr = get_context_manager(_ai_type)
    session_mgr = get_session_manager()
    brain = get_brain()

    if ctx_mgr.metrics.message_count > 0:
        print("\n💾 Creating handoff for next session...")

        # Get brain state for learnings
        brain_state = brain.get_state()

        ctx_mgr.prepare_handoff(
            current_task="Session ended - ready to resume",
            learnings=brain_state.get('recent_learnings', []),
            next_steps=["Continue from where we left off"],
        )

        print("✓ Handoff saved - will resume automatically next time!")


def cleanup():
    """Cleanup on exit - consolidate memories and create handoff"""
    create_exit_handoff()

    brain = get_brain()
    brain.stop()  # Stop brain (consolidation happens in stop)


def handle_sigint(signum, frame):
    """Handle Ctrl+C"""
    print("\n\n🧠 Saving state before exit...")
    cleanup()
    print("Done! Goodbye!")
    sys.exit(130)


def run_with_pty(cmd: list) -> int:
    """
    Run command with PTY for real-time I/O capture

    This allows us to:
    - Track messages in real-time
    - Detect context fullness
    - Inject warnings when needed
    """
    global _ai_type

    ctx_mgr = get_context_manager(_ai_type)
    brain = get_brain()

    # Buffer for tracking output
    output_buffer = []
    input_buffer = []

    def master_read(fd):
        """Read from master (AI output)"""
        data = os.read(fd, 10240)
        if data:
            text = data.decode('utf-8', errors='replace')
            output_buffer.append(text)

            # Track AI responses (simple heuristic: multiline output = response)
            if '\n' in text and len(text) > 50:
                ctx_mgr.record_ai_response(text)

                # Check if we need to warn about context
                if ctx_mgr.should_prepare_handoff() and not ctx_mgr.handoff_ready:
                    ctx_mgr.prepare_handoff(
                        current_task="In progress",
                        next_steps=["Continue current task"]
                    )

        return data

    def stdin_read(fd):
        """Read from stdin (user input)"""
        data = os.read(fd, 10240)
        if data:
            text = data.decode('utf-8', errors='replace')
            input_buffer.append(text)

            # Track user messages
            if text.strip():
                ctx_mgr.record_user_message(text)

                # Let brain perceive the input
                brain.perceive(text)

        return data

    try:
        # Use pty.spawn for interactive session with callbacks
        return pty.spawn(cmd, master_read)
    except Exception as e:
        # Fallback to simple subprocess if PTY fails
        print(f"(PTY failed: {e}, using simple mode)")
        result = subprocess.run(cmd, cwd=os.getcwd())
        return result.returncode


def run_simple(cmd: list) -> int:
    """Simple subprocess run (fallback)"""
    try:
        result = subprocess.run(cmd, cwd=os.getcwd())
        return result.returncode
    except KeyboardInterrupt:
        return 130


def run_claude(args: list) -> int:
    """Run Claude with automatic memory"""
    context = build_auto_context()

    cmd = ['claude']
    if context:
        cmd.extend(['--system-prompt', context[:8000]])
    cmd.extend(args)

    # Use PTY for real-time tracking
    return run_with_pty(cmd)


def run_gemini(args: list) -> int:
    """Run Gemini with automatic memory"""
    context = build_auto_context()

    cmd = ['gemini']

    # Gemini CLI doesn't support system instructions directly
    # Use --prompt-interactive to inject context as first message
    if context and not any(a in args for a in ['-p', '--prompt', '-i', '--prompt-interactive']):
        # Prepend context as interactive prompt
        context_prompt = f"[Memory Context]\n{context[:4000]}\n\n[Ready for your questions]"
        cmd.extend(['--prompt-interactive', context_prompt])

    cmd.extend(args)

    return run_with_pty(cmd)


def run_ollama(args: list) -> int:
    """Run Ollama with automatic memory"""
    context = build_auto_context()

    cmd = ['ollama', 'run']
    if not args or not any(a for a in args if not a.startswith('-')):
        cmd.append('llama3')
    cmd.extend(args)

    if context:
        cmd.extend(['--system', context[:4000]])

    return run_with_pty(cmd)


def main():
    """Main entry - fully automatic with clear/resume support!"""
    global _ai_type, _session_id

    # Setup
    signal.signal(signal.SIGINT, handle_sigint)
    atexit.register(cleanup)

    _ai_type = detect_ai_cli()
    args = sys.argv[1:]

    # Check CLI
    if not check_cli_exists(_ai_type):
        print(f"Error: {_ai_type} not found")
        print("\nInstall:")
        print("  Claude: npm i -g @anthropic-ai/claude-code")
        print("  Gemini: pip install google-generativeai")
        print("  Ollama: brew install ollama")
        return 1

    # Initialize context manager and check for resume
    ctx_mgr = get_context_manager(_ai_type)
    session_mgr = get_session_manager()

    # Start session and check for handoff
    from .memory import get_memory
    memory = get_memory()
    _session_id = memory.start_session(_ai_type, os.getcwd())

    resume_info = ctx_mgr.start_session(_session_id)
    resuming = resume_info.get('resuming', False)

    # Show brain status
    show_brain_status(resuming=resuming)

    # Run
    runners = {
        'claude': run_claude,
        'gemini': run_gemini,
        'ollama': run_ollama,
    }

    try:
        result = runners.get(_ai_type, run_claude)(args)
        return result
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
