# Browser Tool Reference

## Overview
Headless Playwright-based browser automation. **No OpenClaw plugin needed** — fully autonomous.

- **Script:** `scripts/browser_tool.py`
- **Engine:** Playwright (Chromium headless)
- **Profiles:** `~/.viktor/browser-profiles/`
- **Sessions:** `~/.viktor/browser-sessions.json`

---

## Setup (One-Time)

```bash
scripts/setup_browser.sh
```

This installs `playwright`, `beautifulsoup4`, and the Chromium browser.

---

## Basic Commands

### Navigate to URL
```bash
scripts/browser_tool.py navigate "https://example.com"
```
Returns: Page title + clean text content (HTML stripped)

**Flags:**
- `--raw` — Return raw HTML instead of clean text
- `--json` — Output as JSON

### Google Search
```bash
scripts/browser_tool.py search "Dubai real estate trends"
```
Returns: Top 10 search results with titles, URLs, and snippets

### Take Screenshot
```bash
scripts/browser_tool.py screenshot "https://example.com" --output screenshot.png
```
Saves full-page screenshot. If `--output` not specified, auto-generates filename.

### Extract Text Content
```bash
scripts/browser_tool.py extract "https://example.com"
scripts/browser_tool.py extract "https://example.com" --selector "article"
```
Extract text from full page or specific CSS selector.

### Click Element
```bash
scripts/browser_tool.py click "https://example.com" "button.submit"
```
Click an element by CSS selector.

### Fill Form Field
```bash
scripts/browser_tool.py fill "https://example.com" "input#email" "viktor@saniservice.com"
```
Fill a form field by selector.

### Save as PDF
```bash
scripts/browser_tool.py pdf "https://example.com" --output page.pdf
```
Save page as PDF.

### Execute JavaScript
```bash
scripts/browser_tool.py execute "https://example.com" "document.title"
```
Run arbitrary JavaScript and return result.

---

## Session Mode (Persistent Browser)

For sites requiring login (Slack, Google, etc.), use **session mode** with named profiles to persist cookies.

### Start a Session
```bash
scripts/browser_tool.py session start --profile slack
```
Returns: Session ID (e.g., `session_20260218_142530`)

**Profile names:** Any name works. Common: `slack`, `google`, `default`

### Navigate in Session
```bash
scripts/browser_tool.py session navigate session_20260218_142530 "https://saniservice.slack.com"
```
Navigate within an existing session. Login state persists across commands.

### Click in Session
```bash
scripts/browser_tool.py session click session_20260218_142530 "button.message-send"
```

### Fill in Session
```bash
scripts/browser_tool.py session fill session_20260218_142530 "textarea.message" "Hello team"
```

### Screenshot Session
```bash
scripts/browser_tool.py session screenshot session_20260218_142530 --output slack.png
```

### List Active Sessions
```bash
scripts/browser_tool.py session list
```

### Stop Session
```bash
scripts/browser_tool.py session stop session_20260218_142530
```

---

## Common Workflows

### 1. Research Workflow (Search + Extract)
```bash
# Search for topic
scripts/browser_tool.py search "indoor air quality Dubai" --json

# Extract content from top result
scripts/browser_tool.py extract "https://example.com/article" --selector "article"
```

### 2. Slack Access (Session-Based)
```bash
# First time: Start session and log in manually (use --headed flag)
scripts/browser_tool.py --headed session start --profile slack
scripts/browser_tool.py --headed session navigate <session_id> "https://saniservice.slack.com"
# Log in manually in the visible browser window, then close

# Later: Reuse session (headless, cookies persist)
scripts/browser_tool.py session start --profile slack
scripts/browser_tool.py session navigate <session_id> "https://saniservice.slack.com/messages/general"
scripts/browser_tool.py session extract <session_id> --selector ".c-message_list"
```

### 3. Form Automation
```bash
# Navigate, fill form, submit
scripts/browser_tool.py navigate "https://example.com/contact"
scripts/browser_tool.py fill "https://example.com/contact" "input#name" "Viktor Milei"
scripts/browser_tool.py fill "https://example.com/contact" "input#email" "viktor@saniservice.com"
scripts/browser_tool.py click "https://example.com/contact" "button[type=submit]"
```

---

## Tips

### Login Walls
For sites requiring login:
1. Use `--headed` flag to see browser
2. Start session with named profile
3. Manually log in once
4. Cookies persist in profile — future headless runs stay logged in

### CAPTCHAs
- Some sites block headless browsers
- Use `--headed` flag to solve CAPTCHAs manually
- Realistic User-Agent helps (already configured)
- Session mode persists "I'm not a robot" status

### CSS Selectors
- Right-click element in browser → Inspect
- Copy selector from DevTools
- Test selector in DevTools Console: `document.querySelector("selector")`

### JSON Output
Always use `--json` when scripting — easier to parse programmatically:
```bash
scripts/browser_tool.py search "query" --json | jq '.results[0].url'
```

---

## Debugging

### See the browser in action
```bash
scripts/browser_tool.py --headed navigate "https://example.com"
```
The browser window will be visible. Useful for debugging selectors or login flows.

### Timeout Errors
- Default navigation timeout: 30 seconds
- Selector timeout: 10 seconds
- If page is slow, it will fail — no way to extend timeout via CLI currently

### "Selector not found" errors
- Verify selector in browser DevTools
- Page might not have finished loading (dynamic content)
- Try extracting full page first to see structure

---

## vs OpenClaw Browser Plugin

| Feature | OpenClaw Plugin | browser_tool.py |
|---------|----------------|-----------------|
| Requires human | ✅ Yes (click button) | ❌ No |
| Connection drops | ✅ Yes (WebSocket) | ❌ No |
| Autonomous | ❌ No | ✅ Yes |
| Session persistence | ❌ No | ✅ Yes (profiles) |
| Headless | ❌ No | ✅ Yes |
| Setup | Browser extension | `scripts/setup_browser.sh` |

**Use browser_tool.py for everything.** OpenClaw is deprecated.
