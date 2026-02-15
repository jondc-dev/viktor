# Context Recovery System - Deployment Guide

This guide covers deploying the context recovery system to Viktor's Mac Studio.

## Overview

The context recovery system allows Viktor to automatically recover context after OpenClaw compacts his conversation history. It consists of:

1. **Vector Memory Store** - FAISS-based semantic memory
2. **Memory Ingestion** - Periodic reindexing of memories and sessions
3. **Context Injector Daemon** - Generates recovery files every 2 minutes
4. **Compaction Watcher Daemon** - Detects compaction in real-time and triggers immediate recovery
5. **Recovery Hook** - Viktor reads the recovery file on wake

## Prerequisites

- Python 3.8+
- macOS with launchd
- Access to `~/clawd/` workspace
- Access to `~/.openclaw/agents/main/sessions/`

## Step 1: Set Up Vector Memory Environment

```bash
# Create directory structure
mkdir -p ~/clawd/vector-memory
mkdir -p ~/clawd/logs

# Create Python virtualenv
cd ~/clawd/vector-memory
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install faiss-cpu sentence-transformers

# Verify installation
python3 -c "import faiss; import sentence_transformers; print('✅ Dependencies installed')"
```

## Step 2: Deploy Python Scripts

```bash
# Copy files from repo to deployment location
cd /path/to/viktor/repo
cp vector-memory/*.py ~/clawd/vector-memory/
chmod +x ~/clawd/vector-memory/*.py

# Verify files
ls -lh ~/clawd/vector-memory/*.py
```

## Step 3: Run Initial Memory Ingestion

```bash
cd ~/clawd/vector-memory
source venv/bin/activate

# Run ingestion (may take several minutes)
python3 ingest_memories.py

# Expected output:
# - Indexes markdown files from ~/clawd/memory/
# - Indexes sessions from ~/.openclaw/agents/main/sessions/
# - Indexes sessions from ~/.clawdbot/agents/main/sessions/
# - Reports total memories indexed
```

## Step 4: Test Context Injector

```bash
# Test single run
cd ~/clawd/vector-memory
source venv/bin/activate
python3 context_injector.py

# Check output
cat ~/clawd/CONTEXT_RECOVERY.md

# The file should contain:
# - Recent conversation messages
# - Relevant semantic context from vector memory

# Clean up test file
rm ~/clawd/CONTEXT_RECOVERY.md
```

## Step 5: Install Context Injector LaunchAgent

```bash
# Copy plist to LaunchAgents directory
cd /path/to/viktor/repo
cp infrastructure/launchd/ai.openclaw.viktor-context-injector.plist ~/Library/LaunchAgents/

# Load and start the service
launchctl load ~/Library/LaunchAgents/ai.openclaw.viktor-context-injector.plist

# Verify it's running
launchctl list | grep viktor-context-injector
# Should show: PID, exit status, and label

# Check initial logs
tail -f ~/clawd/vector-memory/context_injector.log
```

## Step 6: Install Compaction Watcher LaunchAgent

The compaction watcher detects when OpenClaw compacts your session in real-time and triggers immediate FAISS-based recovery. This provides higher-quality recovery than the periodic context injector.

```bash
# Copy compaction watcher script to deployment location
cd /path/to/viktor/repo
cp scripts/compaction-watcher.py ~/clawd/scripts/
chmod +x ~/clawd/scripts/compaction-watcher.py

# Copy plist to LaunchAgents directory
cp infrastructure/launchd/ai.openclaw.compaction-watcher.plist ~/Library/LaunchAgents/

# Load and start the service
launchctl load ~/Library/LaunchAgents/ai.openclaw.compaction-watcher.plist

# Verify it's running
launchctl list | grep compaction-watcher
# Should show: PID, exit status, and label

# Check initial logs
tail -f ~/clawd/vector-memory/compaction-watcher.log
```

### How It Works

The compaction watcher:
- Polls every 30 seconds
- Tracks session file line counts and sizes
- Detects compaction when:
  - Line count drops >30% (if previous >50 lines)
  - File size drops >50% (if previous >10KB)
- On detection:
  1. Queries FAISS vector memory for relevant semantic context
  2. Reads last 20 messages from the session file
  3. Writes `CONTEXT_RECOVERY.md` with a `COMPACTED` marker
- The `COMPACTED` marker prevents the context injector from overwriting the higher-quality recovery for 5 minutes

### Testing the Compaction Watcher

```bash
# Test manually
cd ~/clawd/scripts
source ~/clawd/vector-memory/venv/bin/activate
python3 compaction-watcher.py

# Check logs for any errors
tail -20 ~/clawd/vector-memory/compaction-watcher.log

# The watcher will run continuously, polling every 30 seconds
# Stop with Ctrl+C
```

## Step 7: Install Cron Job for Reindexing

```bash
# Open crontab
crontab -e

# Add this line (from scripts/crontab.txt):
*/15 * * * * /Users/victor/clawd/vector-memory/venv/bin/python3 /Users/victor/clawd/vector-memory/ingest_memories.py >> /Users/victor/clawd/vector-memory/reindex.log 2>&1

# Save and exit
# Verify cron job
crontab -l | grep ingest_memories
```

## Step 7: Verify End-to-End

```bash
# Wait 2 minutes for context injector to run
sleep 120

# Check if recovery file was created
ls -lh ~/clawd/CONTEXT_RECOVERY.md

# View the file
cat ~/clawd/CONTEXT_RECOVERY.md

# Check logs
tail -20 ~/clawd/vector-memory/context_injector.log
```

