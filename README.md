<p align="center">
  <img src="assets/logo.png" alt="Grey Matter" width="128" height="128">
</p>

<h1 align="center">Grey Matter</h1>

<p align="center">
  <strong>Give your AI a brain that actually remembers.</strong>
</p>

<p align="center">
  <a href="#installation"><img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="Python 3.8+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT License"></a>
  <a href="#"><img src="https://img.shields.io/badge/dependencies-zero-brightgreen.svg" alt="Zero Dependencies"></a>
  <a href="#"><img src="https://img.shields.io/badge/tests-33%20passing-success.svg" alt="Tests Passing"></a>
</p>

<p align="center">
  <a href="#installation">Installation</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#features">Features</a> •
  <a href="#how-it-works">How It Works</a> •
  <a href="#commands">Commands</a>
</p>

---

## The Problem

Every time you start a new chat with Claude, Gemini, or Ollama:

```
You: "Remember, I prefer TypeScript and use 2-space indentation"
AI:  "Got it!"

[Next session]

You: "What are my coding preferences?"
AI:  "I don't have any information about your preferences."
```

**Your AI has amnesia.**

## The Solution

```bash
pip install greymatter-ai
claude++
```

That's it. Now your AI remembers **everything**—automatically.

```
You: "I prefer TypeScript and 2-space indentation"
AI:  "Got it!"

[Next session, next week, next month]

You: "What are my preferences?"
AI:  "You prefer TypeScript with 2-space indentation."
```

---

## Quick Start

```bash
# Install
pip install git+https://github.com/AndroidPoet/greymatter.git

# Run (that's it!)
claude++     # or gemini++ or ollama++
```

No configuration. No commands to learn. Just talk naturally.

---

## Features

| Feature | What it does |
|---------|--------------|
| 🧠 **Human-Like Memory** | Remembers like you do—important stuff sticks, trivial stuff fades |
| 🔍 **Semantic Search** | Finds memories by *meaning*, not just keywords |
| 📁 **Project Memory** | Different project? Different memories. Auto-switches when you `cd` |
| 🔮 **Predictive Loading** | Pre-loads memories you'll probably need |
| ♻️ **Clear & Resume** | Context full? Use `/clear`. Resume seamlessly—nothing lost |
| ⚡ **Zero Config** | Works out of the box. No API keys, no setup |
| 🪶 **Zero Dependencies** | Pure Python stdlib. Optional neural embeddings |

---

## How It Works

Grey Matter wraps your AI CLI with a memory layer modeled after human cognition:

```
                         ┌─────────────────┐
                         │   You speak     │
                         └────────┬────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│  👁️  PERCEPTION                                              │
│      Analyzes intent, emphasis, importance                  │
└─────────────────────────────────────────────────────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│  🎯 ATTENTION                                                │
│      Focuses on what matters (like "ALWAYS" or "I prefer") │
└─────────────────────────────────────────────────────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│  💾 ENCODING                                                 │
│      Important → Long-term memory                           │
│      Trivial → Forgotten                                    │
└─────────────────────────────────────────────────────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│  🔄 RECALL                                                   │
│      Relevant memories surface automatically                │
└─────────────────────────────────────────────────────────────┘
```

### The "Clear, Don't Compact" Philosophy

When AI context gets full, most tools try to summarize. **Summarization loses information.**

Grey Matter does it differently:

1. **Save** everything important to persistent memory
2. **Clear** the context completely
3. **Resume** with a handoff containing exactly what you need

Result: Fresh context, zero information loss.

---

## Commands

### Primary

```bash
claude++     # Claude with memory
gemini++     # Gemini with memory
ollama++     # Ollama with memory
```

### Memory Management (Optional)

```bash
mem stats              # 📊 Memory statistics
mem list               # 📋 Recent memories
mem search "auth"      # 🔍 Search memories
mem forget "secret"    # 🗑️ Forget something
mem-viz                # 🌐 Visual memory graph (opens browser)
```

