#!/bin/bash
# Morning Brief Generator
# Runs at 8am Dubai time daily

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$HOME/clawd"
OUTPUT_DIR="$WORKSPACE/morning-briefs"
DATE=$(date +"%Y-%m-%d")
BRIEF_FILE="$OUTPUT_DIR/brief-$DATE.html"

mkdir -p "$OUTPUT_DIR"

# Get weather
WEATHER=$(curl -s "wttr.in/Dubai?format=%c+%t+%h+%w" 2>/dev/null || echo "☀️ 25°C 60% →10km/h")
WEATHER_DETAIL=$(curl -s "wttr.in/Dubai?format=j1" 2>/dev/null | head -50 || echo "{}")

# Generate brief via clawdbot
clawdbot run --task "Generate the morning brief for today ($DATE). Output ONLY the HTML content for the email (no explanation). Weather: $WEATHER" --timeout 120 > "$BRIEF_FILE"

echo "Brief generated: $BRIEF_FILE"
