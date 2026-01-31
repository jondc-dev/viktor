#!/usr/bin/env python3
"""
Ingest existing Clawdbot memory files into vector store.
Runs on startup or periodically to sync new memories.
"""

import re
from pathlib import Path
from datetime import datetime
from memory_store import VectorMemory

CLAWD_DIR = Path.home() / "clawd"
MEMORY_FILE = CLAWD_DIR / "MEMORY.md"
MEMORY_DIR = CLAWD_DIR / "memory"


def chunk_markdown(content: str, source: str) -> list[dict]:
    """
    Smart chunking for markdown files.
    Splits by headers and meaningful paragraphs.
    """
    chunks = []
    
    # Split by headers (## or ###)
    sections = re.split(r'\n(?=##+ )', content)
    
    for section in sections:
        section = section.strip()
        if not section or len(section) < 50:
            continue
            
        # If section is too long, split by double newlines
        if len(section) > 1000:
            paragraphs = section.split('\n\n')
            for para in paragraphs:
                para = para.strip()
                if para and len(para) > 50:
                    chunks.append({
                        "text": para[:2000],  # Cap at 2000 chars
                        "source": source
                    })
        else:
            chunks.append({
                "text": section,
                "source": source
            })
    
    return chunks


def ingest_memory_file(mem: VectorMemory, filepath: Path) -> int:
    """Ingest a single memory file."""
    if not filepath.exists():
        return 0
        
    content = filepath.read_text()
    source = str(filepath.relative_to(CLAWD_DIR))
    
    # Extract date from filename if daily memory
    timestamp = None
    if filepath.parent.name == "memory":
        # Try to parse date from filename (YYYY-MM-DD.md)
        match = re.match(r'(\d{4}-\d{2}-\d{2})', filepath.stem)
        if match:
            timestamp = f"{match.group(1)}T00:00:00"
    
    chunks = chunk_markdown(content, source)
    if timestamp:
        for chunk in chunks:
            chunk["timestamp"] = timestamp
    
    return mem.add_batch(chunks)


def main():
    print("Initializing vector memory...")
    mem = VectorMemory()
    
    total_added = 0
    
    # Ingest MEMORY.md
    if MEMORY_FILE.exists():
        added = ingest_memory_file(mem, MEMORY_FILE)
        print(f"MEMORY.md: +{added} chunks")
        total_added += added
    
    # Ingest daily memory files
    if MEMORY_DIR.exists():
        for md_file in sorted(MEMORY_DIR.glob("*.md")):
            added = ingest_memory_file(mem, md_file)
            if added > 0:
                print(f"{md_file.name}: +{added} chunks")
            total_added += added
    
    print(f"\nTotal: {total_added} new memories indexed")
    print(f"Index now has {mem.stats()['total_memories']} memories")


if __name__ == "__main__":
    main()
