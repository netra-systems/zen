#!/usr/bin/env python3
"""
Script to run WebSocket tests with auth service disabled for testing.
"""
import os
import subprocess
import sys

# Disable auth service for testing
os.environ['AUTH_FAST_TEST_MODE'] = 'true'
os.environ['AUTH_SERVICE_ENABLED'] = 'false'

# Also set correct URLs in case needed
os.environ['AUTH_SERVICE_URL'] = 'http://127.0.0.1:8083'
os.environ['BACKEND_URL'] = 'http://127.0.0.1:8001'

print(f"AUTH_FAST_TEST_MODE set to: {os.environ['AUTH_FAST_TEST_MODE']}")
print(f"AUTH_SERVICE_ENABLED set to: {os.environ['AUTH_SERVICE_ENABLED']}")
print(f"AUTH_SERVICE_URL set to: {os.environ['AUTH_SERVICE_URL']}")
print(f"BACKEND_URL set to: {os.environ['BACKEND_URL']}")

# Run the WebSocket test
cmd = [
    sys.executable, '-m', 'pytest', 
    'tests/unified/websocket/test_basic_connection.py::TestBasicWebSocketConnection::test_successful_websocket_upgrade',
    '-xvs'
]

print(f"Running command: {' '.join(cmd)}")
result = subprocess.run(cmd, cwd=os.getcwd())
sys.exit(result.returncode)