# Quick Start Guide - Context Optimization

## What Was Done

Viktor's context files have been optimized to reduce token usage by ~12,200 tokens per message (78% reduction on core files):

- **VIKTOR_BACKSTORY.md**: 51KB → 6.6KB (87% reduction)
- **TOOLS.md**: 11.4KB → 7KB (38% reduction)

Full versions are preserved and accessible via FAISS vector memory.

## Immediate Next Steps

### 1. Ingest Backstory into FAISS (5 minutes)

```bash
cd ~/clawd
./scripts/ingest_backstory_to_faiss.py
```

This chunks the full backstory and adds it to your FAISS index with source tag `backstory:VIKTOR_BACKSTORY`.

### 2. Test Recall System (2 minutes)

```bash
# Search backstory
./scripts/recall.py --backstory "María Elena"
./scripts/recall.py --backstory "Father Miguel"
./scripts/recall.py --backstory "football"

# Search all memories
./scripts/recall.py "ISO certification"
```

### 3. Test Memory Management (5 minutes)

```bash
# Dry-run to see what would happen
./scripts/rotate_memory.py --dry-run
./scripts/summarize_daily_memories.py --dry-run

# If results look good, run for real
./scripts/rotate_memory.py
./scripts/summarize_daily_memories.py
```

### 4. Install Cron Jobs (2 minutes)

```bash
crontab -e
```

Add these lines:

```cron
# Memory rotation — weekly (Sunday 3am Dubai time)
0 3 * * 0 /Users/victor/clawd/vector-memory/venv/bin/python3 /Users/victor/clawd/scripts/rotate_memory.py >> /Users/victor/clawd/logs/rotate_memory.log 2>&1

# Daily memory summarization — daily (4am Dubai time)
0 4 * * * /Users/victor/clawd/vector-memory/venv/bin/python3 /Users/victor/clawd/scripts/summarize_daily_memories.py >> /Users/victor/clawd/logs/summarize_daily.log 2>&1
```

## How to Use

### When You Need Details

The condensed files now have routing tables pointing to full content:

```bash
# For X/Twitter details
cat tools-reference/twitter.md

# For selfie generation templates
cat tools-reference/selfie-templates.md

# For voice message examples
cat tools-reference/voice-examples.md

# For backstory details
./scripts/recall.py --backstory "topic you need"
```

### Monitoring

Check logs occasionally:

```bash
# See what memory rotation did
tail ~/clawd/logs/rotate_memory.log

# See what daily summarization did
tail ~/clawd/logs/summarize_daily.log

# Check FAISS index size
cd ~/clawd/vector-memory
python3 -c "from memory_store import VectorMemory; vm = VectorMemory(); print(vm.stats())"
```

## Expected Impact

### Immediate
- **12,207 tokens saved per message** from backstory + tools condensation
- Context loads faster
- More room for conversation history

### Ongoing
- Memory rotation keeps MEMORY.md lean (weekly)
- Daily summarization compresses old memory files (daily)
- Combined: Additional 10-20% token savings over time

## Safety

- **Nothing is ever deleted** — everything is archived
- Full backstory: `reference/VIKTOR_BACKSTORY_FULL.md`
- Memory archives: `memory/archive/`
- FAISS has full text searchable
- All scripts support `--dry-run`

## Troubleshooting

### "No module named 'faiss'"
```bash
cd ~/clawd/vector-memory
source venv/bin/activate
pip install faiss-cpu sentence-transformers
```

### Scripts Won't Run
```bash
chmod +x ~/clawd/scripts/*.py
```

### Need to Re-index Everything
```bash
cd ~/clawd/vector-memory
rm memory.index memory_meta.json
python3 ingest_memories.py
cd ~/clawd
./scripts/ingest_backstory_to_faiss.py
```

## Documentation

- **CONTEXT_OPTIMIZATION.md** — Complete technical documentation
- **IMPLEMENTATION_SUMMARY.md** — What was done and why
- **This file (QUICKSTART.md)** — Quick reference

---

**Questions?** Check the full documentation in CONTEXT_OPTIMIZATION.md
