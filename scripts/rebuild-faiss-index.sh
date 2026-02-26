#!/usr/bin/env bash
# rebuild-faiss-index.sh — Trigger a FAISS index rebuild for Viktor.
# Suitable for cron/LaunchAgent scheduling.
# Logs output to ~/clawd/vector-memory/rebuild.log.
# Always exits 0 (graceful degradation).

VIKTOR_WORKSPACE="${VIKTOR_WORKSPACE:-$HOME/clawd}"
VENV_ACTIVATE="$VIKTOR_WORKSPACE/vector-memory/venv/bin/activate"
VIKTOR_PYTHON="${VIKTOR_PYTHON:-$VIKTOR_WORKSPACE/vector-memory/venv/bin/python3}"
INGEST_SCRIPT="$VIKTOR_WORKSPACE/vector-memory/ingest_memories.py"
LOG_FILE="$VIKTOR_WORKSPACE/vector-memory/rebuild.log"

mkdir -p "$(dirname "$LOG_FILE")"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] rebuild-faiss-index: starting" >> "$LOG_FILE"

if [ ! -f "$INGEST_SCRIPT" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: ingest_memories.py not found at $INGEST_SCRIPT" >> "$LOG_FILE"
    exit 0
fi

# Activate the venv if it exists
if [ -f "$VENV_ACTIVATE" ]; then
    # shellcheck source=/dev/null
    source "$VENV_ACTIVATE"
fi

cd "$VIKTOR_WORKSPACE" || exit 0

"$VIKTOR_PYTHON" "$INGEST_SCRIPT" >> "$LOG_FILE" 2>&1
STATUS=$?

if [ $STATUS -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] rebuild-faiss-index: complete (exit 0)" >> "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] rebuild-faiss-index: FAILED (exit $STATUS)" >> "$LOG_FILE"
fi

exit 0
