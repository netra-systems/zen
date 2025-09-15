#!/usr/bin/env python3
"""
Script to run staging tests with the health check bypass enabled.
This allows us to test against staging even when the health endpoint returns 503.
"""

import os
import subprocess
import sys

# Set environment variables for staging test execution
os.environ['BYPASS_STAGING_HEALTH_CHECK'] = 'true'
os.environ['ENVIRONMENT'] = 'staging'
os.environ['USE_STAGING_SERVICES'] = 'true'
os.environ['E2E_TEST_ENV'] = 'staging'

# Test to run
test_file = sys.argv[1] if len(sys.argv) > 1 else 'tests/e2e/staging/test_1_websocket_events_staging.py'

print(f"Running staging test with bypass: {test_file}")
print(f"Environment variables set:")
print(f"  BYPASS_STAGING_HEALTH_CHECK={os.environ.get('BYPASS_STAGING_HEALTH_CHECK')}")
print(f"  ENVIRONMENT={os.environ.get('ENVIRONMENT')}")
print(f"  USE_STAGING_SERVICES={os.environ.get('USE_STAGING_SERVICES')}")
print(f"  E2E_TEST_ENV={os.environ.get('E2E_TEST_ENV')}")

# Run the test
try:
    result = subprocess.run([
        'python3', '-m', 'pytest', 
        test_file,
        '-v', '--tb=short', '-x'
    ], capture_output=False, text=True)
    sys.exit(result.returncode)
except Exception as e:
    print(f"Error running test: {e}")
    sys.exit(1)