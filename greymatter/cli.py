#!/usr/bin/env python3
"""
mem - Full-featured memory management CLI for ai++

Usage:
    mem save "User prefers dark mode"           # Save a memory
    mem search "preferences"                     # Search memories
    mem list                                     # List recent memories
    mem handoff "Finished auth feature"          # Create handoff
    mem resume                                   # Resume from last handoff
    mem context                                  # Show current context
    mem stats                                    # Show statistics
    mem agent plan "Add user auth"               # Run plan agent
    mem skill tdd                                # Run TDD skill
    mem triggers                                 # List available triggers
    mem skills                                   # List available skills
    mem agents                                   # List available agents
"""

import sys
import argparse
import json
from datetime import datetime


def cmd_save(args):
    """Save a memory"""
    from .memory import get_memory
    memory = get_memory()

    mem_id = memory.save(
        args.content,
        type=args.type,
        importance=args.importance
    )
    print(f"✓ Saved memory #{mem_id}")


def cmd_search(args):
    """Search memories"""
    from .memory import get_memory
    memory = get_memory()
    results = memory.search(args.query, limit=args.limit)

    if not results:
        print("No memories found.")
        return

    print(f"Found {len(results)} memories:\n")
    for m in results:
        importance_star = "⭐" if m['importance'] >= 7 else ""
        print(f"[{m['id']}] {importance_star}[{m['type']}] {m['content'][:80]}")
        print(f"     Created: {m['created_at'][:16]}\n")


def cmd_list(args):
    """List recent memories"""
    from .memory import get_memory
    memory = get_memory()
    results = memory.get_recent(limit=args.limit)

    if not results:
        print("No memories yet.")
        return

    print(f"Recent memories ({len(results)}):\n")
    for m in results:
        prefix = "⭐" if m['importance'] >= 7 else "•"
        print(f"{prefix} [{m['id']}] [{m['type']}] {m['content'][:70]}")


def cmd_handoff(args):
    """Create a handoff"""
    from .memory import get_memory
    memory = get_memory()

    session_id = f"manual-{int(datetime.now().timestamp())}"
    handoff_id = memory.create_handoff(
        session_id,
        args.summary,
        next_steps=args.next,
        open_questions=args.questions
    )
    print(f"✓ Created handoff #{handoff_id}")


def cmd_resume(args):
    """Resume from last handoff"""
    from .memory import get_memory
    memory = get_memory()

    handoff = memory.get_last_handoff()
    if not handoff:
        print("No previous handoff found.")
        return

    print("=" * 50)
    print("📋 RESUMING FROM PREVIOUS SESSION")
    print("=" * 50)
    print(f"\nDate: {handoff['created_at'][:16]}")
    print(f"\n## Summary\n{handoff['summary']}")

    if handoff.get('next_steps'):
        print(f"\n## Next Steps\n{handoff['next_steps']}")

    if handoff.get('open_questions'):
        print(f"\n## Open Questions\n{handoff['open_questions']}")

    # Also show ledger
    ledger = memory.ledger_get_latest()
    if ledger:
        print(f"\n## Session State")
        print(json.dumps(ledger, indent=2))

    print("\n" + "=" * 50)


def cmd_context(args):
    """Show current memory context"""
    from .memory import get_memory
    memory = get_memory()
    context = memory.build_context(query=args.query)

    if not context:
        print("No context available.")
        return

    print("Current Memory Context:")
    print("=" * 50)
    print(context)


def cmd_stats(args):
    """Show statistics"""
    from .memory import get_memory
    memory = get_memory()
    stats = memory.stats()

    print("\n🧠 ai++ Memory Statistics")
    print("=" * 35)
    for key, value in stats.items():
        print(f"  {key.capitalize():15} {value:>10}")

    handoff = memory.get_last_handoff()
    if handoff:
        print(f"\n  Last handoff: {handoff['created_at'][:16]}")


def cmd_delete(args):
    """Delete a memory"""
    from .memory import get_memory
    memory = get_memory()
    memory.delete(args.id)
    print(f"✓ Deleted memory #{args.id}")


def cmd_clear(args):
    """Clear all memories"""
    if not args.force:
        confirm = input("⚠️  Clear ALL memories? This cannot be undone. (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled.")
            return

    import os
    from .memory import DB_PATH

    try:
        os.remove(DB_PATH)
        print("✓ All memories cleared.")
    except FileNotFoundError:
        print("No memories to clear.")


