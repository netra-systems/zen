#!/usr/bin/env python3
"""
Script to run mission critical WebSocket tests with staging fallback enabled.
This addresses Issue #544 by setting proper environment variables.
"""
import os
import subprocess
import sys

def main():
    # Set environment variables for staging fallback
    os.environ["USE_STAGING_FALLBACK"] = "true"
    os.environ["STAGING_WEBSOCKET_URL"] = "wss://netra-staging.onrender.com/ws"
    
    print("Environment variables set:")
    print(f"USE_STAGING_FALLBACK = {os.environ.get('USE_STAGING_FALLBACK')}")
    print(f"STAGING_WEBSOCKET_URL = {os.environ.get('STAGING_WEBSOCKET_URL')}")
    
    # Run the mission critical test suite
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/mission_critical/test_websocket_agent_events_suite.py::TestRealWebSocketComponents::test_websocket_notifier_all_methods",
        "-v", "--tb=short"
    ]
    
    print(f"\nRunning command: {' '.join(cmd)}")
    result = subprocess.run(cmd, env=os.environ)
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())