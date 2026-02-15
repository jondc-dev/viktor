# Email Client Usage Guide

Unified email client for Viktor @ Saniservice with programmatic signature enforcement.

## Overview

`scripts/email_client.py` is a comprehensive email client that handles:
- IMAP folder browsing and email reading
- Email searching with IMAP criteria
- Email sending with automatic signature injection
- Auto-save to Sent folder
- Auto-logging to `memory/email-send-log.md`
- Connection reuse and keepalive

## Configuration

### Server Settings
```python
IMAP_SERVER = "mail.saniservice.com"
IMAP_PORT = 993
SMTP_SERVER = "mail.saniservice.com"
SMTP_PORT = 465
DEFAULT_EMAIL_USER = "viktor@saniservice.com"
```

### Workspace Paths
```python
WORKSPACE_ROOT = Path("/Users/victor/clawd")
SIGNATURE_FILE = WORKSPACE_ROOT / "email_signature.html"
EMAIL_LOG_FILE = WORKSPACE_ROOT / "memory" / "email-send-log.md"
```

### Credentials
Set the `EMAIL_PASS` environment variable:
```bash
export EMAIL_PASS="your_email_password"
```

Optionally override the email user with `EMAIL_USER`:
```bash
export EMAIL_USER="viktor@saniservice.com"
```

## Signature Rules (Enforced in Code)

The email client **automatically** injects signatures based on email type:

| Email Type | Signature |
|------------|-----------|
| **New email** (`is_reply=False`) | Full HTML signature from `email_signature.html` |
| **Reply** (`is_reply=True`) | Simple sign-off: "Best regards,<br>Viktor" |

**You cannot bypass this.** The signature is injected by the `_get_signature()` method.

See `EMAIL_SIGNATURE_RULE.md` for full details.

## Python API

### Initialize Client
```python
from scripts.email_client import EmailClient

# Uses EMAIL_PASS environment variable
client = EmailClient()

# Or provide credentials directly
client = EmailClient(
    email_user="viktor@saniservice.com",
    email_pass="your_password"
)
```

### List Folders
```python
folders = client.list_folders()
print(folders)
# ['INBOX', 'Sent', 'Drafts', 'Trash', 'Spam']
```

### Get Inbox
```python
emails = client.get_inbox(limit=10)
for email in emails:
    print(f"{email['id']}: {email['subject']} from {email['from']}")
```

### Get Sent Emails
```python
sent = client.get_sent(limit=10)
for email in sent:
    print(f"{email['id']}: {email['subject']} to {email['to']}")
```

### Read an Email
```python
email_data = client.read_email(email_id=123, folder="INBOX")
print(f"Subject: {email_data['subject']}")
print(f"From: {email_data['from']}")
print(f"Body:\n{email_data['body']}")
```

### Search Emails
```python
# Search by sender
email_ids = client.search_emails('FROM "sender@example.com"', folder="INBOX")

# Search by subject
email_ids = client.search_emails('SUBJECT "Meeting"', folder="INBOX")

# Search by date
email_ids = client.search_emails('SINCE 01-Jan-2026', folder="INBOX")

# Unseen emails
email_ids = client.search_emails('UNSEEN', folder="INBOX")

# All emails
email_ids = client.search_emails('ALL', folder="INBOX")
```

### Send New Email (Full Signature)
```python
success = client.send_email(
    to="recipient@example.com",
    subject="Meeting Request",
    body="Hi,\n\nI'd like to schedule a meeting...",
    cc="manager@example.com",  # optional
    is_reply=False  # Default: uses full HTML signature
)

if success:
    print("Email sent successfully")
    # Automatically saved to Sent folder
    # Automatically logged to memory/email-send-log.md
```

### Send Reply (Simple Sign-off)
```python
success = client.send_email(
    to="recipient@example.com",
    subject="Re: Meeting Request",
    body="Thanks for your message...",
    is_reply=True,  # Uses simple "Best regards, Viktor" sign-off
    in_reply_to="<message-id@example.com>",  # optional, for threading
    references="<message-id@example.com>"    # optional, for threading
)
```

### Close Connection
```python
client.close()
```

## CLI Usage

The email client includes a command-line interface for common operations.

### List Folders
```bash
python scripts/email_client.py folders
```

### Show Inbox
```bash
# Show 20 most recent emails (default)
python scripts/email_client.py inbox

# Show 50 most recent emails
python scripts/email_client.py inbox --limit 50
```

### Show Sent Emails
```bash
python scripts/email_client.py sent --limit 20
```

### Read an Email
```bash
# Read email ID 123 from INBOX
python scripts/email_client.py read 123

# Read from a specific folder
python scripts/email_client.py read 456 --folder Sent
```

### Search Emails
```bash
# Search by sender
python scripts/email_client.py search 'FROM "sender@example.com"'

# Search by subject in Sent folder
python scripts/email_client.py search 'SUBJECT "Report"' --folder Sent

# Search for unseen emails
python scripts/email_client.py search 'UNSEEN'
```

