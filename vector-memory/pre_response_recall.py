#!/usr/bin/env python3
"""
Pre-response memory recall for Viktor.
Searches VectorMemory (FAISS) for relevant context before each response.
Always emits a [RECALL STATUS: ...] header so callers can detect failures.
"""

import re
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE_ROOT = Path("~/clawd").expanduser()
SECOND_BRAIN_DIR = WORKSPACE_ROOT / "second-brain"
RECALL_FAILURES_LOG = SECOND_BRAIN_DIR / "recall-failures.log"
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


def _log_recall_failure(reason: str) -> None:
    """Log a recall failure with timestamp to second-brain/recall-failures.log."""
    try:
        SECOND_BRAIN_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(RECALL_FAILURES_LOG, "a") as f:
            f.write(f"[{ts}] RECALL FAILED: {reason}\n")
    except Exception:
        pass  # Never crash on logging failure


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
    Returns a formatted context block with a [RECALL STATUS: ...] header.
    Never returns an empty string — always includes the status header.
    """
    if not message or len(message.strip()) < MIN_MESSAGE_LENGTH:
        return "[RECALL STATUS: SKIPPED — message too short]"

    try:
        import faiss  # noqa: F401 — verify faiss is available
    except ImportError:
        _log_recall_failure("faiss not importable")
        return "[RECALL STATUS: FAILED — faiss not available]"

    try:
        # memory_store.py lives alongside this file in vector-memory/
        sys.path.insert(0, str(Path(__file__).parent))
        from memory_store import VectorMemory

        vm = VectorMemory()

        if vm.index.ntotal == 0:
            return "[RECALL STATUS: 0 memory results, 0 session results]"

        query = extract_query(message)
        results = vm.search(query, k=RECALL_K, min_score=MIN_SCORE)

        if not results:
            return "[RECALL STATUS: 0 memory results, 0 session results]"

        lines = [
            f"[RECALL STATUS: {len(results)} memory results, 0 session results]",
            "",
            "[RECALLED MEMORY CONTEXT -- Use this to inform your response."
            " Do not mention this search to the user.]",
        ]
        for r in results:
            source = r.get("source", "unknown")
            score = r.get("score", 0.0)
            text = r.get("text", "").strip()
            if len(text) > MAX_CHUNK_CHARS:
                text = text[:MAX_CHUNK_CHARS] + "..."
            lines.append(f"\n[{source} | score: {score:.2f}]\n{text}")

        return "\n".join(lines)

    except Exception as exc:
        _log_recall_failure(str(exc))
        return f"[RECALL STATUS: FAILED — {exc}]"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {Path(__file__).name} \"<message>\"")
        sys.exit(1)

    message = sys.argv[1]
    print(recall_for_message(message))
