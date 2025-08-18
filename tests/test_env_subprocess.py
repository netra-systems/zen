#!/usr/bin/env python
"""Test if environment variables are passed to subprocess."""

import os
import subprocess
import sys

# Load secrets first
sys.path.insert(0, '.')
from dev_launcher.secret_loader import SecretLoader

# Load all secrets
sl = SecretLoader(verbose=False)
sl.load_all_secrets()

# Check if GEMINI_API_KEY is in parent process
print(f"Parent process - GEMINI_API_KEY present: {'GEMINI_API_KEY' in os.environ}")
if 'GEMINI_API_KEY' in os.environ:
    print(f"Parent process - GEMINI_API_KEY value starts with: {os.environ['GEMINI_API_KEY'][:10]}...")

# Create a subprocess that checks for the same key
result = subprocess.run(
    [sys.executable, "-c", "import os; print(f'Child process - GEMINI_API_KEY present: {\"GEMINI_API_KEY\" in os.environ}')"],
    capture_output=True,
    text=True,
    env=os.environ.copy()  # Pass environment explicitly
)

print(result.stdout.strip())

# Also test with the actual backend secret manager
print("\nTesting backend secret manager:")
result = subprocess.run(
    [sys.executable, "-c", """
import os
os.environ['ENVIRONMENT'] = 'development'
from app.core.secret_manager import SecretManager
sm = SecretManager()
secrets = sm.load_secrets()
print(f"Backend loaded {len(secrets)} secrets")
print(f"gemini-api-key in secrets: {'gemini-api-key' in secrets}")
"""],
    capture_output=True,
    text=True,
    env=os.environ.copy(),
    cwd="."
)

print(result.stdout.strip())
if result.stderr:
    print("Errors:", result.stderr.strip())