#!/bin/bash
# Vector Memory Re-indexing Script
# Runs periodically to sync all memory files into FAISS index

cd ~/clawd/vector-memory
source venv/bin/activate
python ingest_memories.py >> /tmp/vector-reindex.log 2>&1
echo "[$(date)] Reindex complete" >> /tmp/vector-reindex.log
