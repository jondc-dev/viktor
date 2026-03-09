#!/bin/bash
# Frontdesk Email Snapshot Collection Script
# Collects client-facing emails from all frontdesk accounts

OUTPUT_DIR="$HOME/clawd/memory/email-snapshots"
DATE=$(date +%Y-%m-%d)
OUTPUT_FILE="$OUTPUT_DIR/${DATE}-10am.json"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Frontdesk email accounts
ACCOUNTS=(
    "fareed@saniservice.com"
    "eby@saniservice.com" 
    "shijith@saniservice.com"
    "sageer@saniservice.com"
    "arjun@saniservice.com"
    "rodrigo@saniservice.com"
    "frontdesk@saniservice.com"
)

# Initialize JSON array
echo '[' > "$OUTPUT_FILE"

TOTAL_EMAILS=0
FIRST_ENTRY=true

for ACCOUNT in "${ACCOUNTS[@]}"; do
    echo "Processing account: $ACCOUNT"
    ACCOUNT_EMAILS=0
    
    # Get emails from today (received)
    RECEIVED_JSON=$(himalaya --account "$ACCOUNT" envelope list --output json 2>/dev/null | jq -r '.[] | select(.timestamp | startswith("'$(date +%Y-%m-06)'") or startswith("'$(date +%Y-%m-05)')) | select(.from | test("@(saniservice\.com)$") | not) | {account: "'$ACCOUNT'", from: .from, to: .to, subject: .subject, timestamp: .timestamp, direction: "received", body: ""}' 2>/dev/null || echo "[]")
    
    # Get sent emails from today
    SENT_JSON=$(himalaya --account "$ACCOUNT" envelope list --folder "Sent" --output json 2>/dev/null | jq -r '.[] | select(.timestamp | startswith("'$(date +%Y-%m-06)'") or startswith("'$(date +%Y-%m-05)')) | select(.to | test("@(saniservice\.com)$") | not) | {account: "'$ACCOUNT'", from: .from, to: .to, subject: .subject, timestamp: .timestamp, direction: "sent", body: ""}' 2>/dev/null || echo "[]")
    
    # Combine and add to output
    if [ "$FIRST_ENTRY" = false ]; then
        echo "," >> "$OUTPUT_FILE"
    fi
    
    # Count emails for this account
    RECEIVED_COUNT=$(echo "$RECEIVED_JSON" | jq '. | length' 2>/dev/null || echo "0")
    SENT_COUNT=$(echo "$SENT_JSON" | jq '. | length' 2>/dev/null || echo "0")
    ACCOUNT_EMAILS=$((RECEIVED_COUNT + SENT_COUNT))
    TOTAL_EMAILS=$((TOTAL_EMAILS + ACCOUNT_EMAILS))
    
    # Write account summary
    echo "  // $ACCOUNT: $ACCOUNT_EMAILS emails" >> "$OUTPUT_FILE"
    
    # Add received emails
    if [ "$RECEIVED_COUNT" -gt 0 ]; then
        echo "$RECEIVED_JSON" | jq -c '.[]' | while read -r line; do
            if [ "$FIRST_ENTRY" = false ]; then
                echo "," >> "$OUTPUT_FILE"
            fi
            echo -n "  $line" >> "$OUTPUT_FILE"
            FIRST_ENTRY=false
        done
    fi
    
    # Add sent emails
    if [ "$SENT_COUNT" -gt 0 ]; then
        echo "$SENT_JSON" | jq -c '.[]' | while read -r line; do
            if [ "$FIRST_ENTRY" = false ]; then
                echo "," >> "$OUTPUT_FILE"
            fi
            echo -n "  $line" >> "$OUTPUT_FILE"
            FIRST_ENTRY=false
        done
    fi
    
    echo "Collected $ACCOUNT_EMAILS emails from $ACCOUNT"
done

echo '' >> "$OUTPUT_FILE"
echo ']' >> "$OUTPUT_FILE"

echo "Total emails collected: $TOTAL_EMAILS"
echo "Snapshot saved to: $OUTPUT_FILE"