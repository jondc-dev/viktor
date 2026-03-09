#!/usr/bin/env python3
"""
Simple email checker using keychain credentials
"""

import imaplib
import email
import subprocess
import sys
from datetime import datetime

def get_keychain_creds():
    """Get credentials from keychain."""
    result = subprocess.run([
        sys.executable, '/Users/victor/clawd/keychain.py', 'get', 'saniservice_email'
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        return None, None
    
    lines = result.stdout.strip().split('\n')
    username = None
    password = None
    
    for line in lines:
        if line.startswith('Username:'):
            username = line.split(':', 1)[1].strip()
        elif line.startswith('Password:'):
            password = line.split(':', 1)[1].strip()
    
    return username, password

def check_recent_emails():
    """Check recent emails."""
    username, password = get_keychain_creds()
    
    if not username or not password:
        print("Could not get credentials from keychain")
        return
    
    try:
        mail = imaplib.IMAP4_SSL('mail.saniservice.com', 993)
        mail.login(username, password)
        mail.select('INBOX')
        
        # Get last 10 emails
        status, messages = mail.search(None, 'ALL')
        if status == 'OK':
            message_ids = messages[0].split()
            print(f"Total emails in inbox: {len(message_ids)}")
            
            # Show last 5 emails
            for msg_id in reversed(message_ids[-5:]):
                status, msg_data = mail.fetch(msg_id, '(RFC822)')
                if status == 'OK':
                    msg = email.message_from_bytes(msg_data[0][1])
                    print(f"\nFrom: {msg['From']}")
                    print(f"Subject: {msg['Subject']}")
                    print(f"Date: {msg['Date']}")
                    print("-" * 40)
        
        mail.logout()
        
    except Exception as e:
        print(f"Error checking emails: {e}")

if __name__ == "__main__":
    check_recent_emails()