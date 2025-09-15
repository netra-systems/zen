#!/usr/bin/env python3
"""
Phase 1 Windows Fix Test Script - Issue #860

This script tests the WinError 1225 resolution by enabling Windows Docker bypass
and mock WebSocket server functionality.
"""

import os
import sys
import subprocess

# Set environment variables for Windows Docker bypass
os.environ['DOCKER_BYPASS'] = 'true'
os.environ['USE_MOCK_WEBSOCKET'] = 'true'
os.environ['USE_STAGING_FALLBACK'] = 'false'  # Force mock server usage
os.environ['MOCK_WEBSOCKET_URL'] = 'ws://localhost:8001/ws'

print("Phase 1 Windows Fix Test - Issue #860")
print("=====================================")
print("DOCKER_BYPASS=true")
print("USE_MOCK_WEBSOCKET=true")
print("MOCK_WEBSOCKET_URL=ws://localhost:8001/ws")
print()

# Test WebSocket connection establishment
print("Running WebSocket connection test...")
result = subprocess.run([
    sys.executable, '-m', 'pytest',
    'tests/mission_critical/test_websocket_agent_events_suite.py::TestRealWebSocketComponents::test_real_websocket_connection_established',
    '-v', '-s'
], capture_output=False)

print()
print("Test Results:")
if result.returncode == 0:
    print("SUCCESS: WinError 1225 resolved!")
    print("Mock WebSocket server working correctly")
else:
    print(f"FAILED: Test returned exit code {result.returncode}")
    print("Check logs above for details")

sys.exit(result.returncode)