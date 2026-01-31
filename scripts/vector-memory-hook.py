#!/usr/bin/env python3
"""
Hook script to index individual conversation turns or memories.
Usage: vector-memory-hook.py "text to remember" [source]
"""

import sys
import os

# Add vector-memory to path
sys.path.insert(0, os.path.expanduser("~/clawd/vector-memory"))

from memory_store import VectorMemory

def main():
    if len(sys.argv) < 2:
        print("Usage: vector-memory-hook.py <text> [source]")
        sys.exit(1)
    
    text = sys.argv[1]
    source = sys.argv[2] if len(sys.argv) > 2 else "conversation"
    
    mem = VectorMemory()
    
    if mem.add(text, source):
        print(f"✓ Indexed: {text[:50]}...")
    else:
        print("↩ Duplicate, skipped")

if __name__ == "__main__":
    main()
