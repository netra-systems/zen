#!/usr/bin/env python3
import os
import subprocess

# Set staging environment variables
os.environ['USE_STAGING_SERVICES'] = 'true'
os.environ['STAGING_BASE_URL'] = 'https://api.staging.netrasystems.ai'
os.environ['WEBSOCKET_BASE_URL'] = 'wss://api.staging.netrasystems.ai/ws'
os.environ['ENVIRONMENT'] = 'staging'

# Run all tests in the mission critical suite
try:
    result = subprocess.run([
        'python', '-m', 'pytest',
        'tests/mission_critical/test_websocket_agent_events_suite.py',
        '--tb=short', '-x'
    ], capture_output=True, text=True, timeout=300)

    print('STDOUT:')
    print(result.stdout)
    if result.stderr:
        print('STDERR:')
        print(result.stderr)
    print(f'Return code: {result.returncode}')
except subprocess.TimeoutExpired:
    print('Test timed out after 120 seconds')
except Exception as e:
    print(f'Error running test: {e}')