#!/usr/bin/env python3
"""
Pre-response memory recall for Viktor.
Searches VectorMemory (FAISS) for relevant context before each response.
"""

import re
import sys
from pathlib import Path

# Ensure memory_store.py (in the same directory) is importable
sys.path.insert(0, str(Path(__file__).parent))

WORKSPACE_ROOT = Path("~/clawd").expanduser()
MIN_MESSAGE_LENGTH = 15
MAX_CHUNK_CHARS = 500
RECALL_K = 5
MIN_SCORE = 0.3

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "its", "this", "that", "be",
    "are", "was", "were", "has", "have", "had", "do", "does", "did", "not",
    "no", "so", "if", "as", "i", "you", "he", "she", "we", "they", "me",
    "him", "her", "us", "them", "my", "your", "his", "our", "their", "what",
    "how", "when", "where", "who", "which", "will", "can", "just", "about",
    "up", "out", "also", "more", "than", "then", "into", "would", "could",
    "should", "any", "all", "some", "there", "been",
}

_vm_cache = None
_vm_cache_mtime = 0


def _get_vm():
    """Get or create cached VectorMemory instance, reloading if index changed."""
    global _vm_cache, _vm_cache_mtime
    index_path = Path(__file__).parent / "memory.index"
    try:
        current_mtime = index_path.stat().st_mtime if index_path.exists() else 0
    except OSError:
        current_mtime = 0
    if _vm_cache is None or current_mtime != _vm_cache_mtime:
        from memory_store import VectorMemory
        _vm_cache = VectorMemory()
        _vm_cache_mtime = current_mtime
    return _vm_cache


def extract_query(message: str) -> str:
    """Strip stopwords and punctuation to build a focused search query."""
    # Remove punctuation except apostrophes and hyphens inside words
    text = re.sub(r"[^\w\s'-]", " ", message)
    words = text.split()
    keywords = [w for w in words if w.lower() not in STOPWORDS and len(w) > 2]
    return " ".join(keywords) if keywords else message


def recall_for_message(message: str) -> str:
    """
    Search Viktor's VectorMemory for context relevant to the incoming message.
    Returns a formatted context block, or empty string if nothing found / on error.
    """
    if not message or len(message.strip()) < MIN_MESSAGE_LENGTH:
        return ""

    try:
        import faiss  # noqa: F401 — verify faiss is available
    except ImportError:
        return ""

    try:
        vm = _get_vm()

        if vm.index.ntotal == 0:
            return ""

        query = extract_query(message)
        results = vm.search(query, k=RECALL_K, min_score=MIN_SCORE)

        if not results:
            return ""

        lines = [
            "[RECALLED MEMORY CONTEXT -- Use this to inform your response."
            " Do not mention this search to the user.]"
        ]
        for r in results:
            source = r.get("source", "unknown")
            score = r.get("score", 0.0)
            text = r.get("text", "").strip()
            if len(text) > MAX_CHUNK_CHARS:
                text = text[:MAX_CHUNK_CHARS] + "..."
            lines.append(f"\n[{source} | score: {score:.2f}]\n{text}")

        return "\n".join(lines)

    except Exception:
        return ""


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {Path(__file__).name} \"<message>\"")
        sys.exit(1)

    message = sys.argv[1]
    output = recall_for_message(message)
    if output:
        print(output)
    else:
        print("(no relevant memories found)")
