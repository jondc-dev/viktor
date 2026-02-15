#!/usr/bin/env python3
"""
Context Injector Daemon for Viktor
Parses recent OpenClaw sessions and writes CONTEXT_RECOVERY.md with:
- Last 15 real messages (filtered for noise)
- Semantic context from FAISS vector memory
"""

import sys
import json
import time
import re
import argparse
from pathlib import Path
from datetime import datetime
import logging

# Import VectorMemory
sys.path.insert(0, str(Path(__file__).parent))
from memory_store import VectorMemory


# Key paths for Viktor's Mac Studio
SESSIONS_DIR = Path.home() / ".openclaw" / "agents" / "main" / "sessions"
WORKSPACE_DIR = Path.home() / "clawd"
OUTPUT_FILE = WORKSPACE_DIR / "CONTEXT_RECOVERY.md"
STATE_FILE = Path.home() / "clawd" / "vector-memory" / "injector_state.json"
LOG_FILE = Path.home() / "clawd" / "vector-memory" / "context_injector.log"

# Noise filters (case-insensitive substrings)
NOISE_FILTERS = [
    "heartbeat_ok",
    "email inbox remains clear",
    "no unread emails",
    "i'll check the email inbox for new messages.",
]


def strip_whisper_timestamps(text):
    """Strip Whisper timestamp prefixes, keeping the transcribed text."""
    if not text:
        return text
    
    lines = text.strip().split('\n')
    cleaned = []
    for line in lines:
        # Match [HH:MM.SSS --> HH:MM.SSS] prefix
        match = re.match(r'\[\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}\.\d{3}\]\s*(.*)', line)
        if match:
            cleaned.append(match.group(1))
        else:
            cleaned.append(line)
    result = ' '.join(cleaned).strip()
    return result if result else text


def setup_logging():
    """Configure logging to file and console"""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


def is_noise_message(text):
    """Check if message matches noise filters"""
    if not text or not text.strip():
        return True
    
    text_lower = text.lower()
    text_stripped = text.strip()
    
    # Check for noise patterns
    for pattern in NOISE_FILTERS:
        if pattern.lower() in text_lower:
            return True
    
    # Check for system messages about email/heartbeat
    if text_lower.startswith("system:") and ("email" in text_lower or "heartbeat" in text_lower):
        return True
    
    # Whisper transcription warnings
    if "fp16 is not supported on cpu" in text_lower:
        return True
    if "whisper/transcribe.py" in text_lower:
        return True
    if "userwarning:" in text_lower:
        return True
    
    # FFmpeg encoder output
    if "encoder         : lavc" in text_lower:
        return True
    if "video:0kib audio:" in text_lower:
        return True
    if "muxing overhead:" in text_lower:
        return True
    if "[out#0/" in text_lower:
        return True
    if "bitrate=" in text_lower and "speed=" in text_lower:
        return True
    
    # Bare media file paths
    if text_stripped.startswith("MEDIA:/"):
        return True
    
    # Bare audio filenames (e.g. "viktor-voice-4.ogg")
    if re.match(r'^[\w\-]+\.(ogg|mp3|wav|m4a)$', text_stripped):
        return True
    
    return False


