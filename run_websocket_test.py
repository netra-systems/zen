#!/usr/bin/env python3
"""
Script to run WebSocket tests with correct environment variables.
"""
import os
import subprocess
import sys

# Set the correct AUTH_SERVICE_URL
os.environ['AUTH_SERVICE_URL'] = 'http://127.0.0.1:8083'

# Also ensure other environment variables are correct
os.environ['BACKEND_URL'] = 'http://127.0.0.1:8001'

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