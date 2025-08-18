#!/usr/bin/env python
"""Detailed test of environment variable issue."""

import os
import sys

# Load secrets first
sys.path.insert(0, '.')
from dev_launcher.secret_loader import SecretLoader

# Load all secrets
print("Loading secrets via dev_launcher...")
sl = SecretLoader(verbose=False)
sl.load_all_secrets()

# Check what's in environment
print("\nChecking environment variables:")
for key in ['GEMINI_API_KEY', 'JWT_SECRET_KEY', 'FERNET_KEY']:
    value = os.environ.get(key)
    if value:
        print(f"  {key}: Present (starts with {value[:10]}...)")
    else:
        print(f"  {key}: MISSING")

# Now test backend secret manager IN THE SAME PROCESS
print("\nTesting backend SecretManager in same process:")
os.environ['ENVIRONMENT'] = 'development'

from app.core.secret_manager import SecretManager

# Check again before loading
print("\nBefore SecretManager._load_from_environment():")
for key in ['GEMINI_API_KEY', 'JWT_SECRET_KEY', 'FERNET_KEY']:
    value = os.environ.get(key)
    if value:
        print(f"  {key}: Present")
    else:
        print(f"  {key}: MISSING")

sm = SecretManager()
secrets = sm._load_from_environment()

print(f"\nSecretManager._load_from_environment() returned {len(secrets)} secrets")
print("Keys in secrets dict:")
for key in sorted(secrets.keys()):
    print(f"  - {key}")

print("\nChecking specific mappings:")
env_mapping = {
    "gemini-api-key": "GEMINI_API_KEY",
    "jwt-secret-key": "JWT_SECRET_KEY",
    "fernet-key": "FERNET_KEY",
}

for secret_name, env_var in env_mapping.items():
    env_value = os.environ.get(env_var)
    secret_value = secrets.get(secret_name)
    print(f"\n  {secret_name}:")
    print(f"    ENV[{env_var}]: {'Present' if env_value else 'MISSING'}")
    print(f"    secrets[{secret_name}]: {'Present' if secret_value else 'MISSING'}")
    if env_value and not secret_value:
        print(f"    WARNING: ENV var exists but not in secrets dict!")