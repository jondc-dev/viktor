#!/usr/bin/env python3
"""
Compaction Watcher for Viktor
Detects when OpenClaw compacts session files and triggers immediate FAISS-based recovery.

Polls every 30 seconds and detects compaction by watching for:
- Line count drops >30% (if previous >50 lines)
- File size drops >50% (if previous >10KB)

When compaction is detected, generates CONTEXT_RECOVERY.md with:
- FAISS semantic context from VectorMemory
- Last 20 messages from session file (fallback)
- COMPACTED marker to prevent context_injector from overwriting
"""

import sys
import json
import time
import os
from pathlib import Path
from datetime import datetime
import logging

# Import VectorMemory
sys.path.insert(0, str(Path.home() / "clawd" / "vector-memory"))
from memory_store import VectorMemory

# Key paths for Viktor's Mac Studio
SESSIONS_DIR = Path.home() / ".openclaw" / "agents" / "main" / "sessions"
WORKSPACE_DIR = Path.home() / "clawd"
OUTPUT_FILE = WORKSPACE_DIR / "CONTEXT_RECOVERY.md"
STATE_FILE = WORKSPACE_DIR / "vector-memory" / "compaction-watcher-state.json"
LOG_FILE = WORKSPACE_DIR / "vector-memory" / "compaction-watcher.log"

# Compaction detection thresholds
MIN_LINES_FOR_LINE_CHECK = 50
LINE_DROP_THRESHOLD = 0.30  # 30% drop
MIN_SIZE_FOR_SIZE_CHECK = 10 * 1024  # 10KB
SIZE_DROP_THRESHOLD = 0.50  # 50% drop

# Polling interval
POLL_INTERVAL = 30  # seconds

# Noise filters (same as context_injector.py)
NOISE_FILTERS = [
    "heartbeat_ok",
    "email inbox remains clear",
    "no unread emails",
    "i'll check the email inbox for new messages.",
    "openclaw 2026",
    "openclaw 2025",
    "\xf0\x9f\xa6\x9e openclaw",
    "tokens:",
    "context:",
    "compactions:",
    "queue: collect",
    "(no output yet)",
    "(no new output)",
    "process still running",
    "process exited with code",
    "no_reply",
    "sent! 📸",
    "sent! 🎙",
    "sent! 📤",
    "command still running",
    "killed session",
    "(no output)",
    "use process (list/poll/log/write/kill/clear/remove)",
    "viktor generation master",
    "mandatory read before any image generation",
    "enforcement rules",
    "seedream",
    "negative prompt",
    "fal.run/fal-ai",
    "fal.media/files",
]


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


def load_state():
    """Load previous state from disk"""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading state: {e}")
    return {}


def save_state(state):
    """Save state to disk"""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logging.error(f"Error saving state: {e}")


def get_session_stats(session_file):
    """Get line count and file size for a session file"""
    try:
        if not session_file.exists():
            return None, None
        
        line_count = 0
        with open(session_file, 'r') as f:
            for _ in f:
                line_count += 1
        
        file_size = session_file.stat().st_size
        return line_count, file_size
    except Exception as e:
        logging.error(f"Error reading session stats: {e}")
        return None, None


def detect_compaction(session_file, prev_lines, prev_size):
    """
    Detect if compaction occurred based on line count and file size drops.
    Returns True if compaction detected.
    """
    current_lines, current_size = get_session_stats(session_file)
    
    if current_lines is None or current_size is None:
        return False
    
    # Check line count drop (if previous had >50 lines)
    if prev_lines and prev_lines > MIN_LINES_FOR_LINE_CHECK:
        line_drop_ratio = (prev_lines - current_lines) / prev_lines
        if line_drop_ratio > LINE_DROP_THRESHOLD:
            logging.info(f"Compaction detected: line drop {line_drop_ratio:.1%} ({prev_lines} → {current_lines})")
            return True
    
    # Check file size drop (if previous was >10KB)
    if prev_size and prev_size > MIN_SIZE_FOR_SIZE_CHECK:
        size_drop_ratio = (prev_size - current_size) / prev_size
        if size_drop_ratio > SIZE_DROP_THRESHOLD:
            logging.info(f"Compaction detected: size drop {size_drop_ratio:.1%} ({prev_size} → {current_size} bytes)")
            return True
    
    return False


def strip_whisper_timestamps(text):
    """Strip Whisper timestamp prefixes, keeping the transcribed text."""
    import re
    lines = text.strip().split('\n')
    cleaned = []
    has_timestamps = False
    for line in lines:
        match = re.match(r'\[\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}\.\d{3}\]\s*(.*)', line)
        if match:
            has_timestamps = True
            cleaned.append(match.group(1))
        else:
            cleaned.append(line)
    if has_timestamps:
        return ' '.join(c for c in cleaned if c.strip()).strip()
    return text


