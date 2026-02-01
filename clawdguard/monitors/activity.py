#!/usr/bin/env python3
"""
ClawdGuard - Activity Monitor
Tracks system activity and builds behavioral baseline
"""

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict
from dataclasses import dataclass, asdict
import hashlib

@dataclass
class ActivityEvent:
    timestamp: str
    event_type: str  # exec, file_read, file_write, network, message
    details: Dict
    hash: str = ""
    
    def __post_init__(self):
        if not self.hash:
            content = f"{self.event_type}:{json.dumps(self.details, sort_keys=True)}"
            self.hash = hashlib.md5(content.encode()).hexdigest()[:12]

class ActivityMonitor:
    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir or Path(__file__).parent.parent / "logs")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.baseline_path = self.data_dir / "baseline.json"
        self.activity_log_path = self.data_dir / "activity.jsonl"
        self.stats_path = self.data_dir / "stats.json"
        
        self.baseline = self.load_baseline()
        self.current_stats = self.load_stats()
    
    def load_baseline(self) -> Dict:
        """Load learned behavioral baseline"""
        if self.baseline_path.exists():
            with open(self.baseline_path, 'r') as f:
                return json.load(f)
        return {
            "created": datetime.utcnow().isoformat(),
            "learning_events": 0,
            "common_commands": {},
            "common_paths": {},
            "hourly_activity": {str(i): 0 for i in range(24)},
            "command_sequences": [],
            "normal_domains": set(),
            "thresholds": {
                "exec_per_minute": {"mean": 0, "std": 0, "max": 30},
                "file_ops_per_minute": {"mean": 0, "std": 0, "max": 20}
            }
        }
    
    def load_stats(self) -> Dict:
        """Load current session stats"""
        return {
            "session_start": datetime.utcnow().isoformat(),
            "exec_count": 0,
            "file_read_count": 0,
            "file_write_count": 0,
            "network_count": 0,
            "minute_buckets": defaultdict(lambda: {"exec": 0, "file": 0, "network": 0})
        }
    
    def save_baseline(self):
        """Save baseline to disk"""
        # Convert sets to lists for JSON
        baseline_copy = self.baseline.copy()
        if isinstance(baseline_copy.get('normal_domains'), set):
            baseline_copy['normal_domains'] = list(baseline_copy['normal_domains'])
        
        with open(self.baseline_path, 'w') as f:
            json.dump(baseline_copy, f, indent=2)
    
    def log_event(self, event: ActivityEvent):
        """Log an activity event"""
        with open(self.activity_log_path, 'a') as f:
            f.write(json.dumps(asdict(event)) + "\n")
        
        # Update stats
        minute_key = datetime.utcnow().strftime("%Y-%m-%d-%H-%M")
        
        if event.event_type == "exec":
            self.current_stats["exec_count"] += 1
            self.current_stats["minute_buckets"][minute_key]["exec"] += 1
            
            # Learn command patterns
            cmd = event.details.get("command", "")
            cmd_base = cmd.split()[0] if cmd else ""
            self.baseline["common_commands"][cmd_base] = self.baseline["common_commands"].get(cmd_base, 0) + 1
            
        elif event.event_type in ["file_read", "file_write"]:
            self.current_stats["file_read_count" if event.event_type == "file_read" else "file_write_count"] += 1
            self.current_stats["minute_buckets"][minute_key]["file"] += 1
            
            # Learn path patterns
            path = event.details.get("path", "")
            dir_path = str(Path(path).parent)
            self.baseline["common_paths"][dir_path] = self.baseline["common_paths"].get(dir_path, 0) + 1
            
        elif event.event_type == "network":
            self.current_stats["network_count"] += 1
            self.current_stats["minute_buckets"][minute_key]["network"] += 1
            
            # Learn domains
            domain = event.details.get("domain", "")
            if domain and isinstance(self.baseline.get('normal_domains'), set):
                self.baseline["normal_domains"].add(domain)
            elif domain:
                if 'normal_domains' not in self.baseline:
                    self.baseline['normal_domains'] = []
                if domain not in self.baseline['normal_domains']:
                    self.baseline['normal_domains'].append(domain)
        
        # Update hourly activity
        hour = str(datetime.utcnow().hour)
        self.baseline["hourly_activity"][hour] = self.baseline["hourly_activity"].get(hour, 0) + 1
        self.baseline["learning_events"] = self.baseline.get("learning_events", 0) + 1
    
    def record_exec(self, command: str, exit_code: int = 0, duration_ms: int = 0):
        """Record a command execution"""
        event = ActivityEvent(
            timestamp=datetime.utcnow().isoformat() + "Z",
            event_type="exec",
            details={
                "command": command,
                "exit_code": exit_code,
                "duration_ms": duration_ms
            }
        )
        self.log_event(event)
        return event
    
    def record_file_access(self, path: str, operation: str):
        """Record file read/write"""
        event = ActivityEvent(
            timestamp=datetime.utcnow().isoformat() + "Z",
            event_type=f"file_{operation}",
            details={"path": path, "operation": operation}
        )
        self.log_event(event)
        return event
    
    def record_network(self, url: str, method: str = "GET"):
        """Record network request"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        
        event = ActivityEvent(
            timestamp=datetime.utcnow().isoformat() + "Z",
            event_type="network",
            details={
                "url": url,
                "domain": parsed.netloc,
                "method": method
            }
        )
        self.log_event(event)
        return event
    
    def check_rate_limits(self, config: Dict) -> List[str]:
        """Check if current activity exceeds rate limits"""
        warnings = []
        minute_key = datetime.utcnow().strftime("%Y-%m-%d-%H-%M")
        current = self.current_stats["minute_buckets"].get(minute_key, {"exec": 0, "file": 0, "network": 0})
        
        limits = config.get("rate_limits", {})
        
        if current["exec"] > limits.get("exec_per_minute", 30):
            warnings.append(f"Exec rate limit exceeded: {current['exec']}/min")
        
        if current["file"] > limits.get("file_writes_per_minute", 20):
            warnings.append(f"File ops rate limit exceeded: {current['file']}/min")
        
        if current["network"] > limits.get("network_requests_per_minute", 50):
            warnings.append(f"Network rate limit exceeded: {current['network']}/min")
        
        return warnings
    
    def is_anomalous(self, event: ActivityEvent) -> Optional[str]:
        """Check if an event is anomalous compared to baseline"""
        if self.baseline.get("learning_events", 0) < 100:
            # Not enough data to detect anomalies
            return None
        
        if event.event_type == "exec":
            cmd_base = event.details.get("command", "").split()[0]
            if cmd_base and cmd_base not in self.baseline.get("common_commands", {}):
                return f"Unusual command: {cmd_base}"
        
        elif event.event_type in ["file_read", "file_write"]:
            path = event.details.get("path", "")
            dir_path = str(Path(path).parent)
            if dir_path not in self.baseline.get("common_paths", {}):
                return f"Unusual path: {dir_path}"
        
        elif event.event_type == "network":
            domain = event.details.get("domain", "")
            normal_domains = self.baseline.get("normal_domains", [])
            if isinstance(normal_domains, set):
                normal_domains = list(normal_domains)
            if domain and domain not in normal_domains:
                return f"New domain: {domain}"
        
        return None
    
    def get_summary(self) -> Dict:
        """Get activity summary"""
        return {
            "session_start": self.current_stats.get("session_start"),
            "total_events": self.baseline.get("learning_events", 0),
            "exec_count": self.current_stats.get("exec_count", 0),
            "file_ops": self.current_stats.get("file_read_count", 0) + self.current_stats.get("file_write_count", 0),
            "network_requests": self.current_stats.get("network_count", 0),
            "top_commands": sorted(
                self.baseline.get("common_commands", {}).items(),
                key=lambda x: x[1],
                reverse=True
            )[:10],
            "top_paths": sorted(
                self.baseline.get("common_paths", {}).items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }


if __name__ == "__main__":
    # Test activity monitor
    monitor = ActivityMonitor()
    
    # Simulate some activity
    monitor.record_exec("ls -la /root/clawd")
    monitor.record_exec("cat /root/clawd/SOUL.md")
    monitor.record_file_access("/root/clawd/memory/2026-02-01.md", "write")
    monitor.record_network("https://api.anthropic.com/v1/messages", "POST")
    
    # Save baseline
    monitor.save_baseline()
    
    # Print summary
    print(json.dumps(monitor.get_summary(), indent=2))
