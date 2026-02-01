"""
ClawdGuard Alert System
========================
Send security alerts via WhatsApp and email.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

CONFIG_FILE = os.path.expanduser('~/clawd/clawdguard/config/clawdguard.json')
ALERT_LOG = os.path.expanduser('~/clawd/clawdguard/logs/alerts.log')


def load_config() -> Dict:
    """Load ClawdGuard configuration."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {
            'alert_channels': ['whatsapp'],
            'alert_to': '+971543062826',
        }


def log_alert(alert: Dict) -> None:
    """Log alert to file."""
    os.makedirs(os.path.dirname(ALERT_LOG), exist_ok=True)
    with open(ALERT_LOG, 'a') as f:
        f.write(json.dumps(alert) + '\n')


def format_alert(alert: Dict) -> str:
    """Format alert for human readability."""
    severity = alert.get('severity', 'unknown').upper()
    alert_type = alert.get('type', 'unknown')
    message = alert.get('message', 'No details')
    timestamp = alert.get('timestamp', datetime.now().isoformat())
    
    emoji = {
        'CRITICAL': '🚨',
        'HIGH': '⚠️',
        'MEDIUM': '⚡',
        'LOW': 'ℹ️',
    }.get(severity, '❓')
    
    return f"""
{emoji} CLAWDGUARD ALERT {emoji}
━━━━━━━━━━━━━━━━━━━━━
Severity: {severity}
Type: {alert_type}
Time: {timestamp}

{message}

File: {alert.get('file', 'N/A')}
━━━━━━━━━━━━━━━━━━━━━
""".strip()


def send_alert(alert: Dict) -> bool:
    """
    Send alert via configured channels.
    
    Note: This creates a file that Viktor's heartbeat can pick up,
    or can be called directly via clawdbot message tool.
    """
    config = load_config()
    
    # Always log
    log_alert(alert)
    
    # Format message
    message = format_alert(alert)
    
    # Write to alert queue for Viktor to pick up
    queue_file = os.path.expanduser('~/clawd/clawdguard/logs/alert_queue.json')
    
    try:
        try:
            with open(queue_file, 'r') as f:
                queue = json.load(f)
        except Exception:
            queue = []
        
        queue.append({
            'alert': alert,
            'formatted': message,
            'target': config.get('alert_to'),
            'channels': config.get('alert_channels'),
            'created_at': datetime.now().isoformat(),
            'sent': False,
        })
        
        with open(queue_file, 'w') as f:
            json.dump(queue, f, indent=2)
        
        print(f"Alert queued for delivery")
        return True
        
    except Exception as e:
        print(f"Failed to queue alert: {e}")
        return False


def process_alerts(alerts: List[Dict]) -> int:
    """Process multiple alerts, return count sent."""
    count = 0
    for alert in alerts:
        if send_alert(alert):
            count += 1
    return count


if __name__ == '__main__':
    # Test alert
    test_alert = {
        'severity': 'high',
        'type': 'test',
        'message': 'This is a test alert from ClawdGuard',
        'timestamp': datetime.now().isoformat(),
    }
    
    print("Testing ClawdGuard Alert System")
    print("=" * 40)
    print(format_alert(test_alert))
    send_alert(test_alert)
