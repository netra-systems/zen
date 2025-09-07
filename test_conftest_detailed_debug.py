#!/usr/bin/env python3
"""
Test to debug exactly which branch of conftest logic is executing.
"""

import os
import sys

def test_conftest_branch_debug():
    """Test to examine which conftest branch is being taken."""
    print("\n=== Conftest Branch Debug ===")
    
    # Check isolated environment
    from shared.isolated_environment import get_env
    env = get_env()
    
    # Check the exact conditions used in conftest.py
    print("=== Conftest Conditions ===")
    pytest_in_modules = "pytest" in sys.modules
    pytest_has_main = hasattr(sys.modules.get('pytest'), 'main') if pytest_in_modules else False
    sys_has_pytest_running = hasattr(sys, '_pytest_running')
    pytest_current_test = env.get("PYTEST_CURRENT_TEST")
    
    print(f"pytest in sys.modules: {pytest_in_modules}")
    print(f"pytest has main: {pytest_has_main}")
    print(f"sys._pytest_running exists: {sys_has_pytest_running}")
    print(f"PYTEST_CURRENT_TEST: {pytest_current_test}")
    
    # Check the main condition
    main_condition = (pytest_in_modules and pytest_has_main and 
                     (sys_has_pytest_running or bool(pytest_current_test)))
    print(f"Main conftest condition met: {main_condition}")
    
    # Check TEST_ISOLATION
    test_isolation = env.get("TEST_ISOLATION")
    print(f"TEST_ISOLATION: {test_isolation}")
    
    # Check which branch would be taken
    if main_condition:
        if test_isolation == "1":
            print("Would take: TEST_ISOLATION branch")
        else:
            print("Would take: Standard test environment setup branch")
    else:
        print("Would NOT execute pytest configuration setup at all")
    
    # Check some key variables that should be set in each branch
    print("\n=== Current Environment State ===")
    test_vars = [
        'TESTING',
        'ENVIRONMENT', 
        'JWT_SECRET_KEY',
        'SERVICE_SECRET',
        'GOOGLE_OAUTH_CLIENT_ID_TEST',
        'GOOGLE_OAUTH_CLIENT_SECRET_TEST',
        'TEST_ISOLATION'
    ]
    
    for var in test_vars:
        value = env.get(var, "NOT_SET")
        if 'SECRET' in var and value != "NOT_SET" and len(value) > 10:
            value = f"{value[:10]}..."
        print(f"  {var} = {value}")
    
    assert True