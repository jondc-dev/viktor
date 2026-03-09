#!/bin/bash

# Frontdesk Email Snapshot Collection Script
# Collects client-facing emails from all 7 frontdesk accounts

OUTPUT_DIR="$HOME/clawd/memory/email-snapshots"
DATE=$(date +%Y-%m-%d)
OUTPUT_FILE="$OUTPUT_DIR/${DATE}-10am.json"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Initialize JSON array
echo "[" > "$OUTPUT_FILE"

# List of frontdesk accounts
ACCOUNTS=(
    "fareed@saniservice.com"
    "eby@saniservice.com" 
    "shijith@saniservice.com"
    "sageer@saniservice.com"
    "arjun@saniservice.com"
    "rodrigo@saniservice.com"
    "frontdesk@saniservice.com"
)

# Function to get password from keychain
get_password() {
    local email="$1"
    security find-generic-password -a "$email" -s "saniservice-email" -w 2>/dev/null
}

# Function to check if email is client-facing (not internal)
is_client_facing() {
    local from="$1"
    local to="$2"
    
    # Check if sender or recipient is external (not @saniservice.com)
    if [[ ! "$from" =~ @saniservice\.com$ ]] || [[ ! "$to" =~ @saniservice\.com$ ]]; then
        return 0  # Client-facing
    else
        return 1  # Internal
    fi
}

# Function to escape JSON strings
escape_json() {
    echo "$1" | sed 's/\\/\\\\/g; s/"/\\"/g; s/\n/\\n/g; s/\r/\\r/g; s/\t/\\t/g'
}

first_entry=true

for account in "${ACCOUNTS[@]}"; do
    echo "Processing account: $account"
    
    # Get password from keychain
    password=$(get_password "$account")
    if [ -z "$password" ]; then
        echo "Warning: Could not retrieve password for $account"
        continue
    fi
    
    # Create temporary config for this account
    temp_config="/tmp/himalaya-$account.toml"
    cat > "$temp_config" << EOF
[accounts.temp]
email = "$account"
display-name = "$account"
default = true

backend.type = "imap"
backend.host = "imap.saniservice.com"
backend.port = 993
backend.encryption.type = "tls"
backend.login = "$account"
backend.auth.type = "password"
backend.auth.raw = "$password"

message.send.backend.type = "smtp"
message.send.backend.host = "smtp.saniservice.com"
message.send.backend.port = 587
message.send.backend.encryption.type = "start-tls"
message.send.backend.login = "$account"
message.send.backend.auth.type = "password"
message.send.backend.auth.raw = "$password"
EOF
    
    # Set config path for himalaya
    export HIMALAYA_CONFIG="$temp_config"
    
    # Get today's date in format that matches email timestamps
    today=$(date +%Y-%m-%d)
    
    # Get received emails from today
    echo "  Checking received emails..."
    received_emails=$(himalaya --config "$temp_config" envelope list --output json 2>/dev/null | jq -r '.[] | select(.timestamp | startswith("'$today'")) | @base64' 2>/dev/null || true)
    
    for email_b64 in $received_emails; do
        email_json=$(echo "$email_b64" | base64 -d)
        
        # Extract email details
        from=$(echo "$email_json" | jq -r '.from // empty')
        to=$(echo "$email_json" | jq -r '.to // empty')
        subject=$(echo "$email_json" | jq -r '.subject // "No Subject"')
        timestamp=$(echo "$email_json" | jq -r '.timestamp // empty')
        id=$(echo "$email_json" | jq -r '.id // empty')
        
        # Skip if missing critical fields
        if [ -z "$from" ] || [ -z "$to" ] || [ -z "$id" ]; then
            continue
        fi
        
        # Check if client-facing
        if is_client_facing "$from" "$to"; then
            # Get full message body
            body=$(himalaya --config "$temp_config" message read "$id" 2>/dev/null | head -100 | tr '\n' ' ' | sed 's/"/\\"/g' || echo "Body unavailable")
            
            # Add to JSON
            if [ "$first_entry" = true ]; then
                first_entry=false
            else
                echo "," >> "$OUTPUT_FILE"
            fi
            
            cat >> "$OUTPUT_FILE" << EOF
{
  "account": "$account",
  "direction": "received",
  "from": "$(escape_json "$from")",
  "to": "$(escape_json "$to")",
  "subject": "$(escape_json "$subject")",
  "body": "$(escape_json "$body")",
  "timestamp": "$timestamp"
}
EOF
        fi
    done
    
    # Get sent emails from today
    echo "  Checking sent emails..."
    sent_emails=$(himalaya --config "$temp_config" envelope list --folder "Sent" --output json 2>/dev/null | jq -r '.[] | select(.timestamp | startswith("'$today'")) | @base64' 2>/dev/null || true)
    
    for email_b64 in $sent_emails; do
        email_json=$(echo "$email_b64" | base64 -d)
        
        # Extract email details
        from=$(echo "$email_json" | jq -r '.from // empty')
        to=$(echo "$email_json" | jq -r '.to // empty')
        subject=$(echo "$email_json" | jq -r '.subject // "No Subject"')
        timestamp=$(echo "$email_json" | jq -r '.timestamp // empty')
        id=$(echo "$email_json" | jq -r '.id // empty')
        
        # Skip if missing critical fields
        if [ -z "$from" ] || [ -z "$to" ] || [ -z "$id" ]; then
            continue
        fi
        
        # Check if client-facing
        if is_client_facing "$from" "$to"; then
            # Get full message body
            body=$(himalaya --config "$temp_config" message read "$id" 2>/dev/null | head -100 | tr '\n' ' ' | sed 's/"/\\"/g' || echo "Body unavailable")
            
            # Add to JSON
            if [ "$first_entry" = true ]; then
                first_entry=false
            else
                echo "," >> "$OUTPUT_FILE"
            fi
            
            cat >> "$OUTPUT_FILE" << EOF
{
  "account": "$account",
  "direction": "sent",
  "from": "$(escape_json "$from")",
  "to": "$(escape_json "$to")",
  "subject": "$(escape_json "$subject")",
  "body": "$(escape_json "$body")",
  "timestamp": "$timestamp"
}
EOF
        fi
    done
    
    # Clean up temp config
    rm -f "$temp_config"
done

# Close JSON array
echo "" >> "$OUTPUT_FILE"
echo "]" >> "$OUTPUT_FILE"

echo "Email snapshot completed: $OUTPUT_FILE"

# Count emails per account
echo "Summary by account:"
for account in "${ACCOUNTS[@]}"; do
    count=$(jq -r --arg account "$account" '.[] | select(.account == $account) | .account' "$OUTPUT_FILE" | wc -l)
    echo "  $account: $count emails"
done

total_emails=$(jq '. | length' "$OUTPUT_FILE")
echo "Total client-facing emails collected: $total_emails"