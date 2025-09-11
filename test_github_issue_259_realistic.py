#!/usr/bin/env python3
"""
GitHub Issue #259 Realistic Validation Script
Tests the actual scenario where the fix was needed - staging E2E tests running
without access to staging.env configuration files.
"""

import sys
import os
import tempfile
import subprocess
from unittest.mock import patch
sys.path.append('.')

from shared.isolated_environment import IsolatedEnvironment


def test_missing_staging_config_scenario():
    """Test the actual scenario from GitHub issue #259 - missing staging config."""
    print("🎯 Testing missing staging config scenario (original issue #259)...")
    
    # Simulate CI/test environment where staging.env is NOT available
    # This is the exact scenario that was failing before the fix
    with patch('pathlib.Path.exists') as mock_exists:
        # Mock that no .env files exist (simulating CI environment)
        mock_exists.return_value = False
        
        env = IsolatedEnvironment()
        # Force re-initialization to bypass already-loaded staging.env
        env._initialized = False
        env.__init__()
        
        env.enable_isolation()
        
        # Simulate staging E2E test context 
        env.set('PYTEST_CURRENT_TEST', 'test_staging_e2e::test_oauth_integration', 'test_context')
        env.set('ENVIRONMENT', 'staging', 'test_context')
        
        # The original issue: these variables were missing causing E2E test failures
        required_vars = [
            'JWT_SECRET_STAGING',
            'REDIS_PASSWORD',
            'GOOGLE_OAUTH_CLIENT_ID_STAGING', 
            'GOOGLE_OAUTH_CLIENT_SECRET_STAGING'
        ]
        
        missing_vars = []
        available_vars = []
        
        for var in required_vars:
            value = env.get(var)
            if not value:
                missing_vars.append(var)
            else:
                available_vars.append(var)
                # Verify it has the test default pattern
                expected_prefixes = {
                    'JWT_SECRET_STAGING': 'test_jwt_secret_staging_',
                    'REDIS_PASSWORD': 'test_redis_password_',
                    'GOOGLE_OAUTH_CLIENT_ID_STAGING': 'test_oauth_client_id_staging',
                    'GOOGLE_OAUTH_CLIENT_SECRET_STAGING': 'test_oauth_client_secret_staging_'
                }
                expected_prefix = expected_prefixes.get(var, '')
                if expected_prefix and not value.startswith(expected_prefix):
                    print(f"  ⚠️  {var} has value but wrong pattern: {value[:30]}...")
        
        print(f"  Available variables: {len(available_vars)}/{len(required_vars)}")
        for var in available_vars:
            print(f"    ✅ {var}")
        
        if missing_vars:
            print(f"  Missing variables: {missing_vars}")
            return False
        else:
            print("  ✅ All required staging test defaults are available")
            return True


def test_production_config_scenario():
    """Test production test defaults work in similar scenario."""
    print("🧪 Testing production config scenario...")
    
    with patch('pathlib.Path.exists') as mock_exists:
        # Mock that no .env files exist
        mock_exists.return_value = False
        
        env = IsolatedEnvironment()
        env._initialized = False
        env.__init__()
        env.enable_isolation()
        
        # Simulate production E2E test context 
        env.set('PYTEST_CURRENT_TEST', 'test_production_e2e::test_oauth_flow', 'test_context')
        env.set('ENVIRONMENT', 'production', 'test_context')
        
        # Check production defaults
        production_vars = [
            'JWT_SECRET_PRODUCTION',
            'GOOGLE_OAUTH_CLIENT_ID_PRODUCTION',
            'GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION'
        ]
        
        available_vars = []
        for var in production_vars:
            value = env.get(var)
            if value:
                available_vars.append(var)
        
        print(f"  Available production variables: {len(available_vars)}/{len(production_vars)}")
        for var in available_vars:
            print(f"    ✅ {var}")
        
        return len(available_vars) == len(production_vars)


