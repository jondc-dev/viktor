#!/usr/bin/env python3
"""
Keychain Manager - Centralized credential storage for Viktor

This skill manages all login credentials in one secure location,
making it easy to access various services without remembering passwords.

Usage:
    python3 keychain.py list                    # List all stored credentials
    python3 keychain.py get <service>           # Get credentials for a service
    python3 keychain.py set <service> <user>    # Store/update credentials
    python3 keychain.py remove <service>        # Remove credentials
"""

import json
import os
import sys
import getpass
from pathlib import Path
from typing import Dict, Optional

KEYCHAIN_FILE = Path("/Users/victor/clawd/keychain.json")

class KeychainManager:
    def __init__(self):
        self.keychain_file = KEYCHAIN_FILE
        self.credentials = self._load_keychain()
    
    def _load_keychain(self) -> Dict:
        """Load credentials from keychain file."""
        if self.keychain_file.exists():
            try:
                with open(self.keychain_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
    
    def _save_keychain(self):
        """Save credentials to keychain file."""
        try:
            with open(self.keychain_file, 'w') as f:
                json.dump(self.credentials, f, indent=2)
            # Set restrictive permissions
            os.chmod(self.keychain_file, 0o600)
        except IOError as e:
            print(f"Error saving keychain: {e}")
            sys.exit(1)
    
    def list_services(self):
        """List all stored services."""
        if not self.credentials:
            print("No credentials stored in keychain.")
            return
        
        print("Stored services:")
        for service in sorted(self.credentials.keys()):
            username = self.credentials[service].get('username', 'N/A')
            has_password = 'Yes' if 'password' in self.credentials[service] else 'No'
            print(f"  {service}: {username} (password: {has_password})")
    
    def get_credentials(self, service: str) -> Optional[Dict]:
        """Get credentials for a specific service."""
        if service not in self.credentials:
            print(f"No credentials found for '{service}'")
            return None
        
        creds = self.credentials[service].copy()
        if 'password' in creds:
            print(f"Username: {creds['username']}")
            print(f"Password: {creds['password']}")
            print(f"Additional info: {creds.get('notes', 'None')}")
        else:
            print(f"Username: {creds['username']}")
            print("Password not stored (will prompt when needed)")
        
        return creds
    
    def set_credentials(self, service: str, username: str, password: Optional[str] = None):
        """Store or update credentials for a service."""
        if service not in self.credentials:
            self.credentials[service] = {}
        
        self.credentials[service]['username'] = username
        
        if password:
            self.credentials[service]['password'] = password
        
        # Prompt for additional notes
        print(f"Add notes for {service} (press Enter to skip): ", end="")
        notes = input().strip()
        if notes:
            self.credentials[service]['notes'] = notes
        
        self._save_keychain()
        print(f"Credentials for '{service}' updated successfully.")
    
    def remove_credentials(self, service: str):
        """Remove credentials for a service."""
        if service not in self.credentials:
            print(f"No credentials found for '{service}'")
            return
        
        del self.credentials[service]
        self._save_keychain()
        print(f"Credentials for '{service}' removed successfully.")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    keychain = KeychainManager()
    command = sys.argv[1]
    
    if command == "list":
        keychain.list_services()
    
    elif command == "get":
        if len(sys.argv) < 3:
            print("Usage: keychain.py get <service>")
            sys.exit(1)
        keychain.get_credentials(sys.argv[2])
    
    elif command == "set":
        if len(sys.argv) < 4:
            print("Usage: keychain.py set <service> <username> [password]")
            sys.exit(1)
        
        service = sys.argv[2]
        username = sys.argv[3]
        password = sys.argv[4] if len(sys.argv) > 4 else None
        
        if not password:
            password = getpass.getpass(f"Enter password for {username}: ")
        
        keychain.set_credentials(service, username, password)
    
    elif command == "remove":
        if len(sys.argv) < 3:
            print("Usage: keychain.py remove <service>")
            sys.exit(1)
        keychain.remove_credentials(sys.argv[2])
    
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    main()