## Monitoring

### Log Files

- `~/clawd/vector-memory/context_injector.log` - Context injector log
- `~/clawd/vector-memory/context-injector.stdout.log` - Context injector stdout
- `~/clawd/vector-memory/context-injector.stderr.log` - Context injector stderr
- `~/clawd/vector-memory/compaction-watcher.log` - Compaction watcher log (both stdout and stderr)
- `~/clawd/vector-memory/reindex.log` - Cron reindex log

### Check Service Status

```bash
# Check if both LaunchAgents are running
launchctl list | grep -E "viktor-context-injector|compaction-watcher"

# View recent context injector logs
tail -50 ~/clawd/vector-memory/context_injector.log

# View recent compaction watcher logs
tail -50 ~/clawd/vector-memory/compaction-watcher.log

# Check compaction watcher state
cat ~/clawd/vector-memory/compaction-watcher-state.json

# Check last recovery file
ls -lh ~/clawd/CONTEXT_RECOVERY.md
cat ~/clawd/CONTEXT_RECOVERY.md
```

### Restart Services

```bash
# Context Injector
launchctl unload ~/Library/LaunchAgents/ai.openclaw.viktor-context-injector.plist
launchctl load ~/Library/LaunchAgents/ai.openclaw.viktor-context-injector.plist
launchctl list | grep viktor-context-injector

# Compaction Watcher
launchctl unload ~/Library/LaunchAgents/ai.openclaw.compaction-watcher.plist
launchctl load ~/Library/LaunchAgents/ai.openclaw.compaction-watcher.plist
launchctl list | grep compaction-watcher

# Restart both
launchctl unload ~/Library/LaunchAgents/ai.openclaw.*.plist
launchctl load ~/Library/LaunchAgents/ai.openclaw.viktor-context-injector.plist
launchctl load ~/Library/LaunchAgents/ai.openclaw.compaction-watcher.plist
```

## Troubleshooting

### Issue: Dependencies not found

```bash
# Ensure virtualenv is set up correctly
cd ~/clawd/vector-memory
source venv/bin/activate
pip list | grep -E "faiss|sentence"
```

### Issue: Session files not found

```bash
# Check if sessions directory exists
ls -lh ~/.openclaw/agents/main/sessions/

# Check if files are JSONL
file ~/.openclaw/agents/main/sessions/*.jsonl | head -5
```

### Issue: LaunchAgent not starting

```bash
# Check plist syntax for both services
plutil -lint ~/Library/LaunchAgents/ai.openclaw.viktor-context-injector.plist
plutil -lint ~/Library/LaunchAgents/ai.openclaw.compaction-watcher.plist

# Check LaunchAgent logs
cat ~/clawd/vector-memory/context-injector.stderr.log
cat ~/clawd/vector-memory/compaction-watcher.log

# Try running manually
cd ~/clawd/vector-memory
./venv/bin/python3 context_injector.py --daemon --interval 120

# Try running compaction watcher manually
cd ~/clawd/scripts
source ~/clawd/vector-memory/venv/bin/activate
python3 compaction-watcher.py
```

### Issue: CONTEXT_RECOVERY.md not being created

```bash
# Check if injector is running
ps aux | grep context_injector

# Check logs
tail -50 ~/clawd/vector-memory/context_injector.log

# Test manually with force flag
cd ~/clawd/vector-memory
source venv/bin/activate
python3 context_injector.py --force
```

### Issue: Compaction watcher not detecting compaction

```bash
# Check if compaction watcher is running
ps aux | grep compaction-watcher

# Check watcher logs
tail -50 ~/clawd/vector-memory/compaction-watcher.log

# Check watcher state
cat ~/clawd/vector-memory/compaction-watcher-state.json

# Test manually - watch for output
cd ~/clawd/scripts
source ~/clawd/vector-memory/venv/bin/activate
python3 compaction-watcher.py

# The watcher should show poll activity every 30 seconds
# If compaction is detected, it will log "COMPACTION DETECTED"
```

## Uninstall

```bash
# Stop LaunchAgents
launchctl unload ~/Library/LaunchAgents/ai.openclaw.viktor-context-injector.plist
launchctl unload ~/Library/LaunchAgents/ai.openclaw.compaction-watcher.plist

# Remove plists
rm ~/Library/LaunchAgents/ai.openclaw.viktor-context-injector.plist
rm ~/Library/LaunchAgents/ai.openclaw.compaction-watcher.plist

# Remove cron job
crontab -e
# Delete the ingest_memories line

# Optional: Remove files (be careful!)
# rm -rf ~/clawd/vector-memory/
# rm ~/clawd/scripts/compaction-watcher.py
```

## Success Criteria

After deployment, you should see:

1. ✅ Context injector daemon running (visible in `launchctl list`)
2. ✅ Compaction watcher daemon running (visible in `launchctl list`)
3. ✅ Context injector log updating every 2 minutes
4. ✅ Compaction watcher log showing polls every 30 seconds
5. ✅ `CONTEXT_RECOVERY.md` file being created with recent messages
6. ✅ Vector memory reindexing every 15 minutes (check reindex.log)
7. ✅ When compaction occurs, `CONTEXT_RECOVERY.md` shows "COMPACTED" marker and FAISS-based recovery
8. ✅ Viktor reading and using recovery context on wake (check his behavior)

## Support

For issues or questions, check:
- `vector-memory/README.md` - System documentation
- `infrastructure/launchd/README.md` - LaunchAgent details
- Log files in `~/clawd/vector-memory/`
