#!/usr/bin/env python3
"""
Unified Email Client for Viktor @ Saniservice
Handles IMAP reading/searching and SMTP sending with programmatic signature enforcement.

Created: 2026-02-15
Based on Vincent's email_client.py architecture with Viktor-specific configurations.
"""

import imaplib
import smtplib
import email
import os
import sys
import argparse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from bs4 import BeautifulSoup
import quopri
import base64

# Server Configuration
IMAP_SERVER = "mail.saniservice.com"
IMAP_PORT = 993
SMTP_SERVER = "mail.saniservice.com"
SMTP_PORT = 465
DEFAULT_EMAIL_USER = "viktor@saniservice.com"

# Workspace Paths
WORKSPACE_ROOT = Path("/Users/victor/clawd")
SIGNATURE_FILE = WORKSPACE_ROOT / "email_signature.html"
EMAIL_LOG_FILE = WORKSPACE_ROOT / "memory" / "email-send-log.md"

# IMAP connection pool (reused to avoid reconnecting)
_imap_connection = None
_imap_last_activity = None


class EmailClient:
    """Unified email client for IMAP and SMTP operations."""
    
    def __init__(self, email_user: str = None, email_pass: str = None):
        """
        Initialize email client.
        
        Args:
            email_user: Email address (defaults to EMAIL_USER env var or DEFAULT_EMAIL_USER)
            email_pass: Email password (defaults to EMAIL_PASS env var)
        """
        self.email_user = email_user or os.getenv('EMAIL_USER', DEFAULT_EMAIL_USER)
        self.email_pass = email_pass or os.getenv('EMAIL_PASS')
        
        if not self.email_pass:
            raise ValueError("Email password not provided. Set EMAIL_PASS environment variable.")
        
        self.imap = None
        self.smtp = None
    
    def _connect_imap(self) -> imaplib.IMAP4_SSL:
        """Connect to IMAP server with connection reuse."""
        global _imap_connection, _imap_last_activity
        
        # Try to reuse existing connection
        if _imap_connection:
            try:
                # Send NOOP to check if connection is alive
                _imap_connection.noop()
                _imap_last_activity = datetime.now()
                return _imap_connection
            except:
                # Connection dead, create new one
                _imap_connection = None
        
        # Create new connection
        imap = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        imap.login(self.email_user, self.email_pass)
        _imap_connection = imap
        _imap_last_activity = datetime.now()
        return imap
    
    def _connect_smtp(self) -> smtplib.SMTP_SSL:
        """Connect to SMTP server using SSL."""
        smtp = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        smtp.login(self.email_user, self.email_pass)
        return smtp
    
    def list_folders(self) -> List[str]:
        """List all IMAP folders."""
        imap = self._connect_imap()
        status, folders = imap.list()
        
        folder_names = []
        if status == 'OK':
            for folder in folders:
                # Parse folder name from IMAP LIST response
                parts = folder.decode().split('"')
                if len(parts) >= 3:
                    folder_names.append(parts[-2])
        
        return folder_names
    
    def select_folder(self, folder: str = "INBOX") -> Tuple[str, int]:
        """
        Select an IMAP folder.
        
        Args:
            folder: Folder name (default: INBOX)
        
        Returns:
            Tuple of (status, message_count)
        """
        imap = self._connect_imap()
        status, messages = imap.select(folder)
        
        if status == 'OK':
            count = int(messages[0])
            return status, count
        return status, 0
    
    def search_emails(self, criteria: str = "ALL", folder: str = "INBOX") -> List[int]:
        """
        Search emails using IMAP search criteria.
        
        Args:
            criteria: IMAP search criteria (e.g., "ALL", "UNSEEN", "FROM sender@example.com")
            folder: Folder to search in (default: INBOX)
        
        Returns:
            List of email UIDs
        """
        imap = self._connect_imap()
        imap.select(folder)
        
        status, messages = imap.search(None, criteria)
        
        if status == 'OK':
            message_ids = messages[0].split()
            return [int(mid) for mid in message_ids]
        return []
    
    def _decode_payload(self, payload: bytes) -> str:
        """Decode email payload with multiple encoding fallback."""
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'windows-1252']
        
        for encoding in encodings:
            try:
                return payload.decode(encoding)
            except (UnicodeDecodeError, AttributeError):
                continue
        
        # Last resort: decode with errors='ignore'
        return payload.decode('utf-8', errors='ignore')
    
    def _html_to_readable(self, html: str) -> str:
        """Convert HTML to readable plain text, preserving table structure."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Convert tables to pipe-delimited format
        for table in soup.find_all('table'):
            rows = []
            for tr in table.find_all('tr'):
                cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                if cells:
                    rows.append(' | '.join(cells))
            
            if rows:
                table_text = '\n'.join(rows)
                table.replace_with(soup.new_string('\n' + table_text + '\n'))
        
        # Get text with line breaks
        text = soup.get_text(separator='\n')
        
        # Clean up excessive newlines
        lines = [line.strip() for line in text.split('\n')]
        return '\n'.join(line for line in lines if line)
    
    def read_email(self, email_id: int, folder: str = "INBOX") -> Dict:
        """
        Read an email by ID.
        
        Args:
            email_id: Email UID
            folder: Folder containing the email
        
        Returns:
            Dictionary with email details
        """
        imap = self._connect_imap()
        imap.select(folder)
        
        status, msg_data = imap.fetch(str(email_id), '(RFC822)')
        
        if status != 'OK':
            return {"error": "Failed to fetch email"}
        
        # Parse email
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)
        
        # Extract headers
        subject = msg['subject'] or "(No Subject)"
        from_addr = msg['from'] or "(Unknown)"
        to_addr = msg['to'] or ""
        cc_addr = msg.get('cc', '')
        date_str = msg['date'] or ""
        
        # Extract body
        body = ""
        html_body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                # Skip attachments
                if "attachment" in content_disposition:
                    continue
                
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = self._decode_payload(payload)
                
                elif content_type == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        html_body = self._decode_payload(payload)
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                content_type = msg.get_content_type()
                if content_type == "text/html":
                    html_body = self._decode_payload(payload)
                else:
                    body = self._decode_payload(payload)
        
        # Prefer HTML content, convert to readable format
        if html_body:
            body = self._html_to_readable(html_body)
        
        return {
            "id": email_id,
            "subject": subject,
            "from": from_addr,
            "to": to_addr,
            "cc": cc_addr,
            "date": date_str,
            "body": body,
            "html": html_body
        }
    
    def _get_signature(self, is_reply: bool = False) -> str:
        """
        Get email signature based on whether it's a reply.
        This is the ENFORCED signature rule - cannot be bypassed.
        
        Args:
            is_reply: True if replying to existing thread, False for new email
        
        Returns:
            HTML signature string
        """
        if is_reply:
            # Simple sign-off for replies
            return "<p>Best regards,<br>Viktor</p>"
        else:
            # Full HTML signature for new emails
            if SIGNATURE_FILE.exists():
                return SIGNATURE_FILE.read_text()
            else:
                # Fallback if signature file doesn't exist
                return "<p>Best regards,<br>Viktor</p>"
    
    def send_email(self, 
                   to: str, 
                   subject: str, 
                   body: str, 
                   cc: str = None,
                   is_reply: bool = False,
                   in_reply_to: str = None,
                   references: str = None) -> bool:
        """
        Send an email with automatic signature injection.
        
        Args:
            to: Recipient email address(es), comma-separated
            subject: Email subject
            body: Email body (plain text or HTML)
            cc: CC recipients, comma-separated (optional)
            is_reply: True if replying to existing thread (affects signature)
            in_reply_to: Message-ID of email being replied to (optional)
            references: References header for threading (optional)
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f'Viktor <{self.email_user}>'
            msg['To'] = to
            if cc:
                msg['Cc'] = cc
            if in_reply_to:
                msg['In-Reply-To'] = in_reply_to
            if references:
                msg['References'] = references
            
            # Get appropriate signature (ENFORCED - cannot be bypassed)
            signature = self._get_signature(is_reply=is_reply)
            
            # Create plain text version
            plain_body = body.replace('<br>', '\n').replace('</p><p>', '\n\n')
            soup = BeautifulSoup(plain_body, 'html.parser')
            plain_text = soup.get_text()
            
            plain_text += "\n\nBest regards,\nViktor\n"
            plain_text += "\nFront Desk Support Specialist\nSaniservice\n"
            plain_text += "(+971) 04 321 5505\nviktor@saniservice.com\nwww.saniservice.com"
            
            # Create HTML version with signature
            html_body = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
