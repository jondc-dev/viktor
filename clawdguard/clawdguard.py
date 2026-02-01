#!/usr/bin/env python3
"""
ClawdGuard - Viktor's Security Monitoring System
=================================================
Threat detection, config validation, and honeypot monitoring.

Usage:
    python clawdguard.py status        # Show status
    python clawdguard.py scan          # Run threat scan
    python clawdguard.py config-check  # Check gateway config
    python clawdguard.py canary setup  # Create honeypot files
    python clawdguard.py canary check  # Check if honeypots triggered
    python clawdguard.py watch         # Start daemon mode
"""

import sys
import os
import json
import re
from datetime import datetime
from pathlib import Path

# Add core modules to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.patterns import compile_patterns, check_command, scan_content, CRITICAL_PATTERNS, HIGH_PATTERNS
from core.canary import check_canaries, setup_canaries, CANARY_FILES
from core.alert import send_alert, format_alert, load_config

# Paths
CLAWDBOT_CONFIG = os.path.expanduser('~/.clawdbot/clawdbot.json')
CLAWDGUARD_CONFIG = os.path.expanduser('~/clawd/clawdguard/config/clawdguard.json')
VULNS_DB = os.path.expanduser('~/clawd/clawdguard/database/vulns.json')


def load_vulns_db():
    """Load vulnerability database."""
    try:
        with open(VULNS_DB, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  Could not load vulns.json: {e}")
        return {}


def cmd_status():
    """Show ClawdGuard status."""
    print()
    print("🛡️  CLAWDGUARD STATUS")
    print("=" * 50)
    
    # Load config
    config = load_config()
    mode = config.get('mode', 'unknown')
    learning_until = config.get('learning_until', 'N/A')
    
    print(f"Mode: {mode.upper()}")
    if mode == 'learning':
        print(f"Learning until: {learning_until}")
    print()
    
    # Check components
    print("Components:")
    
    # Patterns
    patterns_ok = os.path.exists(os.path.join(os.path.dirname(__file__), 'core/patterns.py'))
    print(f"  {'✅' if patterns_ok else '❌'} Pattern Scanner")
    
    # Vulns DB
    vulns_ok = os.path.exists(VULNS_DB)
    if vulns_ok:
        vulns = load_vulns_db()
        vuln_count = len(vulns.get('vulnerabilities', []))
        print(f"  ✅ Vulnerability DB ({vuln_count} entries)")
    else:
        print(f"  ❌ Vulnerability DB")
    
    # Canaries
    canary_count = sum(1 for f in CANARY_FILES if os.path.exists(f))
    print(f"  {'✅' if canary_count == len(CANARY_FILES) else '⚠️'} Canary Honeypots ({canary_count}/{len(CANARY_FILES)})")
    
    # Alert system
    alert_ok = os.path.exists(os.path.join(os.path.dirname(__file__), 'core/alert.py'))
    print(f"  {'✅' if alert_ok else '❌'} Alert System")
    
    print()
    
    # Quick canary check
    alerts = check_canaries()
    if alerts:
        print("🚨 CANARY ALERTS DETECTED!")
        for alert in alerts:
            print(f"   {alert['severity'].upper()}: {alert['message']}")
    else:
        print("✅ No canary alerts")
    
    print()
    print(f"Config: {CLAWDGUARD_CONFIG}")
    print(f"Vulns DB: {VULNS_DB}")
    print()


def cmd_scan(target=None):
    """Run threat scan on input or recent activity."""
    print()
    print("🔍 CLAWDGUARD THREAT SCAN")
    print("=" * 50)
    
    if target:
        # Scan provided input
        print(f"Scanning: {target[:50]}{'...' if len(target) > 50 else ''}")
        print()
        
        result = check_command(target)
        if result:
            severity, pattern = result
            print(f"🚨 THREAT DETECTED!")
            print(f"   Severity: {severity.upper()}")
            print(f"   Pattern: {pattern}")
            return 1
        else:
            print("✅ No threats detected")
            return 0
    else:
        # Interactive mode
        print("Enter commands to scan (empty line to exit):")
        print()
        
        threats_found = 0
        while True:
            try:
                cmd = input("scan> ").strip()
                if not cmd:
                    break
                
                result = check_command(cmd)
                if result:
                    severity, pattern = result
                    print(f"  🚨 {severity.upper()}: {pattern}")
                    threats_found += 1
                else:
                    print(f"  ✅ Clean")
            except (EOFError, KeyboardInterrupt):
                break
        
        print()
        print(f"Scan complete. Threats found: {threats_found}")
        return threats_found


def cmd_config_check():
    """Check Clawdbot gateway configuration for security issues."""
    print()
    print("⚙️  CONFIG SECURITY CHECK")
    print("=" * 50)
    
    if not os.path.exists(CLAWDBOT_CONFIG):
        print(f"❌ Config not found: {CLAWDBOT_CONFIG}")
        return 1
    
    try:
        with open(CLAWDBOT_CONFIG, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ Could not parse config: {e}")
        return 1
    
    issues = []
    warnings = []
    
    # Check gateway bind
    gateway = config.get('gateway', {})
    mode = gateway.get('mode', 'local')
    bind = gateway.get('bind')
    
    print(f"Gateway mode: {mode}")
    
    if bind == '0.0.0.0':
        issues.append("CRITICAL: Gateway bound to 0.0.0.0 (exposed to network!)")
    elif bind and bind not in ['loopback', 'localhost', '127.0.0.1']:
        warnings.append(f"Gateway bind: {bind} (verify this is intended)")
    else:
        print("✅ Gateway binding: secure (local)")
    
    # Check auth
    auth = config.get('auth', {})
    auth_mode = auth.get('mode')
    
    if auth_mode == 'none':
        issues.append("HIGH: Auth mode is 'none' - no authentication!")
    elif auth.get('token'):
        print("✅ Auth: token configured")
    
    # Check channel policies
    channels = config.get('channels', {})
    
    for channel_name, channel_config in channels.items():
        dm_policy = channel_config.get('dmPolicy', 'open')
        group_policy = channel_config.get('groupPolicy', 'open')
        
        if dm_policy == 'open':
            warnings.append(f"{channel_name}: DM policy is 'open' (anyone can message)")
        else:
            print(f"✅ {channel_name}: DM policy is '{dm_policy}'")
        
        if group_policy == 'open' and channel_name != 'slack':
            warnings.append(f"{channel_name}: Group policy is 'open'")
    
    print()
    
    # Report
    if issues:
        print("🚨 CRITICAL ISSUES:")
        for issue in issues:
            print(f"   ❌ {issue}")
        print()
    
    if warnings:
        print("⚠️  WARNINGS:")
        for warning in warnings:
            print(f"   ⚠️  {warning}")
        print()
    
    if not issues and not warnings:
        print("✅ All security checks passed!")
    
    return len(issues)


def cmd_canary(action):
    """Manage canary honeypots."""
    if action == 'setup':
        setup_canaries()
    elif action == 'check':
        print()
        print("🍯 CANARY CHECK")
        print("=" * 50)
        
        alerts = check_canaries()
        
        if alerts:
            print(f"🚨 {len(alerts)} ALERT(S) DETECTED!")
            print()
            for alert in alerts:
                print(f"Severity: {alert['severity'].upper()}")
                print(f"Type: {alert['type']}")
                print(f"File: {alert.get('file', 'N/A')}")
                print(f"Message: {alert['message']}")
                print()
                
                # Queue alert for delivery
                send_alert(alert)
            
            return len(alerts)
        else:
            print("✅ All canary files intact")
            print()
            for filepath in CANARY_FILES:
                exists = "✅" if os.path.exists(filepath) else "❌"
                print(f"  {exists} {filepath}")
            return 0
    else:
        print(f"Unknown canary action: {action}")
        print("Usage: clawdguard.py canary [setup|check]")
        return 1


def cmd_watch():
    """Start daemon mode (placeholder)."""
    print()
    print("👁️  CLAWDGUARD WATCH MODE")
    print("=" * 50)
    print("Starting real-time monitoring...")
    print("(Press Ctrl+C to stop)")
    print()
    
    import time
    
    try:
        check_interval = 60  # seconds
        while True:
            # Check canaries
            alerts = check_canaries()
            if alerts:
                for alert in alerts:
                    print(f"🚨 ALERT: {alert['message']}")
                    send_alert(alert)
            
            # Show heartbeat
            now = datetime.now().strftime('%H:%M:%S')
            print(f"[{now}] ✓ Watching... (canaries OK)")
            
            time.sleep(check_interval)
            
    except KeyboardInterrupt:
        print()
        print("Watch mode stopped.")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 0
    
    command = sys.argv[1].lower()
    
    if command == 'status':
        return cmd_status()
    
    elif command == 'scan':
        target = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else None
        return cmd_scan(target)
    
    elif command == 'config-check':
        return cmd_config_check()
    
    elif command == 'canary':
        if len(sys.argv) < 3:
            print("Usage: clawdguard.py canary [setup|check]")
            return 1
        return cmd_canary(sys.argv[2].lower())
    
    elif command == 'watch':
        return cmd_watch()
    
    elif command in ['help', '-h', '--help']:
        print(__doc__)
        return 0
    
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        return 1


if __name__ == '__main__':
    sys.exit(main() or 0)