def is_noise_message(text):
    """Check if message matches noise filters"""
    if not text or not text.strip():
        return True
    
    text_lower = text.lower()
    
    # Check for noise patterns
    for pattern in NOISE_FILTERS:
        if pattern.lower() in text_lower:
            return True
    
    # Check for system messages about email/heartbeat
    if text_lower.startswith("system:") and ("email" in text_lower or "heartbeat" in text_lower):
        return True
    
    # Filter JSON system messages
    stripped = text.strip()
    if stripped.startswith('{"images":[') or stripped.startswith('[{"url":'):
        return True
    if stripped.startswith("-rw-") or stripped.startswith("drwx"):
        return True
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            obj = json.loads(stripped)
            if any(k in obj for k in ("status", "channel", "result", "tool", "mediaUrl", "toJid", "runId",
                                       "results", "provider", "sessions", "count", "sessionId", "model")):
                return True
            if len(stripped) > 200:
                return True
        except (json.JSONDecodeError, ValueError):
            if len(stripped) > 200:
                return True
    
    import re
    if re.match(r'^[\w\-\.]+\.(png|jpg|jpeg|gif|webp|pdf|csv|html)$', stripped):
        return True
    
    if "[media attached:" in text_lower:
        return True
    if "to send an image back" in text_lower:
        return True
    if "fp16 is not supported on cpu" in text_lower:
        return True
    if "whisper/transcribe.py" in text_lower:
        return True
    if "encoder         : lavc" in text_lower:
        return True
    if "video:0kib audio:" in text_lower:
        return True
    if "muxing overhead:" in text_lower:
        return True
    if "[out#0/" in text_lower:
        return True
    if "bitrate=" in text_lower and "speed=" in text_lower and "elapsed=" in text_lower:
        return True
    if text.strip().startswith("MEDIA:/"):
        return True
    if re.match(r'^[\w\-]+\.(ogg|mp3|wav|m4a)$', text.strip()):
        return True
    
    return False


