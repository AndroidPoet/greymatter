# Grey Matter

**Human-Like Memory for AI CLIs**

Give Claude, Gemini, and Ollama a brain that remembers everything—automatically.

```bash
# Install
pip install greymatter-ai

# Use (that's it!)
claude++
```

## What It Does

Grey Matter wraps your AI CLI with a memory layer that works like a human brain:

- **Remembers** important things automatically (preferences, decisions, learnings)
- **Forgets** unimportant stuff over time
- **Recalls** relevant context when you need it
- **Switches** memory per project (cd to different folder = different context)
- **Resumes** seamlessly after `/clear` (no lost context!)

No commands needed. Just talk naturally.

## Features

| Feature | Description |
|---------|-------------|
| **Human-Like Memory** | Working memory (7 items) → Long-term encoding → Consolidation |
| **Semantic Search** | Finds by meaning, not just keywords |
| **Per-Project Memory** | Auto-switches when you `cd` to different projects |
| **Context Prediction** | Pre-loads what you'll likely need |
| **Clear/Resume** | Use `/clear` when context is full—resumes automatically |
| **Token Optimization** | Compresses, deduplicates, tiers memories |
| **Zero Dependencies** | Pure Python stdlib (optional: neural embeddings) |
| **Works with Any AI** | Claude, Gemini, Ollama, and more |

## Installation

### Quick Install (pip)

```bash
pip install greymatter-ai
```

### From Source

```bash
git clone https://github.com/greymatter-ai/greymatter.git
cd greymatter
pip install -e .
```

### Optional: Neural Embeddings

For better semantic search (uses sentence-transformers):

```bash
pip install -e ".[neural]"
```

## Usage

### Just Run It

```bash
claude++     # Claude with memory
gemini++     # Gemini with memory
ollama++     # Ollama with memory
```

That's it. Everything is automatic:
- Important things are remembered
- Relevant context surfaces automatically
- Project memory switches when you `cd`
- Old unimportant stuff fades away

### Memory Management (optional)

```bash
mem stats              # Show memory statistics
mem list               # List recent memories
mem search "query"     # Search memories
mem forget "query"     # Forget something
mem-viz                # Open visualization in browser
```

### When Context Gets Full

1. Grey Matter tracks context usage in real-time
2. Shows warning when approaching limit
3. Auto-creates handoff with all important state
4. You run `/clear` in your AI CLI
5. Next time you run `claude++`, it resumes automatically!

## How It Works

```
┌─────────────────────────────────────────────────────┐
│                    YOU TALK                          │
└─────────────────────┬───────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────┐
│  PERCEPTION → Analyzes meaning (intent, emphasis)    │
└─────────────────────┬───────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────┐
│  ATTENTION → Focuses on important information        │
└─────────────────────┬───────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────┐
│  ENCODING → Stores to long-term if memorable         │
└─────────────────────┬───────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────┐
│  RECALL → Surfaces relevant memories automatically   │
└─────────────────────────────────────────────────────┘
```

### Memory Types

- **Sensory** → Brief, mostly filtered out
- **Working** → Short-term, ~7 items (Miller's Law)
- **Episodic** → Events and experiences
- **Semantic** → Facts and knowledge
- **Procedural** → How-to and skills

### The "Clear, Don't Compact" Philosophy

When AI context gets full, most tools try to compress/summarize. This loses information.

Grey Matter takes a different approach:
1. **Save everything important** to persistent memory
2. **Clear the context** completely
3. **Resume with handoff** containing exactly what you need

Result: No information loss, fresh context, seamless continuation.

## Architecture

```
greymatter/
├── brain.py          # Human-like memory system
├── understanding.py  # Semantic analysis (intent, emphasis)
├── memory.py         # SQLite + FTS5 storage
├── smart.py          # Token optimization
├── embeddings.py     # TF-IDF + optional neural search
├── projects.py       # Per-project memory isolation
├── prediction.py     # Context prediction & prefetch
├── context_manager.py # Clear/resume flow
├── visualize.py      # Memory graph web UI
├── wrapper.py        # CLI wrapper (claude++, etc.)
├── session.py        # Session lifecycle
├── hooks.py          # Event hooks
├── agents.py         # Specialized agents
├── triggers.py       # Natural language triggers
└── skills.py         # Quick utilities
```

## Configuration

Grey Matter works out of the box with zero configuration. But you can customize:

```bash
# Environment variables
export GREYMATTER_DATA_DIR="~/.greymatter"  # Data location
export GREYMATTER_USE_NEURAL=1              # Enable neural embeddings
```

## Data Storage

All data stored locally in `~/.greymatter/`:

```
~/.greymatter/
├── memory.db          # Main SQLite database
├── projects/          # Per-project databases
│   ├── my-app.db
│   └── other-project.db
└── config.json        # Optional config
```

## Requirements

- Python 3.8+
- One of: Claude CLI, Gemini CLI, or Ollama
- No other dependencies (neural embeddings optional)

## CLI Installation

Grey Matter wraps these AI CLIs:

```bash
# Claude Code
npm install -g @anthropic-ai/claude-code

# Gemini
pip install google-generativeai

# Ollama
brew install ollama  # or see ollama.ai
```

## Troubleshooting

### Commands not found after install

Add to your `~/.zshrc` or `~/.bashrc`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Then: `source ~/.zshrc`

### Memory not persisting

Check data directory exists:

```bash
ls ~/.greymatter/
```

### Context not resuming after /clear

Ensure you exit cleanly (Ctrl+C saves state):

```bash
claude++  # Use normally
# Press Ctrl+C to exit (saves handoff)
claude++  # Should show "RESUMING FROM PREVIOUS SESSION"
```

## Inspired By

- [Continuous-Claude](https://github.com/parcadei/Continuous-Claude) — "Clear, don't compact" philosophy
- Human memory systems — Working memory, encoding, consolidation, retrieval

## License

MIT
