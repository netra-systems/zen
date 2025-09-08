#!/usr/bin/env python3
"""
Test to debug TEST_COLLECTION_MODE and environment setup.
"""

import os
import sys

def test_collection_mode_debug():
    """Test to examine TEST_COLLECTION_MODE and its impact."""
    print("\n=== Collection Mode Debug ===")
    
    # Check isolated environment
    from shared.isolated_environment import get_env
    env = get_env()
    
    # Check collection mode
    collection_mode = env.get("TEST_COLLECTION_MODE")
    print(f"TEST_COLLECTION_MODE: {collection_mode}")
    
    # Check other collection-related variables
    collection_vars = [
        'TEST_COLLECTION_MODE',
        'PYTEST_CURRENT_TEST',
        'TESTING',
        'ENVIRONMENT'
    ]
    
    print("=== Collection-related variables ===")
    for var in collection_vars:
        value = env.get(var, "NOT_SET")
        print(f"  {var} = {value}")
    
    # Check if we're in collection phase vs execution phase
    pytest_current_test = env.get("PYTEST_CURRENT_TEST", "")
    in_collection = not bool(pytest_current_test) or "call" not in pytest_current_test
    print(f"Likely in collection phase: {in_collection}")
    
    # Check environment variables that should be set in different branches
    expected_vars = [
        'TESTING',
        'ENVIRONMENT', 
        'JWT_SECRET_KEY',
        'SERVICE_SECRET',
        'GOOGLE_OAUTH_CLIENT_ID_TEST',
        'GOOGLE_OAUTH_CLIENT_SECRET_TEST'
    ]
    
    print("\n=== Expected test environment variables ===")
    for var in expected_vars:
        value = env.get(var, "NOT_SET")
        if 'SECRET' in var and value != "NOT_SET" and len(value) > 10:
            value = f"{value[:10]}..."
        print(f"  {var} = {value}")
    
    # Let's try to manually set one of the missing OAuth variables to see if it persists
    print("\n=== Manual OAuth credential test ===")
    env.set("GOOGLE_OAUTH_CLIENT_ID_TEST", "manual-test-client-id-for-debugging", source="manual_debug")
    
    # Check if it was set
    manual_value = env.get("GOOGLE_OAUTH_CLIENT_ID_TEST", "NOT_SET")
    print(f"After manual set: GOOGLE_OAUTH_CLIENT_ID_TEST = {manual_value}")
    
    # Now test the validator
    print("\n=== Manual validator test ===")
    try:
        from shared.configuration.central_config_validator import get_central_validator
        validator = get_central_validator()
        oauth_creds = validator.get_oauth_credentials()
        print(f"OAuth validation: SUCCESS")
        print(f"Client ID: {oauth_creds['client_id'][:15]}...")
    except Exception as e:
        print(f"OAuth validation: FAILED - {e}")
    
    assert True