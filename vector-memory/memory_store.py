#!/usr/bin/env python3
"""
VectorMemory - FAISS-based semantic memory system
Uses sentence-transformers (all-MiniLM-L6-v2) for embeddings
"""

import faiss
import pickle
import hashlib
from pathlib import Path
from sentence_transformers import SentenceTransformer


class VectorMemory:
    """FAISS-backed vector memory store with semantic search"""
    
    def __init__(self, store_path=None):
        if store_path is None:
            store_path = Path.home() / "clawd" / "vector-memory"
        
        self.store_path = Path(store_path)
        self.index_file = self.store_path / "memory.index"
        self.metadata_file = self.store_path / "memory_metadata.pkl"
        
        # Load or create model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Load or create index
        if self.index_file.exists() and self.metadata_file.exists():
            self.index = faiss.read_index(str(self.index_file))
            with open(self.metadata_file, 'rb') as f:
                self.metadata = pickle.load(f)
        else:
            # Create new index (384 dimensions for all-MiniLM-L6-v2)
            self.index = faiss.IndexFlatL2(384)
            self.metadata = []
    
    def add(self, text, source="unknown"):
        """Add text to memory store. Returns True if added, False if duplicate."""
        # Check for duplicates using text hash
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        
        for entry in self.metadata:
            if entry.get('hash') == text_hash:
                return False  # Duplicate
        
        # Generate embedding and add to index
        embedding = self.model.encode([text])[0].astype('float32')
        self.index.add(embedding.reshape(1, -1))
        
        # Add metadata
        self.metadata.append({
            'text': text,
            'source': source,
            'hash': text_hash
        })
        
        # Save
        self.save()
        return True
    
    def search(self, query, k=5):
        """Search for similar memories. Returns list of (text, source, score) tuples."""
        if self.index.ntotal == 0:
            return []
        
        query_embedding = self.model.encode([query])[0].astype('float32')
        distances, indices = self.index.search(query_embedding.reshape(1, -1), min(k, self.index.ntotal))
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.metadata):
                entry = self.metadata[idx]
                results.append((entry['text'], entry['source'], float(dist)))
        
        return results
    
    def save(self):
        """Save index and metadata to disk"""
        self.store_path.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.index_file))
        with open(self.metadata_file, 'wb') as f:
            pickle.dump(self.metadata, f)
    
    def __len__(self):
        return self.index.ntotal