def test_non_test_context_security():
    """Test that test defaults don't leak outside test context."""
    print("🔒 Testing non-test context security...")
    
    with patch('pathlib.Path.exists') as mock_exists:
        # Mock that no .env files exist
        mock_exists.return_value = False
        
        env = IsolatedEnvironment()
        env._initialized = False
        env.__init__()
        env.enable_isolation()
        
        # NO test context - simulate normal application startup
        env.delete('PYTEST_CURRENT_TEST')
        env.delete('TESTING')
        env.delete('TEST_MODE')
        
        # Check that staging/production test defaults are NOT available
        secure_vars = [
            'JWT_SECRET_STAGING',
            'REDIS_PASSWORD',
            'GOOGLE_OAUTH_CLIENT_ID_STAGING',
            'GOOGLE_OAUTH_CLIENT_SECRET_STAGING',
            'JWT_SECRET_PRODUCTION',
            'GOOGLE_OAUTH_CLIENT_ID_PRODUCTION',
            'GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION'
        ]
        
        leaked_vars = []
        secure_vars_list = []
        
        for var in secure_vars:
            value = env.get(var)
            if value:
                leaked_vars.append(var)
            else:
                secure_vars_list.append(var)
        
        print(f"  Properly isolated: {len(secure_vars_list)}/{len(secure_vars)}")
        for var in secure_vars_list:
            print(f"    ✅ {var}")
        
        if leaked_vars:
            print(f"  ⚠️  Security leaks: {leaked_vars}")
            return False
        else:
            print("  ✅ All variables properly isolated")
            return True


def test_backwards_compatibility():
    """Test that the fix doesn't break existing functionality."""
    print("🔄 Testing backwards compatibility...")
    
    try:
        env = IsolatedEnvironment()
        
        # Test new compatibility method
        env.enable_isolation_mode()
        
        # Test basic functionality still works
        env.set('TEST_VAR', 'test_value', 'test')
        value = env.get('TEST_VAR')
        
        if value == 'test_value':
            print("  ✅ Basic set/get functionality works")
            print("  ✅ New enable_isolation_mode() method works")
            return True
        else:
            print(f"  ❌ Basic functionality broken: expected 'test_value', got '{value}'")
            return False
            
    except Exception as e:
        print(f"  ❌ Exception in compatibility test: {e}")
        return False


def test_no_regression_in_staging_with_config():
    """Test that when staging.env IS available, it still takes precedence."""
    print("🏗️  Testing no regression when staging.env is available...")
    
    # Normal scenario - staging.env file exists and should be loaded
    env = IsolatedEnvironment()
    env.complete_reset_for_testing()
    env.enable_isolation()
    
    # Simulate test context
    env.set('PYTEST_CURRENT_TEST', 'test_staging_normal', 'test_context')
    env.set('ENVIRONMENT', 'staging', 'test_context')
    
    # Check that JWT_SECRET_STAGING gets the staging.env value
    jwt_staging = env.get('JWT_SECRET_STAGING')
    
    # Should get the staging.env value, not the test default
    expected_staging_value = "7SVLKvh7mJNeF6njiRJMoZpUWLya3NfsvJfRHPc0-cYI7Oh80oXOUHuBNuMjUI4ghNTHFH0H7s9vf3S835ET5A"
    
    if jwt_staging == expected_staging_value:
        print("  ✅ Staging.env value takes precedence over test defaults")
        return True
    elif jwt_staging and jwt_staging.startswith('test_jwt_secret_staging_'):
        print("  ⚠️  Test default returned instead of staging.env value")
        print("      This could indicate a configuration precedence issue")
        return False
    else:
        print(f"  ❌ Unexpected value: {jwt_staging[:50] if jwt_staging else None}...")
        return False


def main():
    """Run realistic validation tests for GitHub issue #259."""
    print("=" * 70)
    print("GITHUB ISSUE #259 REALISTIC VALIDATION REPORT")
    print("=" * 70)
    print("CONTEXT: Staging E2E tests fail when staging.env is not available")
    print("FIX: Added test defaults for staging/production OAuth credentials")
    print("REQUIREMENT: Test defaults only used when config files unavailable")
    print()
    
    tests = [
        ("Missing Staging Config (Original Issue)", test_missing_staging_config_scenario),
        ("Production Config Scenario", test_production_config_scenario),
        ("Non-Test Context Security", test_non_test_context_security),
        ("Backwards Compatibility", test_backwards_compatibility),
        ("No Regression with Staging Config", test_no_regression_in_staging_with_config)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            if test_func():
                passed += 1
                status = "✅ PASS"
            else:
                status = "❌ FAIL"
        except Exception as e:
            status = f"❌ ERROR: {e}"
        
        print(f"  Status: {status}")
    
    print("\n" + "=" * 70)
    print(f"VALIDATION SUMMARY: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - GitHub issue #259 fix is working correctly!")
        print("✅ Original issue resolved (staging E2E tests work without config)")
        print("✅ Security isolation maintained (no test defaults in production)")
        print("✅ No breaking changes introduced")
        print("✅ Backwards compatibility preserved")
        print("✅ Configuration precedence maintained")
        return True
    else:
        print("⚠️  SOME TESTS FAILED - Review failures above")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)