# Context Recovery System - Deployment Guide

This guide covers deploying the context recovery system to Viktor's Mac Studio.

## Overview

The context recovery system allows Viktor to automatically recover context after OpenClaw compacts his conversation history. It consists of:

1. **Vector Memory Store** - FAISS-based semantic memory
2. **Memory Ingestion** - Periodic reindexing of memories and sessions
3. **Context Injector Daemon** - Generates recovery files every 2 minutes
4. **Recovery Hook** - Viktor reads the recovery file on wake

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

## Step 5: Install LaunchAgent

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

## Step 6: Install Cron Job for Reindexing

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

- `~/clawd/vector-memory/context_injector.log` - Main injector log
- `~/clawd/vector-memory/context-injector.stdout.log` - LaunchAgent stdout
- `~/clawd/vector-memory/context-injector.stderr.log` - LaunchAgent stderr
- `~/clawd/vector-memory/reindex.log` - Cron reindex log

### Check Service Status

```bash
# Check if LaunchAgent is running
launchctl list | grep viktor-context-injector

# View recent logs
tail -50 ~/clawd/vector-memory/context_injector.log

# Check last recovery file
ls -lh ~/clawd/CONTEXT_RECOVERY.md
cat ~/clawd/CONTEXT_RECOVERY.md
```

### Restart Service

```bash
# Unload
launchctl unload ~/Library/LaunchAgents/ai.openclaw.viktor-context-injector.plist

# Reload
launchctl load ~/Library/LaunchAgents/ai.openclaw.viktor-context-injector.plist

# Verify
launchctl list | grep viktor-context-injector
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
# Check plist syntax
plutil -lint ~/Library/LaunchAgents/ai.openclaw.viktor-context-injector.plist

# Check LaunchAgent logs
cat ~/clawd/vector-memory/context-injector.stderr.log

# Try running manually
cd ~/clawd/vector-memory
./venv/bin/python3 context_injector.py --daemon --interval 120
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

## Uninstall

```bash
# Stop LaunchAgent
launchctl unload ~/Library/LaunchAgents/ai.openclaw.viktor-context-injector.plist

# Remove plist
rm ~/Library/LaunchAgents/ai.openclaw.viktor-context-injector.plist

# Remove cron job
crontab -e
# Delete the ingest_memories line

# Optional: Remove files (be careful!)
# rm -rf ~/clawd/vector-memory/
```

## Success Criteria

After deployment, you should see:

1. ✅ Context injector daemon running (visible in `launchctl list`)
2. ✅ Log file updating every 2 minutes
3. ✅ `CONTEXT_RECOVERY.md` file being created with recent messages
4. ✅ Vector memory reindexing every 15 minutes (check reindex.log)
5. ✅ Viktor reading and using recovery context on wake (check his behavior)

## Support

For issues or questions, check:
- `vector-memory/README.md` - System documentation
- `infrastructure/launchd/README.md` - LaunchAgent details
- Log files in `~/clawd/vector-memory/`
