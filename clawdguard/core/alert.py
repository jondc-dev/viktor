#!/usr/bin/env python3
"""
ClawdGuard - Alert System
Sends notifications via WhatsApp, email, etc.
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

@dataclass
class Alert:
    level: str
    title: str
    description: str
    details: str
    timestamp: str = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"

class AlertManager:
    def __init__(self, config_path: str = None):
        self.config_path = config_path or str(Path(__file__).parent.parent / "config" / "clawdguard.json")
        self.config = self.load_config()
        self.alert_log_path = Path(__file__).parent.parent / "logs" / "alerts.jsonl"
    
    def load_config(self) -> dict:
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"alerts": {"whatsapp": True}}
    
    def log_alert(self, alert: Alert):
        """Log alert to file"""
        self.alert_log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.alert_log_path, 'a') as f:
            f.write(json.dumps({
                "timestamp": alert.timestamp,
                "level": alert.level,
                "title": alert.title,
                "description": alert.description,
                "details": alert.details
            }) + "\n")
    
    def format_message(self, alert: Alert) -> str:
        """Format alert for messaging"""
        emoji = {
            "critical": "🚨",
            "high": "⚠️",
            "medium": "📋",
            "low": "ℹ️"
        }.get(alert.level, "❓")
        
        return f"""{emoji} **ClawdGuard Alert**

**Level:** {alert.level.upper()}
**{alert.title}**

{alert.description}

Details: {alert.details}

_Time: {alert.timestamp}_"""
    
    def send_whatsapp(self, alert: Alert, target: str = None) -> bool:
        """
        Send alert via WhatsApp through Clawdbot
        This creates a file that Clawdbot can pick up
        """
        target = target or self.config.get('owner_numbers', ['+971543062826'])[0]
        message = self.format_message(alert)
        
        # Write to alert queue for Clawdbot to pick up
        queue_path = Path(__file__).parent.parent / "logs" / "pending_alerts.jsonl"
        queue_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(queue_path, 'a') as f:
            f.write(json.dumps({
                "channel": "whatsapp",
                "target": target,
                "message": message,
                "level": alert.level,
                "timestamp": alert.timestamp
            }) + "\n")
        
        return True
    
    def send_alert(self, alert: Alert) -> bool:
        """Send alert based on config and severity"""
        # Always log
        self.log_alert(alert)
        
        # Check if we're in learning mode
        if self.config.get('mode') == 'learning':
            # In learning mode, only log, don't send alerts for medium/low
            if alert.level in ['low', 'medium']:
                return True
        
        # Get threat level config
        threat_config = self.config.get('threat_levels', {}).get(alert.level, {})
        alert_type = threat_config.get('alert', 'none')
        
        if alert_type == 'immediate':
            # Send immediately via WhatsApp
            return self.send_whatsapp(alert)
        elif alert_type == 'session':
            # Queue for session notification
            return self.send_whatsapp(alert)
        elif alert_type == 'daily':
            # Just log, will be included in daily digest
            return True
        
        return True


def send_immediate_alert(level: str, title: str, description: str, details: str = ""):
    """Convenience function for sending an alert"""
    manager = AlertManager()
    alert = Alert(
        level=level,
        title=title,
        description=description,
        details=details
    )
    return manager.send_alert(alert)


if __name__ == "__main__":
    # Test alert
    send_immediate_alert(
        level="medium",
        title="Test Alert",
        description="This is a test of the ClawdGuard alert system",
        details="No action needed - just testing"
    )
    print("Test alert sent!")
