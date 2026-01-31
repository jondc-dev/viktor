#!/usr/bin/env python3
"""
Vector Memory System for Clawdbot
Persistent semantic memory that survives context truncation.
"""

import json
import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# Config
MEMORY_DIR = Path(__file__).parent
INDEX_PATH = MEMORY_DIR / "memory.index"
METADATA_PATH = MEMORY_DIR / "memory_meta.json"
MODEL_NAME = "all-MiniLM-L6-v2"  # Fast, good quality, 384 dims
EMBEDDING_DIM = 384


class VectorMemory:
    def __init__(self):
        self.model = SentenceTransformer(MODEL_NAME)
        self.index: Optional[faiss.IndexFlatIP] = None  # Inner product (cosine with normalized vecs)
        self.metadata: list[dict] = []  # Parallel array: [{id, text, source, timestamp, hash}, ...]
        self._load()

    def _load(self):
        """Load existing index and metadata from disk."""
        if INDEX_PATH.exists() and METADATA_PATH.exists():
            self.index = faiss.read_index(str(INDEX_PATH))
            with open(METADATA_PATH, "r") as f:
                self.metadata = json.load(f)
            print(f"Loaded {len(self.metadata)} memories from disk")
        else:
            self.index = faiss.IndexFlatIP(EMBEDDING_DIM)
            self.metadata = []
            print("Created new memory index")

    def _save(self):
        """Persist index and metadata to disk."""
        faiss.write_index(self.index, str(INDEX_PATH))
        with open(METADATA_PATH, "w") as f:
            json.dump(self.metadata, f, indent=2)

    def _hash(self, text: str) -> str:
        """Generate content hash for deduplication."""
        return hashlib.md5(text.encode()).hexdigest()[:12]

    def _embed(self, texts: list[str]) -> np.ndarray:
        """Embed texts and normalize for cosine similarity."""
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        # Normalize for cosine similarity via inner product
        faiss.normalize_L2(embeddings)
        return embeddings

    def add(self, text: str, source: str = "manual", timestamp: Optional[str] = None) -> bool:
        """
        Add a memory to the index.
        Returns False if duplicate (already exists).
        """
        content_hash = self._hash(text)
        
        # Check for duplicates
        if any(m["hash"] == content_hash for m in self.metadata):
            return False

        embedding = self._embed([text])
        self.index.add(embedding)
        
        self.metadata.append({
            "id": len(self.metadata),
            "text": text,
            "source": source,
            "timestamp": timestamp or datetime.now().isoformat(),
            "hash": content_hash
        })
        
        self._save()
        return True

    def add_batch(self, items: list[dict]) -> int:
        """
        Add multiple memories at once.
        Each item: {text, source?, timestamp?}
        Returns count of new memories added.
        """
        new_items = []
        for item in items:
            text = item["text"]
            content_hash = self._hash(text)
            if not any(m["hash"] == content_hash for m in self.metadata):
                new_items.append({
                    "text": text,
                    "source": item.get("source", "batch"),
                    "timestamp": item.get("timestamp", datetime.now().isoformat()),
                    "hash": content_hash
                })

        if not new_items:
            return 0

        texts = [item["text"] for item in new_items]
        embeddings = self._embed(texts)
        self.index.add(embeddings)

        for item in new_items:
            item["id"] = len(self.metadata)
            self.metadata.append(item)

        self._save()
        return len(new_items)

    def search(self, query: str, k: int = 5, min_score: float = 0.3) -> list[dict]:
        """
        Search for similar memories.
        Returns list of {text, source, timestamp, score}
        """
        if self.index.ntotal == 0:
            return []

        query_vec = self._embed([query])
        scores, indices = self.index.search(query_vec, min(k, self.index.ntotal))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or score < min_score:
                continue
            meta = self.metadata[idx]
            results.append({
                "text": meta["text"],
                "source": meta["source"],
                "timestamp": meta["timestamp"],
                "score": float(score)
            })

        return results

    def stats(self) -> dict:
        """Return index statistics."""
        return {
            "total_memories": len(self.metadata),
            "index_size": self.index.ntotal if self.index else 0,
            "sources": list(set(m["source"] for m in self.metadata))
        }


# CLI interface
if __name__ == "__main__":
    import sys
    
    mem = VectorMemory()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  memory_store.py add <text> [source]")
        print("  memory_store.py search <query> [k]")
        print("  memory_store.py stats")
        print("  memory_store.py ingest <file>")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "add":
        text = sys.argv[2]
        source = sys.argv[3] if len(sys.argv) > 3 else "cli"
        if mem.add(text, source):
            print(f"Added memory (source: {source})")
        else:
            print("Duplicate - not added")

    elif cmd == "search":
        query = sys.argv[2]
        k = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        results = mem.search(query, k)
        if results:
            for r in results:
                print(f"\n[{r['score']:.3f}] ({r['source']}, {r['timestamp'][:10]})")
                print(f"  {r['text'][:200]}...")
        else:
            print("No matching memories found")

    elif cmd == "stats":
        stats = mem.stats()
        print(json.dumps(stats, indent=2))

    elif cmd == "ingest":
        filepath = sys.argv[2]
        with open(filepath) as f:
            content = f.read()
        # Simple chunking: split by double newlines
        chunks = [c.strip() for c in content.split("\n\n") if c.strip() and len(c.strip()) > 50]
        added = mem.add_batch([{"text": c, "source": filepath} for c in chunks])
        print(f"Ingested {added} new chunks from {filepath}")

    else:
        print(f"Unknown command: {cmd}")
