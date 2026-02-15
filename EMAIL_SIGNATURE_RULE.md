# ⚠️ EMAIL SIGNATURE RULE — ENFORCED IN CODE

**Created: 15 Feb 2026 — Signature rules programmatically enforced in `scripts/email_client.py`**

## THE RULE (ENFORCED IN CODE)

Signature selection depends on whether it's a new email or a reply.

### Email Signature Rule Matrix

| Scenario | Signature |
|----------|-----------|
| **New email / first email in thread** | Full official Saniservice HTML signature from `email_signature.html` |
| **Reply to existing thread** | Simple sign-off: `Best regards,\nViktor` |

### Summary:
- **New/first email** → Always use full HTML signature
- **Reply in a thread** → Always use simple sign-off: "Best regards,\nViktor"

## CODE ENFORCEMENT

The signature rules are **programmatically enforced** in `scripts/email_client.py`:

The `send_email()` method automatically injects the correct signature based on the `is_reply` parameter.
The agent CANNOT bypass this.

## INTERNAL STAFF
All @saniservice.com and @saniservice.ae email addresses.

## EXTERNAL CONTACTS
Anyone whose email domain is NOT @saniservice.com or @saniservice.ae.
