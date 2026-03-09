#!/bin/bash
# Quick email check using keychain credentials

echo "Getting email credentials from keychain..."
CREDS=$(python3 /Users/victor/clawd/keychain.py get saniservice_email 2>/dev/null | grep -E "(Username|Password):" | cut -d: -f2 | tr -d ' ')

EMAIL_USER=$(echo "$CREDS" | head -1)
EMAIL_PASS=$(echo "$CREDS" | tail -1)

if [ -z "$EMAIL_USER" ] || [ -z "$EMAIL_PASS" ]; then
    echo "Error: Could not get credentials from keychain"
    exit 1
fi

echo "Checking emails for $EMAIL_USER..."
EMAIL_USER="$EMAIL_USER" EMAIL_PASS="$EMAIL_PASS" python3 /Users/victor/clawd/scripts/email_client.py search "ALL"