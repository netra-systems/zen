#!/usr/bin/env python3
"""
Test to Reproduce and Verify E2E_OAUTH_SIMULATION_KEY Configuration Fix

This test validates that:
1. Integration tests can run without E2E_OAUTH_SIMULATION_KEY validation errors
2. Test environment has proper OAuth simulation key available
3. Staging validation only occurs when actually running in staging
"""

import os
import sys
import pytest
from unittest.mock import patch
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from shared.isolated_environment import get_env
from tests.e2e.staging_config import get_staging_config, StagingTestConfig


def test_staging_config_validation_skipped_in_test_environment():
    """Test that staging validation is skipped when not in staging environment."""
    
    # Ensure we're in test environment
    env = get_env()
    
    # Set test environment explicitly
    with patch.dict(os.environ, {"ENVIRONMENT": "test", "TEST_ENV": "test"}, clear=False):
        # Create new staging config instance - should not validate
        staging_config = get_staging_config()
        
        # Should not raise exception and should have config loaded
        assert staging_config is not None
        assert hasattr(staging_config, 'urls')
        assert hasattr(staging_config, 'E2E_OAUTH_SIMULATION_KEY')


def test_e2e_oauth_simulation_key_available_in_test_environment():
    """Test that E2E_OAUTH_SIMULATION_KEY is available in test environment."""
    
    # Ensure we're in test environment 
    env = get_env()
    
    with patch.dict(os.environ, {"ENVIRONMENT": "test", "TEST_ENV": "test"}, clear=False):
        # Enable isolation to use test defaults
        env.enable_isolation()
        
        # Should get the key from test defaults
        key = env.get("E2E_OAUTH_SIMULATION_KEY")
        assert key is not None
        assert key == "test-e2e-oauth-bypass-key-for-testing-only-unified-2025"
        
        # Test with StagingTestConfig
        staging_config = StagingTestConfig()
        assert staging_config.E2E_OAUTH_SIMULATION_KEY is not None


def test_staging_validation_occurs_in_staging_environment():
    """Test that staging validation occurs when actually in staging environment."""
    
    env = get_env()
    
    # Mock staging environment 
    with patch.dict(os.environ, {"ENVIRONMENT": "staging"}, clear=False):
        # Without E2E_OAUTH_SIMULATION_KEY, should get validation error
        with patch.dict(os.environ, {"E2E_OAUTH_SIMULATION_KEY": ""}, clear=False):
            env.enable_isolation()
            
            staging_config = StagingTestConfig()
            result = staging_config.validate_configuration()
            
            # Should fail validation without the key
            assert result is False


def test_staging_validation_passes_with_key():
    """Test that staging validation passes when key is provided."""
    
    env = get_env()
    
    # Mock staging environment with key
    staging_key = "staging-e2e-test-key-for-oauth-bypass"
    with patch.dict(os.environ, {
        "ENVIRONMENT": "staging", 
        "E2E_OAUTH_SIMULATION_KEY": staging_key
    }, clear=False):
        env.enable_isolation()
        
        staging_config = StagingTestConfig()
        result = staging_config.validate_configuration()
        
        # Should pass validation with the key
        assert result is True
        assert staging_config.E2E_OAUTH_SIMULATION_KEY == staging_key


def test_integration_tests_can_import_staging_config_without_error():
    """Test that integration tests can import staging config without errors."""
    
    # Simulate integration test environment
    with patch.dict(os.environ, {"ENVIRONMENT": "test"}, clear=False):
        
        # This should not raise any exceptions
        try:
            from tests.e2e.staging_config import staging_config
            from tests.e2e.staging_config import get_staging_config
            
            # Should be able to access config without validation errors
            config = get_staging_config()
            assert config is not None
            
        except ValueError as e:
            if "E2E_OAUTH_SIMULATION_KEY not set" in str(e):
                pytest.fail(f"Integration tests should not fail with OAuth key validation: {e}")
            raise


def test_get_bypass_auth_headers_works_in_test_env():
    """Test that get_bypass_auth_headers works in test environment."""
    
    env = get_env()
    
    with patch.dict(os.environ, {"ENVIRONMENT": "test"}, clear=False):
        env.enable_isolation()
        
        staging_config = StagingTestConfig()
        
        # Should work without raising exception
        headers = staging_config.get_bypass_auth_headers()
        assert "X-E2E-Bypass-Key" in headers
        assert headers["X-E2E-Bypass-Key"] == "test-e2e-oauth-bypass-key-for-testing-only-unified-2025"


if __name__ == "__main__":
    # Fix Windows encoding issues
    if sys.platform == 'win32':
        import codecs
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    
    print("=== E2E OAuth Simulation Key Configuration Fix Test ===")
    
    # Run the tests
    tests = [
        test_staging_config_validation_skipped_in_test_environment,
        test_e2e_oauth_simulation_key_available_in_test_environment, 
        test_staging_validation_occurs_in_staging_environment,
        test_staging_validation_passes_with_key,
        test_integration_tests_can_import_staging_config_without_error,
        test_get_bypass_auth_headers_works_in_test_env
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            print(f"\n> Running {test_func.__name__}...")
            test_func()
            print(f"[PASS] {test_func.__name__}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test_func.__name__} - {e}")
            failed += 1
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total: {len(tests)}")
    
    if failed == 0:
        print("\nAll tests passed! E2E OAuth simulation key fix is working correctly.")
        sys.exit(0)
    else:
        print(f"\n{failed} test(s) failed. Fix required.")
        sys.exit(1)