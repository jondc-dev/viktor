#!/usr/bin/env python3
"""
ClawdGuard - Canary System
Honeypot files that trigger alerts when accessed
"""

import json
import os
import stat
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import hashlib

class CanarySystem:
    def __init__(self, config_path: str = None):
        self.config_path = config_path or str(Path(__file__).parent.parent / "config" / "clawdguard.json")
        self.config = self.load_config()
        self.state_path = Path(__file__).parent.parent / "logs" / "canary_state.json"
        self.state = self.load_state()
    
    def load_config(self) -> dict:
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"canary_files": []}
    
    def load_state(self) -> dict:
        if self.state_path.exists():
            with open(self.state_path, 'r') as f:
                return json.load(f)
        return {"canaries": {}, "alerts": []}
    
    def save_state(self):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def create_canary(self, path: str, content: str = None) -> bool:
        """Create a canary file"""
        canary_path = Path(path).expanduser()
        
        # Create parent directories
        canary_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate fake but realistic content
        if content is None:
            content = self.generate_fake_content(canary_path.name)
        
        # Write the file
        with open(canary_path, 'w') as f:
            f.write(content)
        
        # Make it look old (but not suspicious)
        # Set permissions to look sensitive
        os.chmod(canary_path, stat.S_IRUSR | stat.S_IWUSR)  # 600
        
        # Record initial state
        file_stat = canary_path.stat()
        self.state["canaries"][str(canary_path)] = {
            "created": datetime.utcnow().isoformat(),
            "initial_atime": file_stat.st_atime,
            "initial_mtime": file_stat.st_mtime,
            "content_hash": hashlib.md5(content.encode()).hexdigest()
        }
        
        self.save_state()
        print(f"🍯 Created canary: {canary_path}")
        return True
    
    def generate_fake_content(self, filename: str) -> str:
        """Generate realistic-looking fake content"""
        if "api" in filename.lower() or "key" in filename.lower():
            return """# API Keys - DO NOT SHARE
# Last updated: 2026-01-15

ANTHROPIC_API_KEY=sk-ant-fake-key-do-not-use-1234567890abcdef
OPENAI_API_KEY=sk-fake-openai-key-1234567890abcdefghij
AWS_ACCESS_KEY_ID=AKIAFAKEACCESSKEYID12
AWS_SECRET_ACCESS_KEY=FaKeSecRetAccEssKey1234567890abcdefghij

# Production keys - HANDLE WITH CARE
STRIPE_SECRET_KEY=sk_live_fake_stripe_key_1234567890
DATABASE_URL=postgresql://admin:SuperSecret123@prod-db.example.com:5432/maindb
"""
        
        elif "password" in filename.lower():
            return """# Password Vault - ENCRYPTED
# Decryption key stored separately

admin_portal: Tr0ub4dor&3_Fake!
database_root: CorrectHorseBatteryStaple_NotReal
aws_console: MyS3cur3P@ssw0rd_Fake
email_master: EmailP@ss2026_NotReal
backup_encryption: Backup_Encryption_Key_2026_Fake

# Recovery codes
recovery_1: FAKE-1234-ABCD-5678
recovery_2: FAKE-9012-EFGH-3456
"""
        
        else:
            return """# Sensitive Configuration
# This file contains mock sensitive data for security monitoring

SECRET_TOKEN=mock_secret_token_for_canary_detection
PRIVATE_KEY=-----BEGIN FAKE PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC7fake
-----END FAKE PRIVATE KEY-----

# If you see this in logs, an unauthorized access attempt was detected
"""
    
    def check_canaries(self) -> List[Dict]:
        """Check if any canary files have been accessed"""
        alerts = []
        
        for path_str, initial_state in self.state.get("canaries", {}).items():
            canary_path = Path(path_str)
            
            if not canary_path.exists():
                # Canary was deleted!
                alerts.append({
                    "type": "deleted",
                    "path": path_str,
                    "timestamp": datetime.utcnow().isoformat(),
                    "severity": "critical"
                })
                continue
            
            try:
                current_stat = canary_path.stat()
                
                # Check if accessed
                if current_stat.st_atime > initial_state["initial_atime"]:
                    alerts.append({
                        "type": "accessed",
                        "path": path_str,
                        "timestamp": datetime.utcnow().isoformat(),
                        "last_access": datetime.fromtimestamp(current_stat.st_atime).isoformat(),
                        "severity": "critical"
                    })
                
                # Check if modified
                if current_stat.st_mtime > initial_state["initial_mtime"]:
                    alerts.append({
                        "type": "modified",
                        "path": path_str,
                        "timestamp": datetime.utcnow().isoformat(),
                        "severity": "critical"
                    })
                    
            except Exception as e:
                alerts.append({
                    "type": "error",
                    "path": path_str,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                    "severity": "high"
                })
        
        # Record alerts
        if alerts:
            self.state["alerts"].extend(alerts)
            self.save_state()
        
        return alerts
    
    def setup_default_canaries(self):
        """Set up canaries from config"""
        canary_paths = self.config.get("canary_files", [
            "/root/.secrets/api_keys.txt",
            "/root/.secrets/passwords.txt",
            "/root/.aws/credentials_backup"
        ])
        
        for path in canary_paths:
            expanded = str(Path(path).expanduser())
            if expanded not in self.state.get("canaries", {}):
                self.create_canary(path)
    
    def get_status(self) -> Dict:
        """Get canary system status"""
        return {
            "total_canaries": len(self.state.get("canaries", {})),
            "canary_paths": list(self.state.get("canaries", {}).keys()),
            "total_alerts": len(self.state.get("alerts", [])),
            "recent_alerts": self.state.get("alerts", [])[-5:]
        }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="ClawdGuard Canary System")
    parser.add_argument("action", choices=["setup", "check", "status", "create"], help="Action to perform")
    parser.add_argument("--path", help="Path for create action")
    
    args = parser.parse_args()
    
    canary = CanarySystem()
    
    if args.action == "setup":
        canary.setup_default_canaries()
        print("✅ Default canaries set up")
        
    elif args.action == "check":
        alerts = canary.check_canaries()
        if alerts:
            print(f"🚨 {len(alerts)} CANARY ALERT(S):")
            for alert in alerts:
                print(f"   [{alert['severity']}] {alert['type']}: {alert['path']}")
        else:
            print("✅ No canary alerts")
            
    elif args.action == "status":
        status = canary.get_status()
        print(json.dumps(status, indent=2))
        
    elif args.action == "create":
        if args.path:
            canary.create_canary(args.path)
        else:
            print("Error: --path required for create")


if __name__ == "__main__":
    main()
