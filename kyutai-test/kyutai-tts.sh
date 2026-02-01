#!/bin/bash
# Kyutai TTS wrapper (MLX)
# Usage: kyutai-tts.sh <output_file> [text]
# Or: echo "text" | kyutai-tts.sh <output_file>

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/venv/bin/activate"

OUTPUT="$1"
TEXT="$2"

if [ -z "$OUTPUT" ]; then
    echo "Usage: kyutai-tts.sh <output_file> [text]"
    echo "Or: echo 'text' | kyutai-tts.sh <output_file>"
    exit 1
fi

if [ -n "$TEXT" ]; then
    echo "$TEXT" | python "$SCRIPT_DIR/dsm/scripts/tts_mlx.py" - "$OUTPUT" --quantize 8 2>/dev/null
else
    python "$SCRIPT_DIR/dsm/scripts/tts_mlx.py" - "$OUTPUT" --quantize 8 2>/dev/null
fi
