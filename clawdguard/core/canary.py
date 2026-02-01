"""
ClawdGuard Canary Honeypot System
==================================
Monitors decoy files that should never be accessed.
Any access triggers immediate CRITICAL alert.
"""

import os
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Canary file locations
CANARY_FILES = [
    os.path.expanduser('~/.clawdbot/.admin_backup.key'),
    os.path.expanduser('~/.clawdbot/.api_keys_backup.json'),
    os.path.expanduser('~/.clawdbot/.recovery_codes.txt'),
]

STATE_FILE = os.path.expanduser('~/clawd/clawdguard/logs/canary_state.json')


def get_file_hash(filepath: str) -> Optional[str]:
    """Get SHA256 hash of file contents."""
    try:
        with open(filepath, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception:
        return None


def get_file_mtime(filepath: str) -> Optional[float]:
    """Get file modification time."""
    try:
        return os.path.getmtime(filepath)
    except Exception:
        return None


def initialize_canary_state() -> Dict:
    """Create initial state for all canary files."""
    state = {
        'initialized_at': datetime.now().isoformat(),
        'files': {}
    }
    
    for filepath in CANARY_FILES:
        if os.path.exists(filepath):
            state['files'][filepath] = {
                'hash': get_file_hash(filepath),
                'mtime': get_file_mtime(filepath),
                'baseline_at': datetime.now().isoformat(),
            }
    
    return state


def save_state(state: Dict) -> None:
    """Save canary state to file."""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def load_state() -> Optional[Dict]:
    """Load canary state from file."""
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return None


def check_canaries() -> List[Dict]:
    """
    Check all canary files for tampering.
    
    Returns list of alerts for any files that have changed.
    """
    state = load_state()
    
    if state is None:
        # First run - initialize baseline
        state = initialize_canary_state()
        save_state(state)
        return []
    
    alerts = []
    
    for filepath in CANARY_FILES:
        baseline = state['files'].get(filepath)
        
        if baseline is None:
            # File wasn't tracked before
            if os.path.exists(filepath):
                alerts.append({
                    'severity': 'critical',
                    'type': 'canary_new_file',
                    'file': filepath,
                    'message': f'New canary file detected: {filepath}',
                    'timestamp': datetime.now().isoformat(),
                })
            continue
        
        if not os.path.exists(filepath):
            # Canary file was DELETED - very suspicious!
            alerts.append({
                'severity': 'critical',
                'type': 'canary_deleted',
                'file': filepath,
                'message': f'CANARY FILE DELETED: {filepath}',
                'timestamp': datetime.now().isoformat(),
            })
            continue
        
        current_hash = get_file_hash(filepath)
        current_mtime = get_file_mtime(filepath)
        
        # Check if file was modified
        if current_hash != baseline['hash']:
            alerts.append({
                'severity': 'critical',
                'type': 'canary_modified',
                'file': filepath,
                'message': f'CANARY FILE MODIFIED: {filepath}',
                'old_hash': baseline['hash'],
                'new_hash': current_hash,
                'timestamp': datetime.now().isoformat(),
            })
        
        # Check if mtime changed (could indicate read with some tools)
        elif current_mtime != baseline['mtime']:
            alerts.append({
                'severity': 'high',
                'type': 'canary_accessed',
                'file': filepath,
                'message': f'Canary file may have been accessed: {filepath}',
                'timestamp': datetime.now().isoformat(),
            })
    
    return alerts


def setup_canaries() -> None:
    """Initialize canary system and create baseline."""
    print("🍯 Setting up ClawdGuard Canary System")
    print("=" * 40)
    
    state = initialize_canary_state()
    save_state(state)
    
    print(f"Monitoring {len(CANARY_FILES)} canary files:")
    for filepath in CANARY_FILES:
        exists = "✅" if os.path.exists(filepath) else "❌"
        print(f"  {exists} {filepath}")
    
    print(f"\nState saved to: {STATE_FILE}")
    print("Any access to these files will trigger CRITICAL alerts!")


if __name__ == '__main__':
    setup_canaries()