### Send Email
```bash
# Send new email (full signature)
python scripts/email_client.py send \
    "recipient@example.com" \
    "Meeting Request" \
    "Hi, I'd like to schedule a meeting..."

# Send with CC
python scripts/email_client.py send \
    "recipient@example.com" \
    "Meeting Request" \
    "Hi, I'd like to schedule a meeting..." \
    --cc "manager@example.com"

# Send reply (simple sign-off)
python scripts/email_client.py send \
    "recipient@example.com" \
    "Re: Meeting Request" \
    "Thanks for your message..." \
    --reply
```

## Email Log

All sent emails are automatically logged to `memory/email-send-log.md` with:
- Timestamp
- Recipients (To, CC)
- Subject
- Signature type (Full or Reply)
- Status

Example log entry:
```markdown
### 2026-02-15 14:30:00
| Field | Value |
|-------|-------|
| **To** | client@example.com |
| **CC** | manager@example.com |
| **Subject** | Project Update |
| **Signature** | Full signature |
| **Status** | ✅ Sent |
```

## Features

### HTML Email Reading
Emails with HTML content are automatically converted to readable plain text:
- Tables are converted to pipe-delimited format
- Formatting is preserved where possible
- Multi-encoding support (UTF-8, Latin-1, ISO-8859-1, Windows-1252)

### Connection Reuse
IMAP connections are reused across operations to improve performance:
- Automatic keepalive with NOOP commands
- Graceful reconnection on timeout

### Auto-Save to Sent Folder
Sent emails are automatically saved to the Sent folder via IMAP, ensuring:
- Consistent sent mail across all devices
- No reliance on SMTP server to handle copying

### Thread Support
When replying to emails, you can preserve threading with:
- `in_reply_to`: Message-ID of the email being replied to
- `references`: Full thread references

## IMAP Search Criteria

Common IMAP search criteria you can use:

- `ALL` - All messages
- `UNSEEN` - Unread messages
- `SEEN` - Read messages
- `FLAGGED` - Flagged/starred messages
- `UNFLAGGED` - Unflagged messages
- `FROM "sender@example.com"` - From specific sender
- `TO "recipient@example.com"` - To specific recipient
- `SUBJECT "keyword"` - Subject contains keyword
- `BODY "text"` - Body contains text
- `SINCE 01-Jan-2026` - Since date
- `BEFORE 01-Jan-2026` - Before date
- `ON 01-Jan-2026` - On specific date

Combine criteria with spaces (implicit AND):
```bash
python scripts/email_client.py search 'FROM "sender@example.com" UNSEEN'
```

## Troubleshooting

### "Email password not provided" Error
Set the `EMAIL_PASS` environment variable:
```bash
export EMAIL_PASS="your_password"
python scripts/email_client.py inbox
```

### Connection Timeout
The client automatically reconnects on timeout. If issues persist:
1. Check your network connection
2. Verify mail server is accessible
3. Confirm credentials are correct

### Sent Folder Not Found
The client tries multiple common Sent folder names:
- `Sent`
- `INBOX.Sent`
- `[Gmail]/Sent Mail`
- `Sent Items`

If your server uses a different name, emails will still send but won't be saved to Sent folder.

### Signature File Not Found
If `email_signature.html` doesn't exist, the client falls back to a simple sign-off for all emails.

Ensure the file exists at: `/Users/victor/clawd/email_signature.html`

## Examples

### Example 1: Send a new email to a client
```python
from scripts.email_client import EmailClient

client = EmailClient()

client.send_email(
    to="client@company.com",
    subject="Indoor Air Quality Assessment Report",
    body="""Hi Sarah,

Please find attached the indoor air quality assessment report for your office building.

The results indicate good air quality overall, with a few recommendations for improvement.

Let me know if you have any questions.""",
    is_reply=False  # Full signature
)

client.close()
```

### Example 2: Reply to an existing email
```python
from scripts.email_client import EmailClient

client = EmailClient()

# Read the original email
original = client.read_email(123, "INBOX")

# Send reply
client.send_email(
    to=original['from'],
    subject=f"Re: {original['subject']}",
    body="Thanks for your email. I'll review and get back to you shortly.",
    is_reply=True,  # Simple sign-off
    in_reply_to=original.get('message_id'),
    references=original.get('references')
)

client.close()
```

### Example 3: Find and reply to all unseen emails from a specific sender
```python
from scripts.email_client import EmailClient

client = EmailClient()

# Search for unseen emails from specific sender
email_ids = client.search_emails('FROM "important@client.com" UNSEEN')

for email_id in email_ids:
    email = client.read_email(email_id, "INBOX")
    
    # Reply to each
    client.send_email(
        to=email['from'],
        subject=f"Re: {email['subject']}",
        body="Thank you for your email. I've received it and will respond shortly.",
        is_reply=True
    )

client.close()
```

## See Also

- `EMAIL_SIGNATURE_RULE.md` - Full signature enforcement rules
- `memory/email-send-log.md` - Log of all sent emails
- `email_signature.html` - HTML signature template
