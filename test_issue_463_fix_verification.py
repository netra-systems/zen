#!/usr/bin/env python3
"""
Verification test for Issue #463 fix
Tests that environment variables are available during test collection
"""

import os
import sys

# Simulate pytest collection by setting PYTEST_CURRENT_TEST
os.environ['PYTEST_CURRENT_TEST'] = 'test_collection_verification'

# Test imports and environment access
try:
    from shared.isolated_environment import get_env

    print("[OK] IsolatedEnvironment import successful")

    env = get_env()

    # Test the three critical variables mentioned in Issue #463
    test_results = {}

    service_secret = env.get('SERVICE_SECRET')
    test_results['SERVICE_SECRET'] = service_secret is not None
    print(f"[OK] SERVICE_SECRET: {'FOUND' if service_secret else 'MISSING'}")

    jwt_secret = env.get('JWT_SECRET_KEY')
    test_results['JWT_SECRET_KEY'] = jwt_secret is not None
    print(f"[OK] JWT_SECRET_KEY: {'FOUND' if jwt_secret else 'MISSING'}")

    auth_service_url = env.get('AUTH_SERVICE_URL')
    test_results['AUTH_SERVICE_URL'] = auth_service_url is not None
    print(f"[OK] AUTH_SERVICE_URL: {'FOUND' if auth_service_url else 'MISSING'}")

    # Check test context detection
    is_test_context = env._is_test_context()
    print(f"[OK] Test context detected: {is_test_context}")

    # Check isolation mode
    is_isolated = env.is_isolated()
    print(f"[OK] Isolation enabled: {is_isolated}")

    # Summary
    all_found = all(test_results.values())
    print(f"\n[{'SUCCESS' if all_found else 'FAILED'}]: All critical environment variables {'found' if all_found else 'not found'}")

    if all_found:
        print("Issue #463 fix appears to be working correctly!")
        sys.exit(0)
    else:
        missing = [k for k, v in test_results.items() if not v]
        print(f"Missing variables: {', '.join(missing)}")
        sys.exit(1)

except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)