</head>
<body style="font-family: Calibri, Arial, sans-serif; font-size: 11pt; color: #000;">
{body if body.startswith('<') else f'<p>{body.replace(chr(10), "<br>")}</p>'}
<br>
{signature}
</body>
</html>"""
            
            # Attach both versions
            msg.attach(MIMEText(plain_text, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))
            
            # Send via SMTP
            smtp = self._connect_smtp()
            recipients = [addr.strip() for addr in to.split(',')]
            if cc:
                recipients.extend([addr.strip() for addr in cc.split(',')])
            
            smtp.send_message(msg)
            smtp.quit()
            
            # Save to Sent folder via IMAP
            self._save_to_sent(msg)
            
            # Log the sent email
            self._log_sent_email(to, cc, subject, is_reply)
            
            return True
            
        except Exception as e:
            print(f"Error sending email: {e}", file=sys.stderr)
            return False
    
    def _save_to_sent(self, msg: MIMEMultipart):
        """Save sent email to Sent folder via IMAP."""
        try:
            imap = self._connect_imap()
            
            # Try common Sent folder names
            sent_folders = ['Sent', 'INBOX.Sent', '[Gmail]/Sent Mail', 'Sent Items']
            
            for folder in sent_folders:
                try:
                    imap.append(folder, '\\Seen', imaplib.Time2Internaldate(datetime.now()), msg.as_bytes())
                    return
                except:
                    continue
            
            # If no standard folder works, just skip
        except Exception as e:
            # Non-critical error, continue
            print(f"Warning: Could not save to Sent folder: {e}", file=sys.stderr)
    
    def _log_sent_email(self, to: str, cc: Optional[str], subject: str, is_reply: bool):
        """Log sent email to email-send-log.md."""
        try:
            # Ensure log file directory exists
            EMAIL_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            # Create log file with header if it doesn't exist
            if not EMAIL_LOG_FILE.exists():
                header = """# Email Send Log

