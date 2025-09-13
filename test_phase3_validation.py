#!/usr/bin/env python3
"""
Phase 3 validation for Issue #598 Redis Configuration Remediation.

This validates that the RedisConfig loads from environment variables correctly.
"""

import os
import sys
from unittest.mock import patch

def main():
    print("=" * 60)
    print("Phase 3: Issue #598 Redis Configuration Remediation Validation")
    print("=" * 60)

    # Test 1: RedisConfig loads from environment variables
    print("\n1. Testing RedisConfig environment variable loading...")

    test_env = {
        'REDIS_HOST': '10.107.0.3',
        'REDIS_PORT': '6379',
        'REDIS_PASSWORD': 'staging-redis-password',
        'REDIS_DB': '0',
        'REDIS_SSL': 'false'
    }

    with patch.dict(os.environ, test_env, clear=False):
        try:
            from netra_backend.app.schemas.config import RedisConfig

            config = RedisConfig()

            # Validate all environment variables were loaded
            assert config.host == '10.107.0.3', f"Host mismatch: {config.host}"
            assert config.port == 6379, f"Port mismatch: {config.port}"
            assert config.password == 'staging-redis-password', f"Password mismatch: {config.password}"
            assert config.db == 0, f"DB mismatch: {config.db}"
            assert config.ssl == False, f"SSL mismatch: {config.ssl}"

            print("   SUCCESS: RedisConfig loads from environment variables correctly")

        except Exception as e:
            print(f"   FAILED: {e}")
            return False

    # Test 2: RedisConfig falls back to defaults when no env vars
    print("\n2. Testing RedisConfig default fallbacks...")

    # Clear Redis environment variables
    redis_vars = ['REDIS_HOST', 'REDIS_PORT', 'REDIS_PASSWORD', 'REDIS_DB', 'REDIS_SSL']
    original_values = {}
    for var in redis_vars:
        original_values[var] = os.environ.get(var)
        if var in os.environ:
            del os.environ[var]

    try:
        # Import a fresh copy or create new instance
        import importlib
        if 'netra_backend.app.schemas.config' in sys.modules:
            importlib.reload(sys.modules['netra_backend.app.schemas.config'])

        from netra_backend.app.schemas.config import RedisConfig

        config = RedisConfig()

        # Validate defaults
        assert config.host == 'localhost', f"Default host mismatch: {config.host}"
        assert config.port == 6379, f"Default port mismatch: {config.port}"
        assert config.password is None, f"Default password mismatch: {config.password}"
        assert config.db == 0, f"Default db mismatch: {config.db}"
        assert config.ssl == False, f"Default ssl mismatch: {config.ssl}"

        print("   SUCCESS: RedisConfig uses correct default values")

    except Exception as e:
        print(f"   FAILED: {e}")
        return False
    finally:
        # Restore environment variables
        for var, value in original_values.items():
            if value is not None:
                os.environ[var] = value

    print("\n" + "=" * 60)
    print("CONCLUSION: Issue #598 Redis Configuration Remediation is WORKING")
    print("=" * 60)
    print()
    print("Key achievements:")
    print("- RedisConfig now loads from REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_DB, REDIS_SSL")
    print("- Environment variables are properly parsed and type-converted")
    print("- Default values are maintained for backward compatibility")
    print("- StagingConfig will load Redis configuration from Google Secret Manager")
    print()
    print("Next steps for deployment:")
    print("1. Configure Redis secrets in Google Secret Manager staging")
    print("2. Deploy updated configuration to staging")
    print("3. Verify health endpoints return 200 OK")

    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\nResult: PASS - Redis configuration remediation is ready for deployment")
        sys.exit(0)
    else:
        print("\nResult: FAIL - Redis configuration remediation needs fixes")
        sys.exit(1)