---

## Installation

### From GitHub (Recommended)

```bash
pip install git+https://github.com/AndroidPoet/greymatter.git
```

### From Source

```bash
git clone https://github.com/AndroidPoet/greymatter.git
cd greymatter
pip install -e .
```

### Optional: Neural Embeddings

For even better semantic search:

```bash
pip install greymatter-ai[neural]
```

### Prerequisites

You need at least one AI CLI installed:

```bash
# Claude Code
npm install -g @anthropic-ai/claude-code

# Gemini
pip install google-generativeai

# Ollama
brew install ollama
```

---

## What Gets Remembered?

Grey Matter automatically detects and remembers:

| Type | Examples |
|------|----------|
| **Preferences** | "I prefer dark mode", "Always use TypeScript" |
| **Decisions** | "We decided to use PostgreSQL", "Going with REST over GraphQL" |
| **Learnings** | "TIL the API uses JWT", "Found out the bug was in auth" |
| **Important Info** | "IMPORTANT: Never commit .env", "The prod server is 10.0.0.1" |
| **Problems & Solutions** | "Fixed the memory leak by...", "The issue was caused by..." |

Things that get forgotten:
- Small talk ("ok", "thanks", "sure")
- Repeated information (deduplication)
- Old, unaccessed memories (natural decay)

---

## Project Isolation

Grey Matter automatically isolates memory per project:

```bash
cd ~/work/api-project
claude++
# Memories: API endpoints, database schema, auth flow

cd ~/personal/blog
claude++
# Different memories: Blog structure, writing style, deploy process
```

No commands needed. Just `cd` and it switches.

---

## Data & Privacy

**Your data stays local.** Always.

```
~/.greymatter/
├── memory.db          # SQLite database (your memories)
└── projects/          # Per-project memories
    ├── api-project.db
    └── blog.db
```

- No cloud sync
- No telemetry
- No API calls (except to your chosen AI)
- Everything in `~/.greymatter/`

---

## Troubleshooting

### Commands not found

```bash
# Add to ~/.zshrc or ~/.bashrc:
export PATH="$HOME/.local/bin:$PATH"
source ~/.zshrc
```

### Memory not persisting

```bash
# Check data directory:
ls ~/.greymatter/
```

### Not resuming after /clear

Exit cleanly with `Ctrl+C` (saves handoff):

```bash
claude++          # Use normally
# Ctrl+C          # Saves state
claude++          # Shows "RESUMING FROM PREVIOUS SESSION"
```

---

## Architecture

```
greymatter/
├── brain.py           # 🧠 Human-like memory orchestrator
├── understanding.py   # 🔍 Intent & emphasis detection
├── memory.py          # 💾 SQLite + FTS5 storage
├── embeddings.py      # 🎯 TF-IDF / neural semantic search
├── context_manager.py # ♻️ Clear/resume flow
├── projects.py        # 📁 Per-project isolation
├── prediction.py      # 🔮 Context prediction
├── smart.py           # ⚡ Token optimization
├── wrapper.py         # 🔌 CLI wrapper
└── visualize.py       # 🌐 Memory graph UI
```

---

## Safety & Security

✅ **Safe to use:**
- No network calls except to your AI CLI
- No data leaves your machine
- No tracking or analytics
- Open source—read the code

✅ **Code quality:**
- 33 tests passing
- Type hints throughout
- No external dependencies (stdlib only)
- Optimized (indexed DB, bounded caches, O(log n) operations)

---

## Inspired By

- [Continuous-Claude](https://github.com/parcadei/Continuous-Claude) — The "clear, don't compact" philosophy
- Human memory systems — Working memory, encoding, consolidation, retrieval

---

## License

MIT — Use it however you want.

---

<p align="center">
  <sub>Built for developers who are tired of repeating themselves.</sub>
</p>
