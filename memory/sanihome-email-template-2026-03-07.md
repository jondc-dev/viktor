# Sanihome AC Opportunities - Email Template & Process

**Date:** 2026-03-07
**Status:** Template finalized and tested

## Email Authentication
- **Email:** viktor@saniservice.com
- **Password:** 7Default3* (stored in keychain as 'saniservice_email')
- **Server:** mail.saniservice.com (SMTP: 465 SSL)
- **Issue resolved:** Script now properly retrieves password from keychain

## Email Template Structure
- Uses official Saniservice HTML template with navy header (#001F3F)
- Single opportunity per email (not bundled)
- Professional formatting with proper tables and sections
- Includes opportunity details, notes, action items
- Green call-to-action button (#4CAF50)

## Opportunity URL Structure
- **Base URL:** `https://mcc.saniservice.com/wp-admin/admin.php?page=frontdesk-opportunities`
- **Individual opportunity:** `&project_id={opportunity_id}`
- **Example:** `https://mcc.saniservice.com/wp-admin/admin.php?page=frontdesk-opportunities&project_id=1`
- **Purpose:** Links directly to specific opportunity (not dashboard)

## Script Details
- **Location:** `/Users/victor/clawd/generate_sanihome_ac_opportunities.py`
- **Schedule:** Mondays only (weekday check: 0 = Monday)
- **Recipients:** JV (WhatsApp + email) + frontdesk@saniservice.com (email)
- **Format:** WhatsApp summary + individual HTML emails

## Process Flow
1. Generate 3 opportunities every Monday
2. Send WhatsApp summary to JV first
3. Send individual HTML emails to JV and frontdesk for each opportunity
4. Save opportunities to JSON file for tracking
5. Follow-up check on Thursday

## Key Fixes Applied
- ✅ Email authentication (keychain integration)
- ✅ Template formatting (official Saniservice style)
- ✅ Individual URLs (project_id parameter)
- ✅ Single opportunity per email (clear focus)

**Next Monday:** Script will run automatically and use this exact template without issues.