# Vector Memory System

Viktor's FAISS-based semantic memory system with automatic context recovery.

## Components

### Core Files

- **`memory_store.py`** — VectorMemory class with FAISS index, sentence-transformers (all-MiniLM-L6-v2), search, add, dedup
- **`ingest_memories.py`** — Indexes markdown memory files + JSONL chat sessions from both `.openclaw` and `.clawdbot`
- **`context_injector.py`** — Daemon that automatically generates `CONTEXT_RECOVERY.md` when Viktor's context gets compacted

### Installation Location

These files should be deployed to: `~/clawd/vector-memory/`

A Python virtualenv with the following dependencies must be set up at `~/clawd/vector-memory/venv/`:
- `faiss-cpu`
- `sentence-transformers`

## Setup

```bash
# Create directory and virtualenv
mkdir -p ~/clawd/vector-memory
cd ~/clawd/vector-memory
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install faiss-cpu sentence-transformers

# Copy files from repo
cp /path/to/viktor/vector-memory/*.py ~/clawd/vector-memory/

# Initial memory ingestion
python3 ingest_memories.py

# Test context injector
python3 context_injector.py
```

## Usage

### Manual Memory Indexing

```bash
cd ~/clawd/vector-memory
source venv/bin/activate
python3 ingest_memories.py
```

This will:
- Index all markdown files from `~/clawd/memory/`
- Index all JSONL sessions from `~/.openclaw/agents/main/sessions/`
- Index all JSONL sessions from `~/.clawdbot/agents/main/sessions/`

### Context Injector

```bash
# Single run
python3 context_injector.py

# Daemon mode (default 60s interval)
python3 context_injector.py --daemon

# Every 2 minutes
python3 context_injector.py --daemon --interval 120

# Force (ignore race condition check)
python3 context_injector.py --force
```

### LaunchAgent (Automatic)

See `infrastructure/launchd/README.md` for installation instructions.

## Context Recovery Flow

1. OpenClaw compacts Viktor's context (messages get truncated)
2. Context injector daemon (running every 2 minutes):
   - Parses most recent session JSONL
   - Extracts last 15 real messages (filters noise)
   - Queries FAISS for semantic context
   - Writes `~/clawd/CONTEXT_RECOVERY.md`
3. Viktor wakes up in new session
4. Reads and deletes `CONTEXT_RECOVERY.md` (per `AGENTS.md`)
5. Has continuity despite context compaction!

## Memory Sources

- Daily notes: `~/clawd/memory/YYYY-MM-DD.md`
- Long-term memory: `~/clawd/MEMORY.md`
- OpenClaw sessions: `~/.openclaw/agents/main/sessions/*.jsonl`
- Legacy Clawdbot sessions: `~/.clawdbot/agents/main/sessions/*.jsonl`

## Logs

- Context injector: `~/clawd/vector-memory/context_injector.log`
- Reindex cron: `~/clawd/vector-memory/reindex.log`
- LaunchAgent stdout: `~/clawd/vector-memory/context-injector.stdout.log`
- LaunchAgent stderr: `~/clawd/vector-memory/context-injector.stderr.log`