def parse_session_messages(session_file):
    """Parse JSONL session file and extract messages"""
    messages = []
    
    try:
        with open(session_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    
                    # Check if this is a message entry
                    if entry.get('type') != 'message':
                        continue
                    
                    # Extract message from nested structure (OpenClaw v3 format)
                    msg = entry.get('message', {})
                    role = msg.get('role')
                    content = msg.get('content', [])
                    timestamp = entry.get('timestamp', '')
                    
                    # Skip if no role or content
                    if not role or not content:
                        continue
                    
                    # Extract text from content array
                    text_parts = []
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and item.get('type') == 'text':
                                text_parts.append(item.get('text', ''))
                    
                    text = ' '.join(text_parts).strip()
                    
                    # Strip Whisper timestamps from text
                    text = strip_whisper_timestamps(text)
                    
                    # Skip noise messages
                    if is_noise_message(text):
                        continue
                    
                    # Map roles
                    display_role = "Viktor" if role == "assistant" else "Jon"
                    
                    messages.append({
                        'role': display_role,
                        'text': text,
                        'timestamp': timestamp
                    })
                
                except json.JSONDecodeError:
                    continue
    
    except Exception as e:
        logging.error(f"Error parsing session {session_file}: {e}")
    
    return messages


def get_most_recent_session():
    """Find the most recently modified session file"""
    if not SESSIONS_DIR.exists():
        logging.error(f"Sessions directory not found: {SESSIONS_DIR}")
        return None
    
    session_files = list(SESSIONS_DIR.glob("*.jsonl"))
    if not session_files:
        logging.error("No session files found")
        return None
    
    # Sort by modification time, most recent first
    session_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return session_files[0]


def get_semantic_context(vm, recent_text):
    """Query vector memory for relevant semantic context"""
    queries = [
        "current projects and tasks",
        "recent decisions and commitments",
        "important context and background"
    ]
    
    # Also query with the actual recent conversation context
    if recent_text:
        queries.append(recent_text[:500])  # Use first 500 chars of recent convo
    
    results = []
    seen_texts = set()
    
    for query in queries:
        try:
            matches = vm.search(query, k=3)
            for text, source, score in matches:
                # Deduplicate and filter by relevance
                if text not in seen_texts and score < 1.5:  # Lower score = more similar
                    results.append((text, source, score))
                    seen_texts.add(text)
                    if len(results) >= 8:  # Limit to 8 total results
                        break
        except Exception as e:
            logging.error(f"Error querying vector memory: {e}")
    
    return results[:8]  # Return max 8 results


def check_race_condition(force=False):
    """Check if compaction-watcher is active to avoid race conditions"""
    if force:
        return True
    
    # Check for compaction-watcher state files
    watcher_state = WORKSPACE_DIR / ".compaction_active"
    if watcher_state.exists():
        logging.info("Compaction watcher is active, skipping update")
        return False
    
    return True


def write_context_recovery(messages, semantic_context):
    """Write CONTEXT_RECOVERY.md with messages and semantic context"""
    try:
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        with open(OUTPUT_FILE, 'w') as f:
            f.write("# Context Recovery\n\n")
            f.write(f"*Auto-generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
            f.write("Your context was compacted. Here's what you need to know:\n\n")
            
            # Recent conversation
            f.write("## Recent Conversation\n\n")
            for msg in messages:
                timestamp = msg.get('timestamp', '')
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        time_str = dt.strftime('%H:%M')
                    except:
                        time_str = ''
                else:
                    time_str = ''
                
                role = msg['role']
                text = msg['text']
                
                if time_str:
                    f.write(f"**{role}** *({time_str})*:\n{text}\n\n")
                else:
                    f.write(f"**{role}**:\n{text}\n\n")
            
            # Semantic context
            if semantic_context:
                f.write("## Relevant Context from Memory\n\n")
                for i, (text, source, score) in enumerate(semantic_context, 1):
                    f.write(f"**{i}.** *(from {source}, relevance: {score:.2f})*\n")
                    f.write(f"{text}\n\n")
        
        logging.info(f"Wrote context recovery to {OUTPUT_FILE}")
        return True
    
    except Exception as e:
        logging.error(f"Error writing context recovery: {e}")
        return False


def save_state(session_file, message_count):
    """Save current state to JSON file"""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        state = {
            'last_session': str(session_file),
            'last_update': datetime.now().isoformat(),
            'message_count': message_count
        }
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logging.error(f"Error saving state: {e}")


def run_once(force=False):
    """Run a single context injection cycle"""
    logger = logging.getLogger(__name__)
    
    # Check race condition
    if not check_race_condition(force):
        return False
    
    # Find most recent session
    session_file = get_most_recent_session()
    if not session_file:
        logger.error("No session file found")
        return False
    
    logger.info(f"Processing session: {session_file.name}")
    
    # Parse messages
    messages = parse_session_messages(session_file)
    logger.info(f"Found {len(messages)} valid messages")
    
    # Get last 15 messages
    recent_messages = messages[-15:] if len(messages) > 15 else messages
    
    if not recent_messages:
        logger.warning("No recent messages to process")
        return False
    
    # Get semantic context from vector memory
    try:
        vm = VectorMemory()
        logger.info(f"Vector memory loaded with {len(vm)} entries")
        
        # Use last few messages as query context
        recent_text = ' '.join([m['text'][:200] for m in recent_messages[-3:]])
        semantic_context = get_semantic_context(vm, recent_text)
        logger.info(f"Found {len(semantic_context)} relevant memory entries")
    except Exception as e:
        logger.error(f"Error loading vector memory: {e}")
        semantic_context = []
    
    # Write context recovery file
    if write_context_recovery(recent_messages, semantic_context):
        save_state(session_file, len(recent_messages))
        logger.info("Context recovery update complete")
        return True
    
    return False


def run_daemon(interval=60):
    """Run as a daemon, updating every `interval` seconds"""
    logger = logging.getLogger(__name__)
    logger.info(f"Starting context injector daemon (interval: {interval}s)")
    
    while True:
        try:
            run_once()
        except Exception as e:
            logger.error(f"Error in daemon loop: {e}")
        
        time.sleep(interval)


def main():
    """Main entry point with CLI interface"""
    parser = argparse.ArgumentParser(description="Viktor Context Injector Daemon")
    parser.add_argument('--daemon', action='store_true', help='Run as daemon')
    parser.add_argument('--interval', type=int, default=120, help='Daemon interval in seconds (default: 120)')
    parser.add_argument('--force', action='store_true', help='Ignore race condition check')
    
    args = parser.parse_args()
    
    logger = setup_logging()
    
    if args.daemon:
        logger.info("Starting in daemon mode")
        run_daemon(args.interval)
    else:
        logger.info("Running single update")
        success = run_once(args.force)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
