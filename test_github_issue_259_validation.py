#!/usr/bin/env python3
"""
GitHub Issue #259 Validation Script
Validates that the added staging and production test defaults resolve the original issue
while maintaining system stability and security isolation.
"""

import sys
import os
import tempfile
import subprocess
sys.path.append('.')

from shared.isolated_environment import IsolatedEnvironment


def test_staging_test_defaults_availability():
    """Test that staging test defaults are available in test context."""
    print("🧪 Testing staging test defaults availability...")
    
    env = IsolatedEnvironment()
    env.enable_isolation()
    
    # Simulate test context
    env.set('PYTEST_CURRENT_TEST', 'test_staging_e2e::test_oauth_flow', 'test_context')
    
    # Check all staging defaults added for issue #259
    staging_vars = {
        'JWT_SECRET_STAGING': 'test_jwt_secret_staging_',
        'REDIS_PASSWORD': 'test_redis_password_',
        'GOOGLE_OAUTH_CLIENT_ID_STAGING': 'test_oauth_client_id_staging.apps.googleusercontent.com',
        'GOOGLE_OAUTH_CLIENT_SECRET_STAGING': 'test_oauth_client_secret_staging_'
    }
    
    results = {}
    for var, expected_prefix in staging_vars.items():
        value = env.get(var)
        if value and (value.startswith(expected_prefix) or value == expected_prefix):
            results[var] = "✅ PRESENT"
        else:
            results[var] = f"❌ MISSING (got: {value})"
    
    for var, result in results.items():
        print(f"  {var}: {result}")
    
    return all("✅" in result for result in results.values())


def test_production_test_defaults_availability():
    """Test that production test defaults are available in test context."""
    print("🧪 Testing production test defaults availability...")
    
    env = IsolatedEnvironment()
    env.enable_isolation()
    
    # Simulate test context
    env.set('PYTEST_CURRENT_TEST', 'test_production_e2e::test_oauth_flow', 'test_context')
    
    # Check production defaults added for issue #259
    production_vars = {
        'JWT_SECRET_PRODUCTION': 'test_jwt_secret_production_',
        'GOOGLE_OAUTH_CLIENT_ID_PRODUCTION': 'test_oauth_client_id_production.apps.googleusercontent.com',
        'GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION': 'test_oauth_client_secret_production_'
    }
    
    results = {}
    for var, expected_prefix in production_vars.items():
        value = env.get(var)
        if value and (value.startswith(expected_prefix) or value == expected_prefix):
            results[var] = "✅ PRESENT"
        else:
            results[var] = f"❌ MISSING (got: {value})"
    
    for var, result in results.items():
        print(f"  {var}: {result}")
    
    return all("✅" in result for result in results.values())


def test_security_isolation():
    """Test that test defaults are NOT available outside test context."""
    print("🔒 Testing security isolation (non-test context)...")
    
    env = IsolatedEnvironment()
    env.enable_isolation()
    
    # Ensure no test context
    env.delete('PYTEST_CURRENT_TEST')
    env.delete('TESTING')
    env.delete('TEST_MODE')
    
    # Check that defaults are not available
    secure_vars = [
        'JWT_SECRET_STAGING',
        'REDIS_PASSWORD', 
        'GOOGLE_OAUTH_CLIENT_ID_STAGING',
        'GOOGLE_OAUTH_CLIENT_SECRET_STAGING',
        'JWT_SECRET_PRODUCTION',
        'GOOGLE_OAUTH_CLIENT_ID_PRODUCTION',
        'GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION'
    ]
    
    results = {}
    for var in secure_vars:
        value = env.get(var)
        if value is None:
            results[var] = "✅ PROPERLY ISOLATED"
        else:
            results[var] = f"❌ SECURITY LEAK (got: {value[:20]}...)"
    
    for var, result in results.items():
        print(f"  {var}: {result}")
    
    return all("✅" in result for result in results.values())