def parse_session_messages(session_file, max_messages=20):
    """Parse JSONL session file and extract last N messages"""
    messages = []
    
    try:
        with open(session_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    
                    if entry.get('type') != 'message':
                        continue
                    
                    msg = entry.get('message', {})
                    role = msg.get('role')
                    content = msg.get('content', [])
                    timestamp = entry.get('timestamp', '')
                    
                    if not role or not content:
                        continue
                    
                    # Extract text from content array
                    text_parts = []
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and item.get('type') == 'text':
                                text_parts.append(item.get('text', ''))
                    
                    text = ' '.join(text_parts).strip()
                    text = strip_whisper_timestamps(text)
                    
                    if is_noise_message(text):
                        continue
                    
                    # Map roles - Viktor-specific labels
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
    
    # Return last N messages
    return messages[-max_messages:] if len(messages) > max_messages else messages


def get_semantic_context_for_compaction(vm, recent_messages):
    """
    Query vector memory for relevant context after compaction.
    More aggressive than normal context injection.
    """
    queries = [
        "current projects and tasks in progress",
        "recent decisions and commitments made",
        "important ongoing work and context",
        "pending items and action items",
        "key decisions and discussions from today"
    ]
    
    # Also query with recent conversation context
    if recent_messages:
        recent_text = ' '.join([m['text'][:300] for m in recent_messages[-5:]])
        queries.append(recent_text[:600])
    
    results = []
    seen_texts = set()
    
    for query in queries:
        try:
            matches = vm.search(query, k=4)
            for match in matches:
                text = match["text"] if isinstance(match, dict) else match[0]
                source = match.get("source", "unknown") if isinstance(match, dict) else match[1]
                score = match.get("score", match.get("timestamp", 0)) if isinstance(match, dict) else match[2]
                
                # More lenient threshold for compaction recovery
                if text not in seen_texts and score < 2.0:
                    results.append((text, source, score))
                    seen_texts.add(text)
                    if len(results) >= 12:  # Get more results for compaction
                        break
        except Exception as e:
            logging.error(f"Error querying vector memory: {e}")
    
    return results[:12]


def write_compaction_recovery(messages, semantic_context):
    """
    Write CONTEXT_RECOVERY.md with COMPACTED marker.
    This marker prevents context_injector from overwriting it.
    """
    try:
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        with open(OUTPUT_FILE, 'w') as f:
            f.write("# Context Recovery (COMPACTED)\n\n")
            f.write(f"*Auto-generated by compaction watcher at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
            f.write("⚠️ **COMPACTION DETECTED** — Your context was just compacted. Here's what you need to know:\n\n")
            
            # Recent conversation
            f.write("## Recent Conversation (Last 20 Messages)\n\n")
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
            
            # Semantic context from FAISS
            if semantic_context:
                f.write("## Relevant Context from Memory (FAISS Recovery)\n\n")
                f.write("*High-relevance memories recovered from your vector memory store:*\n\n")
                for i, (text, source, score) in enumerate(semantic_context, 1):
                    f.write(f"**{i}.** *(from {source}, score: {score:.3f})*\n")
                    f.write(f"{text}\n\n")
            
            f.write("---\n\n")
            f.write("*This recovery file was generated at the moment of compaction. ")
            f.write("It contains targeted semantic context and the last 20 messages.*\n")
        
        logging.info(f"Wrote compaction recovery to {OUTPUT_FILE}")
        return True
    
    except Exception as e:
        logging.error(f"Error writing compaction recovery: {e}")
        return False


def handle_compaction(session_file):
    """
    Handle detected compaction:
    1. Try FAISS recovery via VectorMemory
    2. Fallback to reading last 20 messages
    3. Write CONTEXT_RECOVERY.md with COMPACTED marker
    """
    logging.info(f"Handling compaction for {session_file.name}")
    
    # Parse last 20 messages from session file
    messages = parse_session_messages(session_file, max_messages=20)
    logging.info(f"Retrieved {len(messages)} messages from session file")
    
    # Try FAISS recovery
    semantic_context = []
    try:
        vm = VectorMemory()
        logging.info(f"Vector memory loaded with {len(vm)} entries")
        semantic_context = get_semantic_context_for_compaction(vm, messages)
        logging.info(f"Retrieved {len(semantic_context)} semantic memories")
    except Exception as e:
        logging.error(f"Error loading vector memory for recovery: {e}")
    
    # Write recovery file with COMPACTED marker
    if write_compaction_recovery(messages, semantic_context):
        logging.info("Compaction recovery complete")
        return True
    
    return False


def get_most_recent_session():
    """Find the most recently modified session file"""
    if not SESSIONS_DIR.exists():
        logging.error(f"Sessions directory not found: {SESSIONS_DIR}")
        return None
    
    session_files = list(SESSIONS_DIR.glob("*.jsonl"))
    if not session_files:
        logging.error("No session files found")
        return None
    
    session_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return session_files[0]


def watch_loop():
    """Main watch loop - polls every 30 seconds"""
    logger = logging.getLogger(__name__)
    logger.info(f"Starting compaction watcher (polling every {POLL_INTERVAL}s)")
    
    state = load_state()
    
    while True:
        try:
            # Get most recent session
            session_file = get_most_recent_session()
            if not session_file:
                time.sleep(POLL_INTERVAL)
                continue
            
            session_name = str(session_file)
            
            # Get current stats
            current_lines, current_size = get_session_stats(session_file)
            
            if current_lines is None or current_size is None:
                time.sleep(POLL_INTERVAL)
                continue
            
            # Check if we have previous stats for this session
            if session_name in state:
                prev_stats = state[session_name]
                prev_lines = prev_stats.get('lines')
                prev_size = prev_stats.get('size')
                
                # Detect compaction
                if detect_compaction(session_file, prev_lines, prev_size):
                    logger.info("🔄 COMPACTION DETECTED - Triggering recovery")
                    handle_compaction(session_file)
            
            # Update state
            state[session_name] = {
                'lines': current_lines,
                'size': current_size,
                'last_check': datetime.now().isoformat()
            }
            save_state(state)
            
            # Clean up old sessions from state (keep last 5)
            if len(state) > 5:
                # Sort by last_check timestamp
                sorted_sessions = sorted(
                    state.items(),
                    key=lambda x: x[1].get('last_check', ''),
                    reverse=True
                )
                state = dict(sorted_sessions[:5])
                save_state(state)
        
        except Exception as e:
            logger.error(f"Error in watch loop: {e}")
        
        time.sleep(POLL_INTERVAL)


def main():
    """Main entry point"""
    logger = setup_logging()
    logger.info("Viktor Compaction Watcher starting...")
    
    # Check dependencies
    try:
        from memory_store import VectorMemory
        logger.info("✓ VectorMemory module loaded")
    except ImportError as e:
        logger.error(f"Failed to import VectorMemory: {e}")
        logger.error("Make sure vector-memory dependencies are installed")
        sys.exit(1)
    
    # Start watch loop
    try:
        watch_loop()
    except KeyboardInterrupt:
        logger.info("Compaction watcher stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
