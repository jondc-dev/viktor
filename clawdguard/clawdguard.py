#!/usr/bin/env python3
"""
🛡️ ClawdGuard - Security Firewall for Clawdbot

Main entry point for the ClawdGuard security system.

Usage:
    python clawdguard.py status        # Show current status
    python clawdguard.py scan          # Run a single scan
    python clawdguard.py watch         # Start daemon mode
    python clawdguard.py config-check  # Check Clawdbot config for vulnerabilities
    python clawdguard.py canary setup  # Set up canary files
    python clawdguard.py canary check  # Check canary files
    python clawdguard.py report        # Generate security report
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Ensure imports work
sys.path.insert(0, str(Path(__file__).parent))

from core.patterns import PatternMatcher
from core.alert import AlertManager, send_immediate_alert
from core.canary import CanarySystem
from monitors.activity import ActivityMonitor
from monitors.watcher import LogWatcher


def cmd_status(args):
    """Show ClawdGuard status"""
    config_path = Path(__file__).parent / "config" / "clawdguard.json"
    
    print("🛡️ ClawdGuard Status")
    print("=" * 50)
    
    # Load config
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        mode = config.get('mode', 'unknown')
        learning_until = config.get('learning_until', 'N/A')
        
        print(f"\n📊 Mode: {mode.upper()}")
        if mode == 'learning':
            print(f"   Learning until: {learning_until}")
        
    except FileNotFoundError:
        print("⚠️ Config not found")
        return
    
    # Activity stats
    monitor = ActivityMonitor()
    summary = monitor.get_summary()
    
    print(f"\n📈 Activity (since {summary.get('session_start', 'unknown')}):")
    print(f"   Total events learned: {summary.get('total_events', 0)}")
    print(f"   Commands this session: {summary.get('exec_count', 0)}")
    print(f"   File operations: {summary.get('file_ops', 0)}")
    print(f"   Network requests: {summary.get('network_requests', 0)}")
    
    # Top commands
    top_cmds = summary.get('top_commands', [])[:5]
    if top_cmds:
        print(f"\n🔧 Top Commands:")
        for cmd, count in top_cmds:
            print(f"   {cmd}: {count}")
    
    # Canary status
    canary = CanarySystem()
    canary_status = canary.get_status()
    
    print(f"\n🍯 Canaries:")
    print(f"   Active: {canary_status.get('total_canaries', 0)}")
    print(f"   Alerts: {canary_status.get('total_alerts', 0)}")
    
    # Vulnerability database
    matcher = PatternMatcher()
    print(f"\n📚 Vulnerability Database:")
    print(f"   Known vulnerabilities: {len(matcher.vulns)}")
    print(f"   Exploit patterns: {len(matcher.exploit_patterns)}")
    
    print()


def cmd_scan(args):
    """Run a single security scan"""
    print("🔍 Running security scan...")
    
    watcher = LogWatcher()
    threats = watcher.run_once()
    
    # Also check canaries
    canary = CanarySystem()
    canary_alerts = canary.check_canaries()
    
    # Check config
    matcher = PatternMatcher()
    config_threats = matcher.check_config()
    
    total_issues = len(threats) + len(canary_alerts) + len(config_threats)
    
    if total_issues == 0:
        print("✅ No threats detected")
    else:
        print(f"\n⚠️ Found {total_issues} issue(s):")
        
        for threat in threats:
            print(f"   🔴 [{threat.level.value}] {threat.name}")
        
        for alert in canary_alerts:
            print(f"   🍯 [{alert['severity']}] Canary {alert['type']}: {alert['path']}")
        
        for threat in config_threats:
            print(f"   ⚙️ [{threat.level.value}] {threat.name}")


def cmd_watch(args):
    """Start daemon mode"""
    watcher = LogWatcher()
    watcher.run_daemon(interval=args.interval)


def cmd_config_check(args):
    """Check Clawdbot config for vulnerabilities"""
    print("⚙️ Checking Clawdbot configuration...")
    
    matcher = PatternMatcher()
    threats = matcher.check_config()
    
    if not threats:
        print("✅ Configuration looks secure!")
        
        # Show current secure settings
        try:
            with open("/root/.clawdbot/clawdbot.json", 'r') as f:
                config = json.load(f)
            
            gateway = config.get('gateway', {})
            print(f"\n   bind: {gateway.get('bind', 'not set')}")
            print(f"   auth.mode: {gateway.get('auth', {}).get('mode', 'not set')}")
            print(f"   trustedProxies: {gateway.get('trustedProxies', 'not set')}")
            
        except Exception as e:
            print(f"   (Could not read config: {e})")
    else:
        print(f"\n⚠️ Found {len(threats)} configuration issue(s):\n")
        
        for threat in threats:
            print(f"🔴 [{threat.level.value.upper()}] {threat.name}")
            print(f"   {threat.description}")
            print(f"   Source: {threat.source}")
            print()


def cmd_canary(args):
    """Manage canary files"""
    canary = CanarySystem()
    
    if args.canary_action == "setup":
        canary.setup_default_canaries()
        print("✅ Canary files set up")
        
    elif args.canary_action == "check":
        alerts = canary.check_canaries()
        if alerts:
            print(f"🚨 {len(alerts)} CANARY ALERT(S)!")
            for alert in alerts:
                print(f"   [{alert['severity']}] {alert['type']}: {alert['path']}")
                
                # Send alert
                send_immediate_alert(
                    level=alert['severity'],
                    title="🍯 Canary File Triggered!",
                    description=f"Canary file was {alert['type']}",
                    details=f"Path: {alert['path']}"
                )
        else:
            print("✅ All canaries intact")
            
    elif args.canary_action == "status":
        status = canary.get_status()
        print(json.dumps(status, indent=2))


def cmd_report(args):
    """Generate security report"""
    print("📋 ClawdGuard Security Report")
    print(f"   Generated: {datetime.utcnow().isoformat()}Z")
    print("=" * 50)
    
    # Config check
    print("\n## Configuration Security")
    matcher = PatternMatcher()
    config_threats = matcher.check_config()
    
    if config_threats:
        for t in config_threats:
            print(f"   ❌ {t.name}: {t.description}")
    else:
        print("   ✅ All configuration checks passed")
    
    # Vulnerability database
    print(f"\n## Vulnerability Database")
    print(f"   Tracking {len(matcher.vulns)} known vulnerabilities")
    print(f"   {len(matcher.exploit_patterns)} exploit pattern sets")
    
    # Activity summary
    print("\n## Activity Baseline")
    monitor = ActivityMonitor()
    summary = monitor.get_summary()
    print(f"   Events recorded: {summary.get('total_events', 0)}")
    
    # Canary status
    print("\n## Canary System")
    canary = CanarySystem()
    status = canary.get_status()
    print(f"   Active canaries: {status.get('total_canaries', 0)}")
    print(f"   Historical alerts: {status.get('total_alerts', 0)}")
    
    # Recent threats
    threats_log = Path(__file__).parent / "logs" / "threats.jsonl"
    if threats_log.exists():
        print("\n## Recent Threats")
        with open(threats_log, 'r') as f:
            lines = f.readlines()[-10:]
            for line in lines:
                try:
                    t = json.loads(line)
                    print(f"   [{t['level']}] {t['name']} - {t.get('action', 'unknown')}")
                except:
                    pass
    
    print("\n" + "=" * 50)
    print("Report complete.")


def main():
    parser = argparse.ArgumentParser(
        description="🛡️ ClawdGuard - Security Firewall for Clawdbot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s status           Show current security status
  %(prog)s scan             Run a single security scan
  %(prog)s watch            Start continuous monitoring
  %(prog)s config-check     Check Clawdbot configuration
  %(prog)s canary setup     Set up honeypot canary files
  %(prog)s report           Generate security report
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Status
    subparsers.add_parser("status", help="Show ClawdGuard status")
    
    # Scan
    subparsers.add_parser("scan", help="Run a single security scan")
    
    # Watch
    watch_parser = subparsers.add_parser("watch", help="Start daemon mode")
    watch_parser.add_argument("--interval", type=float, default=5.0, help="Scan interval in seconds")
    
    # Config check
    subparsers.add_parser("config-check", help="Check Clawdbot config")
    
    # Canary
    canary_parser = subparsers.add_parser("canary", help="Manage canary files")
    canary_parser.add_argument("canary_action", choices=["setup", "check", "status"])
    
    # Report
    subparsers.add_parser("report", help="Generate security report")
    
    args = parser.parse_args()
    
    if args.command == "status":
        cmd_status(args)
    elif args.command == "scan":
        cmd_scan(args)
    elif args.command == "watch":
        cmd_watch(args)
    elif args.command == "config-check":
        cmd_config_check(args)
    elif args.command == "canary":
        cmd_canary(args)
    elif args.command == "report":
        cmd_report(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
