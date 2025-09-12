#!/usr/bin/env python3
"""Fresh security test without any cached imports."""

import subprocess
import sys
import os

# Run the specific test in a completely fresh Python interpreter
cmd = [
    sys.executable, 
    "-B",  # Don't create .pyc files
    "-c",
    """
import os
from unittest.mock import Mock

# Set up production environment
test_env = {
    'ENVIRONMENT': 'production',
    'GOOGLE_CLOUD_PROJECT': 'netra-prod',
    'K_SERVICE': 'netra-backend-prod',
    'E2E_TESTING': '1',
    'E2E_OAUTH_SIMULATION_KEY': 'test-key-123'
}

# Clear and set environment
for key in list(os.environ.keys()):
    if key.startswith(('E2E_', 'ENVIRONMENT', 'GOOGLE_CLOUD', 'K_SERVICE')):
        del os.environ[key]

for key, value in test_env.items():
    os.environ[key] = value

print(f"Environment set: ENVIRONMENT={os.environ.get('ENVIRONMENT')}")
print(f"Project: {os.environ.get('GOOGLE_CLOUD_PROJECT')}")

# Now import
import sys
sys.path.insert(0, '/Users/anthony/Documents/GitHub/netra-apex')
from netra_backend.app.websocket_core.unified_websocket_auth import extract_e2e_context_from_websocket

# Mock WebSocket
mock_websocket = Mock()
mock_websocket.headers = {'host': 'prod.example.com', 'x-test-type': 'E2E'}

# Test function
context = extract_e2e_context_from_websocket(mock_websocket)

print(f"Context returned: {context is not None}")
if context:
    print(f"Keys in context: {list(context.keys())}")
    print(f"security_mode present: {'security_mode' in context}")
    print(f"is_e2e_testing: {context.get('is_e2e_testing')}")
    if 'security_mode' in context:
        print(" PASS:  NEW VERSION - Security fix is active")
        if context.get('is_e2e_testing'):
            print(" FAIL:  SECURITY FAILURE: E2E bypass allowed in production!")
        else:
            print(" PASS:  SECURITY SUCCESS: E2E bypass blocked in production!")
    else:
        print(" FAIL:  OLD VERSION - Security fix not loaded")
else:
    print(" PASS:  SECURITY SUCCESS: No context returned (E2E blocked)")
"""
]

print("Running fresh security test...")
result = subprocess.run(cmd, capture_output=True, text=True, cwd='/Users/anthony/Documents/GitHub/netra-apex')
print("STDOUT:")
print(result.stdout)
if result.stderr:
    print("STDERR:")  
    print(result.stderr)
print(f"Exit code: {result.returncode}")