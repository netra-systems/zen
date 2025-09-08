#!/usr/bin/env python3
"""
Test to debug conftest loading and environment setup.
"""

import os
import sys

def test_conftest_environment_setup():
    """Test to examine how conftest sets up environment during pytest execution."""
    print("\n=== Conftest Debug Test ===")
    
    # Check if we're using backend conftest
    print(f"Working directory: {os.getcwd()}")
    print(f"Python path: {sys.path[:3]}")
    
    # Check pytest modules
    print(f"pytest in sys.modules: {'pytest' in sys.modules}")
    print(f"PYTEST_CURRENT_TEST: {os.environ.get('PYTEST_CURRENT_TEST', 'NOT_SET')}")
    
    # Check isolated environment
    from shared.isolated_environment import get_env
    env = get_env()
    
    print(f"Isolation enabled: {env.is_isolated()}")
    print(f"Test context: {env._is_test_context()}")
    print(f"Environment name: {env.get_environment_name()}")
    
    # Check OAuth credentials
    oauth_vars = [
        'ENVIRONMENT',
        'TESTING',
        'GOOGLE_OAUTH_CLIENT_ID_TEST',
        'GOOGLE_OAUTH_CLIENT_SECRET_TEST'
    ]
    
    print("\n=== Environment Variables ===")
    for var in oauth_vars:
        value = env.get(var, "NOT_SET")
        if 'SECRET' in var and value != "NOT_SET":
            value = f"{value[:10]}..."
        print(f"  {var} = {value}")
    
    # Check if we're in the netra_backend conftest context
    print(f"\n=== Module detection ===")
    print(f"Backend conftest patterns found:")
    
    # Check if specific backend test environment variables are set
    backend_test_vars = [
        'SERVICE_SECRET',
        'FERNET_KEY',
        'JWT_SECRET_KEY'
    ]
    
    for var in backend_test_vars:
        value = env.get(var, "NOT_SET")
        if value != "NOT_SET":
            if 'SECRET' in var or 'KEY' in var:
                value = f"{value[:10]}..."
            print(f"  {var} = {value}")
    
    assert True