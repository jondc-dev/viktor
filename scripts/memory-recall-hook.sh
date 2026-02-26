#!/usr/bin/env bash
# memory-recall-hook.sh — Pre-response memory recall wrapper for Viktor
# Usage: memory-recall-hook.sh "<message>" [session_id]
# Always exits 0 (graceful degradation).

VIKTOR_WORKSPACE="${VIKTOR_WORKSPACE:-$HOME/clawd}"
VIKTOR_PYTHON="${VIKTOR_PYTHON:-$VIKTOR_WORKSPACE/vector-memory/venv/bin/python3}"
HOOK_SCRIPT="$VIKTOR_WORKSPACE/scripts/memory-recall-hook.py"
VENV_ACTIVATE="$VIKTOR_WORKSPACE/vector-memory/venv/bin/activate"

MESSAGE="${1:-}"

if [ -z "$MESSAGE" ]; then
    exit 0
fi

# Verify the hook script exists
if [ ! -f "$HOOK_SCRIPT" ]; then
    exit 0
fi

# Activate the venv if it exists
if [ -f "$VENV_ACTIVATE" ]; then
    # shellcheck source=/dev/null
    source "$VENV_ACTIVATE"
fi

# Quick sanity check: make sure faiss is importable
if ! "$VIKTOR_PYTHON" -c "import faiss" 2>/dev/null; then
    exit 0
fi

# Run from the workspace directory so relative paths inside the script resolve
cd "$VIKTOR_WORKSPACE" || exit 0

exec "$VIKTOR_PYTHON" "$HOOK_SCRIPT" "$MESSAGE"
