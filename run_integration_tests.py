#!/usr/bin/env python
"""Run integration tests with proper environment setup."""

import os
import sys
import subprocess

# Set required environment variables
os.environ.update({
    'TESTING': '1',
    'JWT_SECRET_KEY': 'test-jwt-secret-key-for-testing-only-must-be-32-chars',
    'FERNET_KEY': 'iZAG-Kz661gRuJXEGzxgghUFnFRamgDrjDXZE6HdJkw=',
    'ENVIRONMENT': 'testing',
    'DATABASE_URL': 'postgresql://test:test@localhost:5432/netra_test',
    'REDIS_URL': 'redis://localhost:6379/1',
    'DEV_MODE_DISABLE_CLICKHOUSE': 'true',
    'CLICKHOUSE_ENABLED': 'false',
    'LOG_LEVEL': 'ERROR',
    'TEST_DISABLE_REDIS': 'true'
})

print("Environment configured for integration tests")
print(f"TESTING: {os.environ.get('TESTING')}")
print(f"ENVIRONMENT: {os.environ.get('ENVIRONMENT')}")

# Run pytest on integration tests
try:
    result = subprocess.run([
        sys.executable, '-m', 'pytest', 
        'app/tests/integration/', 
        '-v', '--tb=short', '--maxfail=5'
    ], capture_output=True, text=True, timeout=180)
    
    print("STDOUT:")
    print(result.stdout)
    print("STDERR:")  
    print(result.stderr)
    print(f"Return code: {result.returncode}")
    
except subprocess.TimeoutExpired:
    print("Integration tests timed out after 3 minutes")
except Exception as e:
    print(f"Error running integration tests: {e}")