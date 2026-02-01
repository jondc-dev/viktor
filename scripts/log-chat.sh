#!/bin/bash
# Log a chat message to today's memory file
# Usage: log-chat.sh <from> <message>

FROM="$1"
shift
MESSAGE="$*"

TODAY=$(date +%Y-%m-%d)
TIME=$(TZ=Asia/Dubai date +"%H:%M")
MEMORY_FILE="$HOME/clawd/memory/${TODAY}.md"

# Ensure memory dir exists
mkdir -p "$HOME/clawd/memory"

# Create file with header if it doesn't exist
if [ ! -f "$MEMORY_FILE" ]; then
    echo "# ${TODAY}" > "$MEMORY_FILE"
    echo "" >> "$MEMORY_FILE"
fi

# Add Chat Log section if it doesn't exist
if ! grep -q "## Chat Log" "$MEMORY_FILE"; then
    echo "" >> "$MEMORY_FILE"
    echo "## Chat Log" >> "$MEMORY_FILE"
fi

# Append the message
echo "" >> "$MEMORY_FILE"
echo "**${TIME} - ${FROM}:** ${MESSAGE}" >> "$MEMORY_FILE"
