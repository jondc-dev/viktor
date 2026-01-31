#!/bin/bash
# Start Viktor Voice Server with ngrok

cd "$(dirname "$0")"

# Start ngrok in background
echo "Starting ngrok..."
ngrok http 3000 --log=stdout > ngrok.log 2>&1 &
NGROK_PID=$!
sleep 3

# Get ngrok URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"https://[^"]*' | cut -d'"' -f4)

if [ -z "$NGROK_URL" ]; then
  echo "Failed to get ngrok URL"
  kill $NGROK_PID 2>/dev/null
  exit 1
fi

echo "Ngrok URL: $NGROK_URL"
echo ""
echo "Configure these webhooks in Vonage Dashboard:"
echo "  Answer URL: ${NGROK_URL}/answer"
echo "  Event URL:  ${NGROK_URL}/event"
echo ""

# Export for the server
export NGROK_URL
export PORT=3000

# Start server
echo "Starting voice server..."
node server.js