def cmd_agent(args):
    """Run an agent"""
    from .agents import run_agent, AGENTS

    if args.agent_name not in AGENTS:
        print(f"Unknown agent: {args.agent_name}")
        print(f"Available: {', '.join(AGENTS.keys())}")
        return

    print(f"🤖 Running {args.agent_name} agent...")
    print("=" * 50)

    result = run_agent(args.agent_name, args.task, ai_type=args.ai)

    if result.success:
        print(result.output)
        if result.learnings:
            print("\n📚 Learnings:")
            for l in result.learnings:
                print(f"  • {l}")
    else:
        print(f"❌ Error: {result.error}")


def cmd_skill(args):
    """Run a skill"""
    from .skills import run_skill, list_skills

    if args.skill_name == 'list':
        skills = list_skills()
        print("\n🛠️  Available Skills:")
        print("=" * 35)
        for name, desc in skills.items():
            print(f"  {name:20} {desc[:40]}")
        return

    result = run_skill(args.skill_name, {'cwd': args.cwd} if args.cwd else {})

    if result.success:
        print(f"✓ {result.output}")
        if result.data:
            print(json.dumps(result.data, indent=2))
    else:
        print(f"❌ Error: {result.error}")


def cmd_triggers(args):
    """List available triggers"""
    from .triggers import get_engine

    engine = get_engine()
    print("\n🎯 Available Triggers:")
    print("=" * 50)
    for trigger in engine.triggers:
        print(f"\n  {trigger.name}")
        print(f"    {trigger.description}")
        print(f"    Patterns: {[p.pattern for p in trigger.patterns[:2]]}")


def cmd_agents(args):
    """List available agents"""
    from .agents import AGENTS

    print("\n🤖 Available Agents:")
    print("=" * 50)
    for name, agent_class in AGENTS.items():
        agent = agent_class()
        print(f"\n  {name}")
        print(f"    {agent.description}")


def cmd_skills(args):
    """List available skills"""
    from .skills import list_skills

    skills = list_skills()
    print("\n🛠️  Available Skills:")
    print("=" * 50)
    for name, desc in skills.items():
        print(f"  {name:20} {desc}")


def cmd_git(args):
    """Git integration commands"""
    from .git_integration import get_git_integration

    git = get_git_integration()

    if not git.is_git_repo():
        print("Not a git repository.")
        return

    if args.git_action == 'history':
        commits = git.get_commit_history_with_reasoning(limit=args.limit)
        print("\n📜 Commit History with Reasoning:")
        print("=" * 50)
        for c in commits:
            print(f"\n  {c['hash'][:8]} {c['message'][:50]}")
            if c['reasoning']:
                for entry in c['reasoning'].get('entries', [])[:2]:
                    if entry.get('message'):
                        print(f"    💭 {entry['message'][:60]}")

    elif args.git_action == 'search':
        results = git.search_reasoning(args.query)
        print(f"\n🔍 Found {len(results)} reasoning entries:")
        for r in results:
            print(f"\n  Commit: {r['commit'][:8]}")
            print(f"  {r['entry'].get('message', '')[:80]}")

    elif args.git_action == 'annotate':
        git.annotate_commit(args.message)
        print("✓ Annotated current commit")


def cmd_optimize(args):
    """Smart memory optimization commands"""
    from .smart import get_optimizer, TokenCounter

    optimizer = get_optimizer()

    if args.optimize_action == 'stats':
        stats = optimizer.get_stats()
        print("\n🧠 Smart Memory Statistics")
        print("=" * 40)
        print(f"  Total memories:     {stats['total_memories']:>8}")
        print(f"  Total tokens:       {stats['total_tokens']:>8}")
        print(f"  Avg tokens/memory:  {stats['avg_tokens_per_memory']:>8}")
        print(f"\n  Memory Tiers:")
        print(f"    🔥 Hot (recent/important):  {stats['hot_memories']:>5}")
        print(f"    🌡️  Warm (moderate):         {stats['warm_memories']:>5}")
        print(f"    ❄️  Cold (old/low-value):    {stats['cold_memories']:>5}")

    elif args.optimize_action == 'context':
        context, stats = optimizer.get_optimized_context(query=args.query)
        print("\n📦 Optimized Context")
        print("=" * 40)
        print(f"  Memories included: {stats['included_memories']}/{stats['total_memories']}")
        print(f"  Tokens used:       {stats['tokens_used']}")
        print(f"  Tokens saved:      {stats['tokens_saved']}")
        print(f"  Compressed:        {stats['compressed']}")
        print(f"  Deduplicated:      {stats['deduplicated']}")
        if args.show:
            print("\n" + "-" * 40)
            print(context)

    elif args.optimize_action == 'cleanup':
        if not args.force:
            confirm = input("Clean up old/low-value memories? (yes/no): ")
            if confirm.lower() != 'yes':
                print("Cancelled.")
                return
        result = optimizer.cleanup_old_memories(
            max_age_days=args.days,
            min_importance=args.min_importance
        )
        print(f"\n🧹 Cleanup Complete")
        print(f"  Deleted: {result['deleted']} memories")
        print(f"  Archived: {result['archived']} memories")
        print(f"  Tokens freed: ~{result['tokens_freed']}")

    elif args.optimize_action == 'analyze':
        content = args.text
        tokens = TokenCounter.count(content)
        from .smart import TextCompressor, SimilarityDetector
        compressed = TextCompressor.compress(content)
        compressed_tokens = TokenCounter.count(compressed)

        print(f"\n📊 Text Analysis")
        print("=" * 40)
        print(f"  Original tokens:   {tokens}")
        print(f"  Compressed tokens: {compressed_tokens}")
        print(f"  Savings:           {tokens - compressed_tokens} ({(1 - compressed_tokens/max(1,tokens))*100:.1f}%)")
        print(f"\n  Compressed text:")
        print(f"  {compressed[:200]}...")


