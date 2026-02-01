#!/usr/bin/env python3
"""
ClawdGuard - Log Watcher Sidecar
Monitors Clawdbot logs in real-time for threats
"""

import json
import os
import sys
import time
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import argparse

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.patterns import PatternMatcher, ThreatMatch, ThreatLevel
from core.alert import AlertManager, Alert, send_immediate_alert
from monitors.activity import ActivityMonitor

class LogWatcher:
    def __init__(self, log_dir: str = None, config_path: str = None):
        self.log_dir = Path(log_dir or "/Users/victor/.clawdbot/logs")
        self.config_path = config_path or str(Path(__file__).parent.parent / "config" / "clawdguard.json")
        
        self.config = self.load_config()
        self.pattern_matcher = PatternMatcher()
        self.activity_monitor = ActivityMonitor()
        self.alert_manager = AlertManager(self.config_path)
        
        self.file_positions = {}  # Track read positions
        self.processed_hashes = set()  # Avoid duplicate alerts
        
    def load_config(self) -> dict:
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def is_learning_mode(self) -> bool:
        """Check if we're still in learning mode"""
        mode = self.config.get('mode', 'learning')
        if mode != 'learning':
            return False
        
        learning_until = self.config.get('learning_until')
        if learning_until:
            deadline = datetime.fromisoformat(learning_until.replace('Z', '+00:00'))
            if datetime.now(deadline.tzinfo) > deadline:
                return False
        
        return True
    
    def handle_threat(self, threat: ThreatMatch, context: str = "") -> bool:
        """Handle a detected threat based on mode and severity"""
        # Create unique hash to avoid duplicate alerts
        threat_hash = f"{threat.vuln_id}:{threat.matched_text}"
        if threat_hash in self.processed_hashes:
            return False
        self.processed_hashes.add(threat_hash)
        
        learning = self.is_learning_mode()
        
        # Log the threat
        log_path = Path(__file__).parent.parent / "logs" / "threats.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(log_path, 'a') as f:
            f.write(json.dumps({
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "level": threat.level.value,
                "vuln_id": threat.vuln_id,
                "name": threat.name,
                "matched": threat.matched_text,
                "context": context[:200],
                "learning_mode": learning,
                "action": "logged" if learning else "blocked"
            }) + "\n")
        
        # In learning mode, only alert for critical
        if learning and threat.level != ThreatLevel.CRITICAL:
            print(f"[LEARNING] Would alert: [{threat.level.value}] {threat.name}")
            return False
        
        # Send alert
        alert = Alert(
            level=threat.level.value,
            title=f"🛡️ {threat.name}",
            description=threat.description,
            details=f"Matched: {threat.matched_text}\nContext: {context[:100]}"
        )
        
        self.alert_manager.send_alert(alert)
        
        # Return True if we should block (non-learning + high/critical)
        if not learning and threat.level in [ThreatLevel.CRITICAL, ThreatLevel.HIGH]:
            return True
        
        return False
    
    def scan_exec_log(self, log_line: str) -> List[ThreatMatch]:
        """Scan an exec log line for threats"""
        threats = []
        
        # Try to extract command from log
        # Format varies, common patterns:
        # {"timestamp":"...","command":"...","exit_code":0}
        # [EXEC] command here
        
        try:
            if log_line.strip().startswith('{'):
                data = json.loads(log_line)
                command = data.get('command', '')
            else:
                # Try to extract command after common prefixes
                match = re.search(r'\[EXEC\]\s*(.+)', log_line)
                if match:
                    command = match.group(1)
                else:
                    command = log_line
            
            if command:
                threats = self.pattern_matcher.scan_command(command)
                
                # Record activity for baseline
                self.activity_monitor.record_exec(command)
                
        except json.JSONDecodeError:
            pass
        
        return threats
    
    def watch_file(self, filepath: Path) -> List[ThreatMatch]:
        """Watch a single log file for new content"""
        all_threats = []
        
        if not filepath.exists():
            return all_threats
        
        # Get current position
        current_pos = self.file_positions.get(str(filepath), 0)
        
        try:
            with open(filepath, 'r') as f:
                # Seek to last position
                f.seek(current_pos)
                
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Scan for threats
                    threats = self.scan_exec_log(line)
                    
                    for threat in threats:
                        should_block = self.handle_threat(threat, line)
                        if should_block:
                            all_threats.append(threat)
                
                # Update position
                self.file_positions[str(filepath)] = f.tell()
                
        except Exception as e:
            print(f"Error watching {filepath}: {e}")
        
        return all_threats
    
    def watch_directory(self) -> List[ThreatMatch]:
        """Watch all log files in directory"""
        all_threats = []
        
        if not self.log_dir.exists():
            return all_threats
        
        for log_file in self.log_dir.glob("*.log"):
            threats = self.watch_file(log_file)
            all_threats.extend(threats)
        
        # Also check JSONL session logs
        for jsonl_file in self.log_dir.glob("*.jsonl"):
            threats = self.watch_file(jsonl_file)
            all_threats.extend(threats)
        
        return all_threats
    
    def run_once(self):
        """Run a single scan cycle"""
        threats = self.watch_directory()
        
        # Check rate limits
        warnings = self.activity_monitor.check_rate_limits(self.config)
        for warning in warnings:
            print(f"⚠️ Rate limit warning: {warning}")
            if not self.is_learning_mode():
                send_immediate_alert(
                    level="high",
                    title="Rate Limit Exceeded",
                    description=warning,
                    details="Unusual activity volume detected"
                )
        
        # Save baseline periodically
        self.activity_monitor.save_baseline()
        
        return threats
    
    def run_daemon(self, interval: float = 5.0):
        """Run as a daemon, scanning periodically"""
        print(f"🛡️ ClawdGuard Watcher starting...")
        print(f"   Mode: {'LEARNING' if self.is_learning_mode() else 'ENFORCEMENT'}")
        print(f"   Watching: {self.log_dir}")
        print(f"   Interval: {interval}s")
        print()
        
        try:
            while True:
                threats = self.run_once()
                
                if threats:
                    print(f"[{datetime.utcnow().isoformat()}] Detected {len(threats)} threat(s)")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n🛡️ ClawdGuard Watcher stopped")
            self.activity_monitor.save_baseline()


def main():
    parser = argparse.ArgumentParser(description="ClawdGuard Log Watcher")
    parser.add_argument("--log-dir", default="/Users/victor/.clawdbot/logs", help="Log directory to watch")
    parser.add_argument("--config", help="Config file path")
    parser.add_argument("--interval", type=float, default=5.0, help="Scan interval in seconds")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    
    args = parser.parse_args()
    
    watcher = LogWatcher(log_dir=args.log_dir, config_path=args.config)
    
    if args.once:
        threats = watcher.run_once()
        print(f"Scan complete. Found {len(threats)} actionable threat(s).")
    else:
        watcher.run_daemon(interval=args.interval)


if __name__ == "__main__":
    main()
