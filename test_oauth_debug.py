#!/usr/bin/env python3
"""
Debug test to examine OAuth configuration during pytest execution.
"""

import os
import sys
import pytest

def test_oauth_config_debug():
    """Test to debug OAuth configuration during pytest execution."""
    print("\n=== OAuth Configuration Debug (Inside pytest) ===")
    print(f"Python executable: {sys.executable}")
    print(f"Working directory: {os.getcwd()}")
    
    # Check environment variables directly
    print("\n=== Direct OS Environment ===")
    oauth_vars = [
        'ENVIRONMENT',
        'TESTING', 
        'GOOGLE_OAUTH_CLIENT_ID_TEST',
        'GOOGLE_OAUTH_CLIENT_SECRET_TEST',
        'PYTEST_CURRENT_TEST'
    ]
    
    for var in oauth_vars:
        value = os.environ.get(var, "NOT_SET")
        if 'SECRET' in var and value != "NOT_SET":
            value = f"{value[:10]}..." if len(value) > 10 else value
        print(f"  {var} = {value}")
    
    # Check isolated environment
    print("\n=== Isolated Environment ===")
    try:
        from shared.isolated_environment import get_env
        env = get_env()
        
        print(f"  Isolation enabled: {env.is_isolated()}")
        print(f"  Environment detection: {env.get_environment_name()}")
        print(f"  Test context: {env._is_test_context()}")
        
        for var in oauth_vars:
            value = env.get(var, "NOT_SET")
            if 'SECRET' in var and value != "NOT_SET":
                value = f"{value[:10]}..." if len(value) > 10 else value
            print(f"  {var} = {value}")
        
    except Exception as e:
        print(f"  Error accessing isolated environment: {e}")
    
    # Check central validator
    print("\n=== Central Config Validator ===")
    try:
        from shared.configuration.central_config_validator import get_central_validator
        validator = get_central_validator()
        
        print(f"  Environment: {validator.get_environment()}")
        print(f"  Test context: {validator._is_test_context()}")
        
        try:
            oauth_creds = validator.get_oauth_credentials()
            print(f"  OAuth validation: SUCCESS")
            print(f"  Client ID: {oauth_creds['client_id'][:15]}...")
            print(f"  Client Secret: {oauth_creds['client_secret'][:10]}...")
        except Exception as e:
            print(f"  OAuth validation: FAILED - {e}")
        
    except Exception as e:
        print(f"  Error accessing central validator: {e}")
    
    print("=== End Debug ===")
    
    # Make sure test passes 
    assert True