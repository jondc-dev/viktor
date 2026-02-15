# LaunchAgent Configuration

This directory contains macOS LaunchAgent plists for Viktor's background services.

## Context Injector Daemon

The context injector daemon automatically recovers context when Viktor's conversation is compacted by OpenClaw.

### Installation

```bash
# Copy the plist to LaunchAgents directory
cp infrastructure/launchd/ai.openclaw.viktor-context-injector.plist ~/Library/LaunchAgents/

# Load and start the service
launchctl load ~/Library/LaunchAgents/ai.openclaw.viktor-context-injector.plist

# Verify it's running
launchctl list | grep viktor-context-injector
```

### Management

```bash
# Stop the service
launchctl unload ~/Library/LaunchAgents/ai.openclaw.viktor-context-injector.plist

# Restart the service
launchctl unload ~/Library/LaunchAgents/ai.openclaw.viktor-context-injector.plist
launchctl load ~/Library/LaunchAgents/ai.openclaw.viktor-context-injector.plist

# Check status
launchctl list | grep viktor-context-injector

# View logs
tail -f ~/clawd/vector-memory/context_injector.log
tail -f ~/clawd/vector-memory/context-injector.stdout.log
tail -f ~/clawd/vector-memory/context-injector.stderr.log
```

### How It Works

1. Runs every 2 minutes (120 second interval)
2. Parses the most recent OpenClaw session JSONL file
3. Extracts the last 15 real messages (filtering heartbeats, email noise)
4. Queries the FAISS vector memory for semantic context
5. Writes `~/clawd/CONTEXT_RECOVERY.md` with:
   - Recent conversation messages
   - Relevant memories from the vector store
6. Viktor reads and deletes this file on wake (see AGENTS.md)

### Race Condition Protection

The injector checks for `.compaction_active` state file to avoid conflicts with other watchers.

### Manual Testing

```bash
# Test single run (won't start daemon)
cd ~/clawd/vector-memory
source venv/bin/activate
python3 context_injector.py

# Test with force flag (ignores race condition check)
python3 context_injector.py --force

# Test daemon mode locally (60 second interval)
python3 context_injector.py --daemon --interval 60
```
