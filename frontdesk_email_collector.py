#!/usr/bin/env python3
"""
Frontdesk Email Analysis Script
Collects today's client-facing emails from all frontdesk accounts for coaching analysis.
"""

import imaplib
import email
import os
import sys
from datetime import datetime, timedelta
from email.header import decode_header
import json

def connect_imap(email_user, email_pass):
    """Connect to IMAP server."""
    try:
        imap = imaplib.IMAP4_SSL("mail.saniservice.com", 993)
        imap.login(email_user, email_pass)
        return imap
    except Exception as e:
        print(f"Failed to connect {email_user}: {e}")
        return None

def get_today_emails(imap, folder="INBOX"):
    """Get emails from today."""
    try:
        imap.select(folder)
        today = datetime.now().strftime("%d-%b-%Y")
        status, messages = imap.search(None, f'SINCE "{today}"')
        
        if status != 'OK':
            return []
            
        email_ids = messages[0].split()
        emails = []
        
        for email_id in email_ids:
            status, msg_data = imap.fetch(email_id, '(RFC822)')
            if status == 'OK':
                msg = email.message_from_bytes(msg_data[0][1])
                
                # Extract basic info
                subject = decode_header(msg.get("Subject", ""))[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode('utf-8', errors='ignore')
                
                from_addr = msg.get("From", "")
                to_addr = msg.get("To", "")
                date = msg.get("Date", "")
                
                # Get email body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            break
                        elif part.get_content_type() == "text/html":
                            body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            break
                else:
                    body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                
                emails.append({
                    'id': email_id.decode(),
                    'subject': subject,
                    'from': from_addr,
                    'to': to_addr,
                    'date': date,
                    'body': body[:1000]  # First 1000 chars for analysis
                })
        
        return emails
    except Exception as e:
        print(f"Error getting emails: {e}")
        return []

def is_client_facing(email_data):
    """Check if email is client-facing based on content and recipients."""
    body = email_data.get('body', '').lower()
    subject = email_data.get('subject', '').lower()
    to_addr = email_data.get('to', '').lower()
    from_addr = email_data.get('from', '').lower()
    
    # Check for external domains (not saniservice.com)
    external_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'ae', 'com', 'org']
    is_external = any(domain in to_addr or domain in from_addr for domain in external_domains)
    
    # Check for client-related keywords
    client_keywords = ['customer', 'client', 'service', 'appointment', 'quote', 'invoice', 'booking']
    has_client_content = any(keyword in body or keyword in subject for keyword in client_keywords)
    
    return is_external and has_client_content

def main():
    # Frontdesk accounts
    accounts = [
        'fareed@saniservice.com',
        'eby@saniservice.com', 
        'shijith@saniservice.com',
        'sageer@saniservice.com',
        'arjun@saniservice.com',
        'rodrigo@saniservice.com',
        'frontdesk@saniservice.com'
    ]
    
    # Get email password from keychain
    try:
        email_pass = os.popen("security find-generic-password -a 'viktor@saniservice.com' -s 'saniservice-email' -w").read().strip()
    except:
        print("Failed to get email password from keychain")
        sys.exit(1)
    
    all_emails = {}
    
    for account in accounts:
        print(f"Checking {account}...")
        imap = connect_imap(account, email_pass)
        if not imap:
            continue
            
        # Get emails from both INBOX and Sent
        inbox_emails = get_today_emails(imap, "INBOX")
        sent_emails = get_today_emails(imap, "Sent")
        
        # Filter for client-facing emails
        client_emails = []
        for email_data in inbox_emails + sent_emails:
            if is_client_facing(email_data):
                client_emails.append(email_data)
        
        if client_emails:
            all_emails[account] = client_emails
            print(f"  Found {len(client_emails)} client-facing emails")
        
        imap.logout()
    
    # Save results
    with open('/Users/victor/clawd/frontdesk_emails_today.json', 'w') as f:
        json.dump(all_emails, f, indent=2, default=str)
    
    print(f"\nAnalysis complete. Found emails from {len(all_emails)} accounts.")
    return all_emails

if __name__ == "__main__":
    main()