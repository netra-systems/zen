#!/usr/bin/env python
"""Test a single integration test directly."""

import os
import sys

# Set environment variables
os.environ.update({
    'TESTING': '1',
    'JWT_SECRET_KEY': 'test-jwt-secret-key-for-testing-only-must-be-32-chars',
    'FERNET_KEY': 'iZAG-Kz661gRuJXEGzxgghUFnFRamgDrjDXZE6HdJkw=',
    'ENVIRONMENT': 'testing',
    'DATABASE_URL': 'postgresql://test:test@localhost:5432/netra_test',
    'REDIS_URL': 'redis://localhost:6379/1',
    'DEV_MODE_DISABLE_CLICKHOUSE': 'true',
    'CLICKHOUSE_ENABLED': 'false',
    'LOG_LEVEL': 'ERROR'
})

print("Environment configured")

# Import and check test file
try:
    import app.tests.integration.test_critical_integration
    print("Integration test module imported successfully")
    
    # Get all test functions
    test_functions = []
    for attr in dir(app.tests.integration.test_critical_integration):
        if attr.startswith('test_'):
            test_functions.append(attr)
    
    print(f"Found {len(test_functions)} test functions:")
    for func in test_functions:
        print(f"  - {func}")
        
except Exception as e:
    print(f"Error importing integration tests: {e}")
    import traceback
    traceback.print_exc()