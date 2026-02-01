# 🛡️ ClawdGuard

**Security firewall layer for Clawdbot**

Created: 2026-02-01
Author: Tom (with Jon)
Status: Learning Mode (Week 1)

## Purpose

Protect Clawdbot from:
- Data exfiltration (API keys, credentials, personal data)
- Prompt injection attacks
- Unauthorized command execution
- Known vulnerabilities in OpenClaw/MoltBot ecosystem

## Components

### 1. Activity Monitor (`monitors/activity.py`)
- Tracks all exec commands, file access, network requests
- Builds behavioral baseline during learning mode
- Detects anomalies based on learned patterns

### 2. Vulnerability Database (`database/vulns.json`)
- Known CVEs and exploit patterns
- Fed from Twitter, news, security research
- Pattern matching for real-time detection

### 3. Threat Responder (`core/responder.py`)
- CRITICAL: Auto-block + instant WhatsApp alert
- HIGH: Block + session notification
- MEDIUM: Allow + log + daily digest
- LOW: Log only

### 4. Log Watcher (`monitors/watcher.py`)
- Sidecar process tailing Clawdbot logs
- Real-time pattern matching
- Async to avoid latency impact

### 5. Canary System (`core/canary.py`)
- Fake sensitive files as honeypots
- Any access = immediate alert

## Modes

- **Learning** (current): Observe, log, don't block
- **Enforcement**: Active blocking based on rules
- **Paranoid**: Allowlist only, everything else blocked

## Configuration

See `config/clawdguard.json`

## For Viktor

This system is designed to be shared. Viktor can run the same components
on his instance. Vulnerability database syncs via shared repo.