*Permanent record of every email sent from viktor@saniservice.com.*

---

"""
                EMAIL_LOG_FILE.write_text(header)
            
            # Log entry
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            signature_type = "Reply sign-off" if is_reply else "Full signature"
            
            log_entry = f"""### {timestamp}
| Field | Value |
|-------|-------|
| **To** | {to} |
| **CC** | {cc or 'None'} |
| **Subject** | {subject} |
| **Signature** | {signature_type} |
| **Status** | ✅ Sent |

"""
            
            # Append to log
            with EMAIL_LOG_FILE.open('a') as f:
                f.write(log_entry)
                
        except Exception as e:
            print(f"Warning: Could not log sent email: {e}", file=sys.stderr)
    
    def get_inbox(self, limit: int = 20) -> List[Dict]:
        """
        Get recent emails from inbox.
        
        Args:
            limit: Maximum number of emails to retrieve
        
        Returns:
            List of email summaries
        """
        email_ids = self.search_emails("ALL", "INBOX")
        
        # Get most recent emails
        recent_ids = sorted(email_ids, reverse=True)[:limit]
        
        emails = []
        for email_id in recent_ids:
            try:
                email_data = self.read_email(email_id, "INBOX")
                emails.append({
                    "id": email_id,
                    "subject": email_data.get("subject", ""),
                    "from": email_data.get("from", ""),
                    "date": email_data.get("date", ""),
                })
            except:
                continue
        
        return emails
    
    def get_sent(self, limit: int = 20) -> List[Dict]:
        """
        Get recent sent emails.
        
        Args:
            limit: Maximum number of emails to retrieve
        
        Returns:
            List of email summaries
        """
        # Try common Sent folder names
        sent_folders = ['Sent', 'INBOX.Sent', '[Gmail]/Sent Mail', 'Sent Items']
        
        for folder in sent_folders:
            try:
                email_ids = self.search_emails("ALL", folder)
                
                # Get most recent emails
                recent_ids = sorted(email_ids, reverse=True)[:limit]
                
                emails = []
                for email_id in recent_ids:
                    try:
                        email_data = self.read_email(email_id, folder)
                        emails.append({
                            "id": email_id,
                            "subject": email_data.get("subject", ""),
                            "to": email_data.get("to", ""),
                            "date": email_data.get("date", ""),
                        })
                    except:
                        continue
                
                if emails:
                    return emails
            except:
                continue
        
        return []
    
    def close(self):
        """Close IMAP connection."""
        if self.imap:
            try:
                self.imap.close()
                self.imap.logout()
            except:
                pass


def main():
    """CLI interface for email client."""
    parser = argparse.ArgumentParser(description="Unified Email Client for Viktor")
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # List folders
    subparsers.add_parser('folders', help='List all IMAP folders')
    
    # Inbox
    inbox_parser = subparsers.add_parser('inbox', help='Show inbox')
    inbox_parser.add_argument('--limit', type=int, default=20, help='Number of emails to show')
    
    # Sent
    sent_parser = subparsers.add_parser('sent', help='Show sent emails')
    sent_parser.add_argument('--limit', type=int, default=20, help='Number of emails to show')
    
    # Read
    read_parser = subparsers.add_parser('read', help='Read an email')
    read_parser.add_argument('id', type=int, help='Email ID')
    read_parser.add_argument('--folder', default='INBOX', help='Folder name')
    
    # Search
    search_parser = subparsers.add_parser('search', help='Search emails')
    search_parser.add_argument('criteria', help='IMAP search criteria (e.g., "FROM sender@example.com")')
    search_parser.add_argument('--folder', default='INBOX', help='Folder to search')
    
    # Send
    send_parser = subparsers.add_parser('send', help='Send an email')
    send_parser.add_argument('to', help='Recipient email(s), comma-separated')
    send_parser.add_argument('subject', help='Email subject')
    send_parser.add_argument('body', help='Email body')
    send_parser.add_argument('--cc', help='CC recipients, comma-separated')
    send_parser.add_argument('--reply', action='store_true', help='Mark as reply (uses simple signature)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Initialize client
    try:
        client = EmailClient()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Set EMAIL_PASS environment variable with your email password.", file=sys.stderr)
        sys.exit(1)
    
    try:
        if args.command == 'folders':
            folders = client.list_folders()
            print("Available folders:")
            for folder in folders:
                print(f"  - {folder}")
        
        elif args.command == 'inbox':
            emails = client.get_inbox(limit=args.limit)
            print(f"Inbox ({len(emails)} emails):\n")
            for email in emails:
                print(f"[{email['id']}] {email['subject']}")
                print(f"     From: {email['from']}")
                print(f"     Date: {email['date']}")
                print()
        
        elif args.command == 'sent':
            emails = client.get_sent(limit=args.limit)
            print(f"Sent ({len(emails)} emails):\n")
            for email in emails:
                print(f"[{email['id']}] {email['subject']}")
                print(f"     To: {email['to']}")
                print(f"     Date: {email['date']}")
                print()
        
        elif args.command == 'read':
            email_data = client.read_email(args.id, args.folder)
            if 'error' in email_data:
                print(f"Error: {email_data['error']}", file=sys.stderr)
                sys.exit(1)
            
            print(f"Subject: {email_data['subject']}")
            print(f"From: {email_data['from']}")
            print(f"To: {email_data['to']}")
            if email_data.get('cc'):
                print(f"CC: {email_data['cc']}")
            print(f"Date: {email_data['date']}")
            print("\n" + "="*80 + "\n")
            print(email_data['body'])
        
        elif args.command == 'search':
            email_ids = client.search_emails(args.criteria, args.folder)
            print(f"Found {len(email_ids)} emails matching '{args.criteria}' in {args.folder}")
            for email_id in email_ids[:20]:  # Limit to 20 results
                try:
                    email_data = client.read_email(email_id, args.folder)
                    print(f"\n[{email_id}] {email_data['subject']}")
                    print(f"     From: {email_data['from']}")
                    print(f"     Date: {email_data['date']}")
                except:
                    continue
        
        elif args.command == 'send':
            success = client.send_email(
                to=args.to,
                subject=args.subject,
                body=args.body,
                cc=args.cc,
                is_reply=args.reply
            )
            if success:
                print(f"✅ Email sent to {args.to}")
            else:
                print(f"❌ Failed to send email", file=sys.stderr)
                sys.exit(1)
    
    finally:
        client.close()


if __name__ == "__main__":
    main()
