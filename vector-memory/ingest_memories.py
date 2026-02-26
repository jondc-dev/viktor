#!/usr/bin/env python3
"""
Memory ingestion script for Viktor's vector memory system.
Indexes markdown memory files and JSONL chat sessions from both
.openclaw and .clawdbot directories.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Import VectorMemory
sys.path.insert(0, str(Path(__file__).parent))
from memory_store import VectorMemory


# Paths to memory sources
MEMORY_DIR = Path.home() / "clawd" / "memory"
SESSIONS_DIR_OPENCLAW = Path.home() / ".openclaw" / "agents" / "main" / "sessions"
SESSIONS_DIR_CLAWDBOT = Path.home() / ".clawdbot" / "agents" / "main" / "sessions"


def ingest_markdown_memories(memory_dir, vm):
    """Index all markdown files in memory directory"""
    if not memory_dir.exists():
        print(f"Memory directory not found: {memory_dir}")
        return 0
    
    count = 0
    for md_file in memory_dir.rglob("*.md"):
        try:
            content = md_file.read_text()
            source = f"memory:{md_file.name}"
            
            # Split into paragraphs for better granularity
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            
            for para in paragraphs:
                if len(para) > 20:  # Skip very short paragraphs
                    if vm.add(para, source):
                        count += 1
        except Exception as e:
            print(f"Error indexing {md_file}: {e}")
    
    return count


def chunk_text(text, max_chars=1500, overlap=300):
    """Chunk long text with overlap for better embedding quality."""
    if overlap >= max_chars:
        overlap = 0
    if len(text) <= max_chars:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start += max_chars - overlap
    return chunks


def ingest_session_messages(sessions_dir, vm):
    """Index messages from JSONL session files"""
    if not sessions_dir.exists():
        print(f"Sessions directory not found: {sessions_dir}")
        return 0
    
    count = 0
    for session_file in sessions_dir.glob("*.jsonl"):
        try:
            with open(session_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        
                        # Check if this is a message entry
                        if entry.get('type') != 'message':
                            continue
                        
                        # Extract message from nested structure
                        msg = entry.get('message', {})
                        role = msg.get('role')
                        content = msg.get('content', [])
                        
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
                        
                        if text and len(text) > 20:
                            source = f"session:{session_file.stem}"
                            for chunk in chunk_text(text):
                                if vm.add(chunk, source):
                                    count += 1
                    
                    except json.JSONDecodeError:
                        continue
        
        except Exception as e:
            print(f"Error indexing {session_file}: {e}")
    
    return count


def main():
    """Main ingestion routine"""
    print("Starting memory ingestion...")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    vm = VectorMemory()
    initial_count = len(vm)
    print(f"Initial index size: {initial_count} memories")
    
    # Ingest markdown memories
    print(f"\nIndexing markdown memories from {MEMORY_DIR}...")
    md_count = ingest_markdown_memories(MEMORY_DIR, vm)
    print(f"Added {md_count} new memories from markdown files")
    
    # Ingest sessions from OpenClaw
    print(f"\nIndexing sessions from {SESSIONS_DIR_OPENCLAW}...")
    oc_count = ingest_session_messages(SESSIONS_DIR_OPENCLAW, vm)
    print(f"Added {oc_count} new memories from OpenClaw sessions")
    
    # Ingest sessions from Clawdbot
    print(f"\nIndexing sessions from {SESSIONS_DIR_CLAWDBOT}...")
    cb_count = ingest_session_messages(SESSIONS_DIR_CLAWDBOT, vm)
    print(f"Added {cb_count} new memories from Clawdbot sessions")
    
    # Final stats
    final_count = len(vm)
    total_added = md_count + oc_count + cb_count
    print(f"\nFinal index size: {final_count} memories")
    print(f"Total new memories added: {total_added}")
    print("Ingestion complete!")


if __name__ == "__main__":
    main()