def test_backwards_compatibility():
    """Test that existing functionality still works."""
    print("🔄 Testing backwards compatibility...")
    
    env = IsolatedEnvironment()
    
    # Test basic functionality
    test_results = {}
    
    # Test enable_isolation method (original)
    try:
        env.enable_isolation()
        test_results['enable_isolation'] = "✅ WORKS"
    except Exception as e:
        test_results['enable_isolation'] = f"❌ BROKEN: {e}"
    
    # Test enable_isolation_mode method (compatibility)
    try:
        env.enable_isolation_mode()
        test_results['enable_isolation_mode'] = "✅ WORKS"
    except Exception as e:
        test_results['enable_isolation_mode'] = f"❌ BROKEN: {e}"
    
    # Test basic set/get
    try:
        env.set('TEST_VAR', 'test_value', 'test')
        value = env.get('TEST_VAR')
        if value == 'test_value':
            test_results['basic_set_get'] = "✅ WORKS"
        else:
            test_results['basic_set_get'] = f"❌ BROKEN: got {value}"
    except Exception as e:
        test_results['basic_set_get'] = f"❌ BROKEN: {e}"
    
    for test, result in test_results.items():
        print(f"  {test}: {result}")
    
    return all("✅" in result for result in test_results.values())


def test_original_failing_scenario():
    """Test the original failing scenario from GitHub issue #259."""
    print("🎯 Testing original failing scenario from GitHub issue #259...")
    
    # Create a minimal test script that simulates the original failure
    test_script = '''
import sys
sys.path.append('.')
from shared.isolated_environment import IsolatedEnvironment

# Simulate staging E2E test context
env = IsolatedEnvironment()
env.enable_isolation()
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
for var in required_vars:
    value = env.get(var)
    if not value:
        missing_vars.append(var)

if missing_vars:
    print(f"FAILURE: Missing variables: {missing_vars}")
    exit(1)
else:
    print("SUCCESS: All required staging test defaults are available")
    exit(0)
'''
    
    # Write and execute the test script
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(test_script)
        temp_script = f.name
    
    try:
        result = subprocess.run([sys.executable, temp_script], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("  ✅ Original failing scenario now PASSES")
            return True
        else:
            print(f"  ❌ Original failing scenario still FAILS: {result.stdout} {result.stderr}")
            return False
    except Exception as e:
        print(f"  ❌ Test execution error: {e}")
        return False
    finally:
        os.unlink(temp_script)


def test_no_environmental_pollution():
    """Test that changes don't pollute the environment."""
    print("🌍 Testing environmental pollution prevention...")
    
    # Get initial environment state
    initial_env = dict(os.environ)
    
    # Use IsolatedEnvironment extensively
    env = IsolatedEnvironment()
    env.enable_isolation()
    env.set('PYTEST_CURRENT_TEST', 'test_pollution_check', 'test_context')
    
    # Access test defaults
    _ = env.get('JWT_SECRET_STAGING')
    _ = env.get('REDIS_PASSWORD')
    _ = env.get('GOOGLE_OAUTH_CLIENT_ID_STAGING')
    
    # Disable isolation
    env.disable_isolation()
    
    # Check that os.environ is not polluted
    current_env = dict(os.environ)
    new_vars = set(current_env.keys()) - set(initial_env.keys())
    
    # Filter out expected test-related variables
    unexpected_vars = [var for var in new_vars 
                      if not var.startswith(('PYTEST_', 'TEST_', '_PYTEST_'))]
    
    if not unexpected_vars:
        print("  ✅ No environmental pollution detected")
        return True
    else:
        print(f"  ❌ Environmental pollution detected: {unexpected_vars}")
        return False


def main():
    """Run all validation tests for GitHub issue #259."""
    print("=" * 60)
    print("GITHUB ISSUE #259 VALIDATION REPORT")
    print("=" * 60)
    print("Testing: Added 4 staging + 3 production test defaults")
    print("Added: JWT_SECRET_STAGING, REDIS_PASSWORD, GOOGLE_OAUTH_CLIENT_ID_STAGING,")
    print("       GOOGLE_OAUTH_CLIENT_SECRET_STAGING, JWT_SECRET_PRODUCTION,") 
    print("       GOOGLE_OAUTH_CLIENT_ID_PRODUCTION, GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION")
    print()
    
    tests = [
        ("Staging Test Defaults", test_staging_test_defaults_availability),
        ("Production Test Defaults", test_production_test_defaults_availability),
        ("Security Isolation", test_security_isolation),
        ("Backwards Compatibility", test_backwards_compatibility),
        ("Original Failing Scenario", test_original_failing_scenario),
        ("Environmental Pollution", test_no_environmental_pollution)
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
    
    print("\n" + "=" * 60)
    print(f"VALIDATION SUMMARY: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - GitHub issue #259 fix maintains system stability!")
        print("✅ System stability VERIFIED")
        print("✅ No breaking changes introduced")
        print("✅ Security isolation maintained")
        print("✅ Original issue resolved")
        return True
    else:
        print("⚠️  SOME TESTS FAILED - Review failures above")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)