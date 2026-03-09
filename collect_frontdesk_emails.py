#!/usr/bin/env python3
"""
Frontdesk Email Snapshot Collection
Collects client-facing emails from all frontdesk accounts for today's 10AM snapshot
"""

import json
import subprocess
import datetime
import os
from pathlib import Path

def run_himalaya_command(account, folder="INBOX", extra_args=[]):
    """Run himalaya command and return JSON output"""
    try:
        cmd = ["himalaya", "--account", account, "envelope", "list", "--output", "json"] + extra_args
        if folder != "INBOX":
            cmd.extend(["--folder", folder])
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
        return []
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
        print(f"Error accessing {account} {folder}: {e}")
        return []

def is_internal_email(email):
    """Check if email is internal (saniservice.com domain)"""
    if not email:
        return False
    return "saniservice.com" in email.lower()

def is_client_facing(email_data, direction):
    """Determine if email is client-facing (not internal)"""
    if direction == "received":
        # For received emails, sender should not be internal
        return not is_internal_email(email_data.get("from", ""))
    else:  # sent
        # For sent emails, recipient should not be internal
        recipients = email_data.get("to", "")
        if isinstance(recipients, list):
            recipients = " ".join(recipients)
        return not is_internal_email(recipients)

def collect_emails_for_account(account, today_str):
    """Collect client-facing emails for a specific account"""
    emails = []
    
    # Collect received emails
    received_emails = run_himalaya_command(account)
    for email in received_emails:
        if email.get("timestamp", "").startswith(today_str) and is_client_facing(email, "received"):
            emails.append({
                "account": account,
                "from": email.get("from", ""),
                "to": email.get("to", ""),
                "subject": email.get("subject", ""),
                "timestamp": email.get("timestamp", ""),
                "direction": "received",
                "body": ""  # We'll skip body content for now to avoid large downloads
            })
    
    # Collect sent emails
    sent_emails = run_himalaya_command(account, folder="Sent")
    for email in sent_emails:
        if email.get("timestamp", "").startswith(today_str) and is_client_facing(email, "sent"):
            emails.append({
                "account": account,
                "from": email.get("from", ""),
                "to": email.get("to", ""),
                "subject": email.get("subject", ""),
                "timestamp": email.get("timestamp", ""),
                "direction": "sent",
                "body": ""  # We'll skip body content for now to avoid large downloads
            })
    
    return emails

def main():
    # Configuration
    accounts = [
        "fareed@saniservice.com",
        "eby@saniservice.com",
        "shijith@saniservice.com", 
        "sageer@saniservice.com",
        "arjun@saniservice.com",
        "rodrigo@saniservice.com",
        "frontdesk@saniservice.com"
    ]
    
    # Setup directories
    output_dir = Path.home() / "clawd" / "memory" / "email-snapshots"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get today's date
    today = datetime.date.today()
    today_str = today.strftime("%Y-%m-%d")
    output_file = output_dir / f"{today_str}-10am.json"
    
    print(f"Collecting frontdesk email snapshot for {today_str} 10AM...")
    
    all_emails = []
    account_summary = {}
    
    # Collect emails from each account
    for account in accounts:
        print(f"Processing {account}...")
        account_emails = collect_emails_for_account(account, today_str)
        all_emails.extend(account_emails)
        account_summary[account] = len(account_emails)
        print(f"  Found {len(account_emails)} client-facing emails")
    
    # Save snapshot
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_emails, f, indent=2, ensure_ascii=False)
    
    # Print summary
    total_emails = len(all_emails)
    print(f"\n=== EMAIL SNAPSHOT SUMMARY ===")
    print(f"Date: {today_str} 10:00 AM")
    print(f"Total emails collected: {total_emails}")
    print(f"Output file: {output_file}")
    print("\nEmails per account:")
    for account, count in account_summary.items():
        print(f"  {account}: {count} emails")
    
    return total_emails, account_summary

if __name__ == "__main__":
    main()