def main():
    parser = argparse.ArgumentParser(
        description='mem - ai++ Memory Management CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  mem save "User prefers TypeScript" -i 8
  mem search "preferences"
  mem agent plan "Add user authentication"
  mem skill tdd
  mem resume
        """
    )
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # save
    p = subparsers.add_parser('save', help='Save a memory')
    p.add_argument('content', help='Content to remember')
    p.add_argument('-t', '--type', default='learning', help='Memory type')
    p.add_argument('-i', '--importance', type=int, default=5, help='Importance (1-10)')

    # search
    p = subparsers.add_parser('search', help='Search memories')
    p.add_argument('query', help='Search query')
    p.add_argument('-l', '--limit', type=int, default=10)

    # list
    p = subparsers.add_parser('list', help='List recent memories')
    p.add_argument('-l', '--limit', type=int, default=20)

    # handoff
    p = subparsers.add_parser('handoff', help='Create a handoff')
    p.add_argument('summary', help='Session summary')
    p.add_argument('-n', '--next', help='Next steps')
    p.add_argument('-q', '--questions', help='Open questions')

    # resume
    subparsers.add_parser('resume', help='Resume from last handoff')

    # context
    p = subparsers.add_parser('context', help='Show memory context')
    p.add_argument('query', nargs='?', help='Optional query')

    # stats
    subparsers.add_parser('stats', help='Show statistics')

    # delete
    p = subparsers.add_parser('delete', help='Delete a memory')
    p.add_argument('id', type=int, help='Memory ID')

    # clear
    p = subparsers.add_parser('clear', help='Clear all memories')
    p.add_argument('-f', '--force', action='store_true')

    # agent
    p = subparsers.add_parser('agent', help='Run an agent')
    p.add_argument('agent_name', help='Agent name (plan, research, debug, validate, code, review, explorer)')
    p.add_argument('task', help='Task for the agent')
    p.add_argument('--ai', default='claude', help='AI to use')

    # skill
    p = subparsers.add_parser('skill', help='Run a skill')
    p.add_argument('skill_name', help='Skill name (or "list")')
    p.add_argument('--cwd', help='Working directory')

    # triggers
    subparsers.add_parser('triggers', help='List triggers')

    # agents
    subparsers.add_parser('agents', help='List agents')

    # skills
    subparsers.add_parser('skills', help='List skills')

    # git
    p = subparsers.add_parser('git', help='Git integration')
    p.add_argument('git_action', choices=['history', 'search', 'annotate'])
    p.add_argument('--query', '-q', help='Search query')
    p.add_argument('--message', '-m', help='Annotation message')
    p.add_argument('--limit', '-l', type=int, default=10)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        'save': cmd_save,
        'search': cmd_search,
        'list': cmd_list,
        'handoff': cmd_handoff,
        'resume': cmd_resume,
        'context': cmd_context,
        'stats': cmd_stats,
        'delete': cmd_delete,
        'clear': cmd_clear,
        'agent': cmd_agent,
        'skill': cmd_skill,
        'triggers': cmd_triggers,
        'agents': cmd_agents,
        'skills': cmd_skills,
        'git': cmd_git,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        try:
            cmd_func(args)
            return 0
        except Exception as e:
            print(f"Error: {e}")
            return 1

    parser.print_help()
    return 1


if __name__ == '__main__':
    sys.exit(main())
