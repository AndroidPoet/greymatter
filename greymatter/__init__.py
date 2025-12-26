"""
ai++ - Universal Memory Layer for AI CLIs

The ultimate memory system that works with any AI CLI.
Makes Claude, Gemini, Ollama, and any other AI remember everything.

Features:
- SQLite + FTS5 persistent memory (zero dependencies)
- Session lifecycle management (4 phases)
- Hooks system for extensibility
- Specialized agents (plan, research, debug, validate, review, explore)
- Natural language triggers
- Git integration for reasoning history
- Skills for quick utilities
- Auto-learning extraction

Usage:
    claude++     # Run Claude with memory
    gemini++     # Run Gemini with memory
    ollama++     # Run Ollama with memory
    mem          # Memory management CLI
"""

from .memory import Memory, get_memory, DATA_DIR, DB_PATH
from .session import SessionManager, get_session_manager, SessionPhase
from .hooks import HookRegistry, get_registry, hook
from .agents import AGENTS, get_agent, run_agent
from .triggers import TriggerEngine, get_engine, process_triggers
from .skills import run_skill, list_skills, skill
from .git_integration import GitIntegration, get_git_integration
from .smart import MemoryOptimizer, get_optimizer, TokenCounter, SmartContextBuilder
from .brain import Brain, get_brain, think, recall, dream

__version__ = '1.0.0'
__all__ = [
    # Memory
    'Memory', 'get_memory', 'DATA_DIR', 'DB_PATH',
    # Session
    'SessionManager', 'get_session_manager', 'SessionPhase',
    # Hooks
    'HookRegistry', 'get_registry', 'hook',
    # Agents
    'AGENTS', 'get_agent', 'run_agent',
    # Triggers
    'TriggerEngine', 'get_engine', 'process_triggers',
    # Skills
    'run_skill', 'list_skills', 'skill',
    # Git
    'GitIntegration', 'get_git_integration',
]
