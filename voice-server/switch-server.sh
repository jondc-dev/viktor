#!/bin/bash
# Switch between voice server versions

cd "$(dirname "$0")"

MODE="${1:-status}"

kill_servers() {
  pkill -f "node server.js" 2>/dev/null
  pkill -f "node server-hybrid.js" 2>/dev/null
  pkill -f "node server-direct.js" 2>/dev/null
  pkill -f "node server-vonage-haiku.js" 2>/dev/null
  sleep 1
}

case "$MODE" in
  fast|v10)
    echo "Switching to v10 (Vonage ASR → Haiku Direct → ElevenLabs TTS)..."
    kill_servers
    nohup node server-vonage-haiku.js >> server.log 2>&1 &
    echo "Started server-vonage-haiku.js (PID: $!)"
    echo "⚡ Reliable STT + fast Haiku — best of both worlds"
    ;;
  direct|v9)
    echo "Switching to v9 (Direct: Kyutai STT → Haiku → ElevenLabs TTS)..."
    kill_servers
    nohup node server-direct.js >> server.log 2>&1 &
    echo "Started server-direct.js (PID: $!)"
    echo "⚡ No queue — experimental Kyutai"
    ;;
  hybrid|v8)
    echo "Switching to v8 (Hybrid: Kyutai STT + Queue + ElevenLabs TTS)..."
    kill_servers
    nohup node server-hybrid.js >> server.log 2>&1 &
    echo "Started server-hybrid.js (PID: $!)"
    ;;
  original|v7)
    echo "Switching to v7 (Vonage ASR + Queue + ElevenLabs TTS)..."
    kill_servers
    nohup node server.js >> server.log 2>&1 &
    echo "Started server.js (PID: $!)"
    ;;
  status)
    if pgrep -f "server-vonage-haiku.js" > /dev/null; then
      echo "Running: v10 (Vonage ASR → Haiku Direct → ElevenLabs TTS)"
    elif pgrep -f "server-direct.js" > /dev/null; then
      echo "Running: v9 (Kyutai STT → Haiku → ElevenLabs TTS)"
    elif pgrep -f "server-hybrid.js" > /dev/null; then
      echo "Running: v8 (Kyutai STT + Queue)"  
    elif pgrep -f "server.js" > /dev/null; then
      echo "Running: v7 (Vonage ASR + Queue)"  
    else
      echo "No server running"
    fi
    ;;
  *)
    echo "Usage: $0 [fast|direct|hybrid|original|status]"
    echo ""
    echo "  fast     - v10: Vonage ASR → Haiku direct → ElevenLabs TTS (recommended)"
    echo "  direct   - v9: Kyutai STT → Haiku direct → ElevenLabs TTS (experimental)"
    echo "  hybrid   - v8: Kyutai STT → Queue → Agent → ElevenLabs TTS"
    echo "  original - v7: Vonage ASR → Queue → Agent → ElevenLabs TTS"
    echo "  status   - Show current mode"
    ;;
esac
