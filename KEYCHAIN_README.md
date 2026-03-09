# Keychain Manager - Secure Credential Storage

## Overview
The keychain manager provides a centralized, secure way to store and access all login credentials. This eliminates the need to remember passwords or search through different locations.

## Security Features
- Credentials stored in encrypted JSON file
- File permissions set to 600 (owner-only access)
- No passwords displayed in command history
- Local storage only (no cloud sync)

## Usage

### List all stored credentials
```bash
python3 keychain.py list
```

### Store new credentials
```bash
# Interactive (password hidden)
python3 keychain.py set <service_name> <username>

# With password as argument (not recommended)
python3 keychain.py set <service_name> <username> <password>
```

### Retrieve credentials
```bash
python3 keychain.py get <service_name>
```

### Remove credentials
```bash
python3 keychain.py remove <service_name>
```

## Current Services
- **saniservice_email**: Viktor's Saniservice email account
  - Username: viktor@saniservice.com
  - Password: [stored securely]
  - Notes: Main email for frontdesk operations

## Integration with Other Tools
The keychain can be integrated with other scripts. Example:

```python
import subprocess
import sys

# Get credentials from keychain
result = subprocess.run([
    sys.executable, '/Users/victor/clawd/keychain.py', 'get', 'saniservice_email'
], capture_output=True, text=True)

# Parse the output to extract username and password
# [Implementation details in email_helper.py]
```

## Adding New Services
When you get new login credentials:
1. Use `python3 keychain.py set <service> <username>`
2. Enter the password when prompted
3. Add any relevant notes
4. The credentials are now securely stored and easily accessible

## Future Enhancements
- Support for API keys and tokens
- Category grouping (email, social media, work tools)
- Search functionality
- Backup/restore capabilities