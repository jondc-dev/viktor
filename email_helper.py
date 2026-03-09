#!/usr/bin/env python3
"""
Email Helper - Easy email access using keychain credentials

This script provides a simple interface to check emails using
credentials stored in the keychain.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add the workspace to path
sys.path.insert(0, '/Users/victor/clawd')

def check_frontdesk_emails():
    """Check for frontdesk-related emails using stored credentials."""
    
    # Get credentials from keychain
    result = subprocess.run([
        sys.executable, '/Users/victor/clawd/keychain.py', 'get', 'saniservice_email'
    ], capture_output=True, text=True)
    
    if result.returncode != 0 or 'Username:' not in result.stdout:
        print("Error: Could not retrieve email credentials from keychain")
        return False
    
    # Extract credentials from output
    lines = result.stdout.strip().split('\n')
    username = None
    password = None
    
    for line in lines:
        if line.startswith('Username:'):
            username = line.split(':', 1)[1].strip()
        elif line.startswith('Password:'):
            password = line.split(':', 1)[1].strip()
    
    if not username or not password:
        print("Error: Could not parse credentials")
        return False
    
    # Set environment variables
    env = os.environ.copy()
    env['EMAIL_USER'] = username
    env['EMAIL_PASS'] = password
    
    # Check for recent emails
    print("Checking recent emails...")
    subprocess.run([
        sys.executable, '/Users/victor/clawd/scripts/email_client.py', 'search', 'ALL'
    ], env=env)
    
    return True

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nUsage:")
        print("  email_helper.py frontdesk    - Check for frontdesk emails")
        print("  email_helper.py today        - Check today's emails")
        print("  email_helper.py inbox        - Show recent inbox")
        return
    
    command = sys.argv[1]
    
    if command == "frontdesk":
        check_frontdesk_emails()
    elif command == "today":
        # Implementation for today's emails
        print("Checking today's emails...")
    elif command == "inbox":
        # Show recent inbox
        print("Showing recent inbox...")
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()