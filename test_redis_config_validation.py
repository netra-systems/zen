#!/usr/bin/env python3
"""
Test script to validate Redis configuration loading from environment variables.

This script tests the Redis configuration remediation for Issue #598.
"""

import os
import sys
from unittest.mock import patch

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(__file__))

def test_redis_config_environment_loading():
    """Test that RedisConfig properly loads from environment variables."""
    print("Testing Redis configuration environment variable loading...")

    # Test environment variables
    test_env = {
        'REDIS_HOST': '10.107.0.3',
        'REDIS_PORT': '6379',
        'REDIS_PASSWORD': 'test-password',
        'REDIS_DB': '0',
        'REDIS_SSL': 'false'
    }

    # Patch environment variables
    with patch.dict(os.environ, test_env, clear=False):
        try:
            from netra_backend.app.schemas.config import RedisConfig

            # Create Redis config - should load from environment
            redis_config = RedisConfig()

            # Validate configuration loaded correctly
            print(f"Redis Host: {redis_config.host}")
            print(f"Redis Port: {redis_config.port}")
            print(f"Redis DB: {redis_config.db}")
            print(f"Redis SSL: {redis_config.ssl}")
            print(f"Redis Password Set: {bool(redis_config.password)}")

            # Validate values
            assert redis_config.host == '10.107.0.3', f"Expected host '10.107.0.3', got '{redis_config.host}'"
            assert redis_config.port == 6379, f"Expected port 6379, got {redis_config.port}"
            assert redis_config.password == 'test-password', f"Expected password 'test-password', got '{redis_config.password}'"
            assert redis_config.db == 0, f"Expected db 0, got {redis_config.db}"
            assert redis_config.ssl == False, f"Expected ssl False, got {redis_config.ssl}"

            print("✅ RedisConfig environment variable loading works correctly!")
            return True

        except Exception as e:
            print(f"❌ RedisConfig environment variable loading failed: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_staging_config_redis_loading():
    """Test that StagingConfig properly loads Redis configuration."""
    print("\nTesting StagingConfig Redis configuration loading...")

    # Test environment variables for staging
    test_env = {
        'ENVIRONMENT': 'staging',
        'REDIS_HOST': '10.107.0.3',
        'REDIS_PORT': '6379',
        'REDIS_PASSWORD': 'staging-password',
        'REDIS_DB': '1',
        'REDIS_SSL': 'true'
    }

    # Patch environment variables
    with patch.dict(os.environ, test_env, clear=False):
        try:
            from netra_backend.app.schemas.config import StagingConfig

            # Create staging config - should load Redis config from environment
            staging_config = StagingConfig()

            # Validate Redis configuration loaded correctly
            print(f"Staging Redis Host: {staging_config.redis.host}")
            print(f"Staging Redis Port: {staging_config.redis.port}")
            print(f"Staging Redis DB: {staging_config.redis.db}")
            print(f"Staging Redis SSL: {staging_config.redis.ssl}")
            print(f"Staging Redis Password Set: {bool(staging_config.redis.password)}")

            # Validate values
            assert staging_config.redis.host == '10.107.0.3', f"Expected host '10.107.0.3', got '{staging_config.redis.host}'"
            assert staging_config.redis.port == 6379, f"Expected port 6379, got {staging_config.redis.port}"
            assert staging_config.redis.password == 'staging-password', f"Expected password 'staging-password', got '{staging_config.redis.password}'"
            assert staging_config.redis.db == 1, f"Expected db 1, got {staging_config.redis.db}"
            assert staging_config.redis.ssl == True, f"Expected ssl True, got {staging_config.redis.ssl}"

            print("✅ StagingConfig Redis configuration loading works correctly!")
            return True

        except Exception as e:
            print(f"❌ StagingConfig Redis configuration loading failed: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_default_fallback_values():
    """Test that RedisConfig uses sensible defaults when no environment variables are set."""
    print("\nTesting RedisConfig default fallback values...")

    # Clear Redis environment variables
    redis_env_vars = ['REDIS_HOST', 'REDIS_PORT', 'REDIS_PASSWORD', 'REDIS_DB', 'REDIS_SSL']
    original_values = {}

    # Save and clear environment variables
    for var in redis_env_vars:
        original_values[var] = os.environ.get(var)
        if var in os.environ:
            del os.environ[var]

    try:
        from netra_backend.app.schemas.config import RedisConfig

        # Create Redis config - should use defaults
        redis_config = RedisConfig()

        # Validate default values
        print(f"Default Redis Host: {redis_config.host}")
        print(f"Default Redis Port: {redis_config.port}")
        print(f"Default Redis DB: {redis_config.db}")
        print(f"Default Redis SSL: {redis_config.ssl}")
        print(f"Default Redis Username: {redis_config.username}")
        print(f"Default Redis Password: {redis_config.password}")

        # Validate default values
        assert redis_config.host == 'localhost', f"Expected default host 'localhost', got '{redis_config.host}'"
        assert redis_config.port == 6379, f"Expected default port 6379, got {redis_config.port}"
        assert redis_config.username == 'default', f"Expected default username 'default', got '{redis_config.username}'"
        assert redis_config.password is None, f"Expected default password None, got '{redis_config.password}'"
        assert redis_config.db == 0, f"Expected default db 0, got {redis_config.db}"
        assert redis_config.ssl == False, f"Expected default ssl False, got {redis_config.ssl}"

        print("✅ RedisConfig default fallback values work correctly!")
        return True

    except Exception as e:
        print(f"❌ RedisConfig default fallback values failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Restore original environment variables
        for var, value in original_values.items():
            if value is not None:
                os.environ[var] = value

def main():
    """Main test runner."""
    print("Issue #598 Redis Configuration Remediation Validation")
    print("=" * 55)

    test_results = []

    # Run tests
    test_results.append(test_redis_config_environment_loading())
    test_results.append(test_staging_config_redis_loading())
    test_results.append(test_default_fallback_values())

    # Summary
    passed_tests = sum(test_results)
    total_tests = len(test_results)

    print(f"\n{'='*55}")
    print(f"Test Results: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print("🎉 All Redis configuration tests passed!")
        print("✅ Issue #598 remediation is working correctly")
        return 0
    else:
        print("❌ Some Redis configuration tests failed")
        print("⚠️  Issue #598 remediation needs further investigation")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)