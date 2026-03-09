#!/bin/bash
# Collect today's client-facing emails from all frontdesk accounts

# Get email password from keychain
EMAIL_PASS=$(security find-generic-password -a 'viktor@saniservice.com' -s 'saniservice-email' -w)

# List of frontdesk accounts
accounts=(
    "fareed@saniservice.com"
    "eby@saniservice.com" 
    "shijith@saniservice.com"
    "sageer@saniservice.com"
    "arjun@saniservice.com"
    "rodrigo@saniservice.com"
    "frontdesk@saniservice.com"
)

# Today's date in IMAP format (DD-MMM-YYYY)
TODAY=$(date +%d-%b-%Y)

echo "=== FRONTDESK EMAIL ANALYSIS - $(date) ==="
echo ""

for account in "${accounts[@]}"; do
    echo "--- $account ---"
    
    # Search for emails from today in INBOX
    python3 ~/clawd/scripts/email_client.py search --folder INBOX "SINCE $TODAY" 2>/dev/null | head -20
    
    # Search for emails from today in SENT
    python3 ~/clawd/scripts/email_client.py search --folder Sent "SINCE $TODAY" 2>/dev/null | head -20
    
    echo ""
done