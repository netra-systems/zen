#!/usr/bin/env python3
"""Debug script to test WebSocket auth security fix directly."""

import os
from unittest.mock import Mock
import sys

# Set up the environment to match test conditions (test environment first)
print("Testing in test environment first...")
test_env_dev = {
    "ENVIRONMENT": "test",
    "GOOGLE_CLOUD_PROJECT": "netra-test", 
    "K_SERVICE": "netra-backend-test",
    "E2E_TESTING": "1",
    "E2E_OAUTH_SIMULATION_KEY": "test-key-123"
}

# Apply environment
for key, value in test_env_dev.items():
    os.environ[key] = value

# Now import and test the function
sys.path.insert(0, '/Users/anthony/Documents/GitHub/netra-apex')

from netra_backend.app.websocket_core.unified_websocket_auth import extract_e2e_context_from_websocket

# Create mock WebSocket
mock_websocket = Mock()
mock_websocket.headers = {
    "host": "prod.example.com",
    "x-test-type": "E2E"
}

print("=== DEBUG WebSocket Auth Security Test ===")
print(f"Environment: {os.environ.get('ENVIRONMENT')}")
print(f"Project: {os.environ.get('GOOGLE_CLOUD_PROJECT')}")
print(f"E2E_TESTING: {os.environ.get('E2E_TESTING')}")
print(f"Headers: {dict(mock_websocket.headers)}")
print()

# Test the function
context = extract_e2e_context_from_websocket(mock_websocket)

print(f"Returned context: {context}")

if context:
    print(f"is_e2e_testing: {context.get('is_e2e_testing')}")
    print(f"security_mode: {context.get('security_mode')}")
    print(f"detection_method: {context.get('detection_method')}")
    print()
    print(" FAIL:  SECURITY FAILURE: Production allowed E2E bypass!")
else:
    print(" PASS:  SECURITY SUCCESS: Production correctly blocked E2E bypass!")