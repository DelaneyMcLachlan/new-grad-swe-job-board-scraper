"""
Test script to verify .env file is being loaded correctly
"""
import sys
from pathlib import Path

# Add parent directory to path so we can import from root
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

print("=" * 60)
print("Testing .env File Loading")
print("=" * 60)
print()

# Check if values are loaded
email_host = os.getenv("EMAIL_HOST", "")
email_port = os.getenv("EMAIL_PORT", "")
email_user = os.getenv("EMAIL_USER", "")
email_password = os.getenv("EMAIL_PASSWORD", "")
email_to = os.getenv("EMAIL_TO", "")

print("Environment Variables:")
print(f"  EMAIL_HOST: {email_host if email_host else '(not set)'}")
print(f"  EMAIL_PORT: {email_port if email_port else '(not set)'}")
print(f"  EMAIL_USER: {email_user if email_user else '(not set)'}")
print(f"  EMAIL_PASSWORD: {'*' * len(email_password) if email_password else '(not set)'}")
print(f"  EMAIL_TO: {email_to if email_to else '(not set)'}")
print()

# Check if .env file exists
import os.path
env_exists = os.path.exists('.env')
print(f".env file exists: {env_exists}")

if env_exists:
    print("\nReading .env file directly:")
    try:
        with open('.env', 'r') as f:
            lines = f.readlines()
            for line in lines:
                if line.strip() and not line.strip().startswith('#'):
                    # Hide password value
                    if 'PASSWORD' in line:
                        key, _ = line.split('=', 1) if '=' in line else (line, '')
                        print(f"  {key.strip()}=***")
                    else:
                        print(f"  {line.strip()}")
    except Exception as e:
        print(f"  Error reading file: {e}")

print()
print("=" * 60)
print("Status Check:")
print("=" * 60)

all_set = all([email_host, email_port, email_user, email_password, email_to])
if all_set:
    print("[OK] All email variables are set!")
    print("[OK] Your .env file is being loaded correctly")
    print("\nYou can now run: python test_email.py")
else:
    print("[WARNING] Some variables are missing")
    missing = []
    if not email_host: missing.append("EMAIL_HOST")
    if not email_port: missing.append("EMAIL_PORT")
    if not email_user: missing.append("EMAIL_USER")
    if not email_password: missing.append("EMAIL_PASSWORD")
    if not email_to: missing.append("EMAIL_TO")
    print(f"\nMissing: {', '.join(missing)}")
    print("\nMake sure you've filled in all values in your .env file")

