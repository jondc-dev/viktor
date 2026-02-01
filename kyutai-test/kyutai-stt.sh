#!/bin/bash
# Kyutai STT wrapper (MLX)
# Usage: kyutai-stt.sh <audio_file> [output_file]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/venv/bin/activate"

INPUT="$1"
OUTPUT="${2:-/dev/stdout}"

if [ -z "$INPUT" ]; then
    echo "Usage: kyutai-stt.sh <audio_file> [output_file]"
    exit 1
fi

python -m moshi_mlx.run_inference \
    --hf-repo kyutai/stt-1b-en_fr-mlx \
    "$INPUT" \
    --temp 0 2>/dev/null | tail -1 > "$OUTPUT"
