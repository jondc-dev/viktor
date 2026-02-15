#!/usr/bin/env python3
"""
Backstory FAISS Ingestion Script
Chunks the full backstory by markdown sections and ingests into Viktor's FAISS vector memory.
Source tag: "backstory:VIKTOR_BACKSTORY"
"""

import sys
from pathlib import Path

# Add vector-memory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "vector-memory"))

from memory_store import VectorMemory


def chunk_by_sections(text: str, max_chars: int = 1500) -> list[str]:
    """
    Chunk markdown text by sections (headers), respecting max_chars limit.
    Splits on ## or ### headers, then further splits if section exceeds max_chars.
    """
    chunks = []
    lines = text.split('\n')
    current_chunk = []
    current_size = 0
    current_header = ""
    
    for line in lines:
        # Check if this is a header line
        if line.startswith('## ') or line.startswith('### '):
            # Save previous chunk if it exists
            if current_chunk:
                chunk_text = '\n'.join(current_chunk).strip()
                if chunk_text:
                    chunks.append(chunk_text)
            
            # Start new chunk with this header
            current_header = line
            current_chunk = [line]
            current_size = len(line)
        else:
            # Add line to current chunk
            current_chunk.append(line)
            current_size += len(line) + 1  # +1 for newline
            
            # If chunk exceeds max_chars, save and start new chunk
            if current_size > max_chars:
                chunk_text = '\n'.join(current_chunk).strip()
                if chunk_text:
                    chunks.append(chunk_text)
                # Start new chunk with header (for context continuity)
                current_chunk = [current_header] if current_header else []
                current_size = len(current_header) if current_header else 0
    
    # Save final chunk
    if current_chunk:
        chunk_text = '\n'.join(current_chunk).strip()
        if chunk_text:
            chunks.append(chunk_text)
    
    return chunks


def main():
    # Path to full backstory
    backstory_path = Path(__file__).parent.parent / "reference" / "VIKTOR_BACKSTORY_FULL.md"
    
    if not backstory_path.exists():
        print(f"Error: Backstory not found at {backstory_path}")
        sys.exit(1)
    
    print(f"Reading backstory from {backstory_path}")
    with open(backstory_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    print(f"Backstory size: {len(text)} chars, {len(text.split())} words")
    
    # Chunk the text
    chunks = chunk_by_sections(text, max_chars=1500)
    print(f"Created {len(chunks)} chunks")
    
    # Initialize vector memory
    print("Loading FAISS vector memory...")
    vm = VectorMemory()
    
    # Ingest chunks
    source = "backstory:VIKTOR_BACKSTORY"
    added_count = 0
    duplicate_count = 0
    
    print(f"Ingesting chunks with source tag: {source}")
    for i, chunk in enumerate(chunks, 1):
        # Show progress
        if i % 10 == 0:
            print(f"  Progress: {i}/{len(chunks)}")
        
        # Add to FAISS
        if vm.add(chunk, source=source):
            added_count += 1
        else:
            duplicate_count += 1
    
    print("\n" + "="*60)
    print("Ingestion Complete")
    print("="*60)
    print(f"Total chunks: {len(chunks)}")
    print(f"Added to FAISS: {added_count}")
    print(f"Duplicates skipped: {duplicate_count}")
    print(f"Source tag: {source}")
    print(f"Vector memory loaded from: {vm.__class__.__module__}")
    print("\nTest recall with:")
    print(f"  python3 ~/clawd/scripts/recall.py --backstory \"María Elena\"")
    print(f"  python3 ~/clawd/scripts/recall.py --backstory \"Father Miguel\"")
    print(f"  python3 ~/clawd/scripts/recall.py --backstory \"football\"")


if __name__ == "__main__":
    main()
