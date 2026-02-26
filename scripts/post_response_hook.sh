#!/usr/bin/env bash
# post_response_hook.sh — Post-response accountability wrapper for Viktor
# Usage: post_response_hook.sh "<assistant_response_text>"
# Always exits 0 (graceful degradation).

VIKTOR_WORKSPACE="${VIKTOR_WORKSPACE:-$HOME/clawd}"
VIKTOR_PYTHON="${VIKTOR_PYTHON:-$VIKTOR_WORKSPACE/vector-memory/venv/bin/python3}"
SCRIPT="$VIKTOR_WORKSPACE/scripts/post_response_hook.py"
VENV_ACTIVATE="$VIKTOR_WORKSPACE/vector-memory/venv/bin/activate"

RESPONSE_TEXT="${1:-}"

if [ -z "$RESPONSE_TEXT" ]; then
    exit 0
fi

if [ ! -f "$SCRIPT" ]; then
    exit 0
fi

# Activate the venv if it exists
if [ -f "$VENV_ACTIVATE" ]; then
    # shellcheck source=/dev/null
    source "$VENV_ACTIVATE"
fi

cd "$VIKTOR_WORKSPACE" || exit 0

"$VIKTOR_PYTHON" "$SCRIPT" "$RESPONSE_TEXT" 2>/dev/null || true
exit 0
