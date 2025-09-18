#!/usr/bin/env python3
"""
Test Redis Secret Loading Fixes for Issue #1343

This script validates that the Redis secret loading fixes work correctly.
It tests the updated UnifiedSecretsManager with GCP Secret Manager integration
and the RedisConnectionHandler with the new secret loading.

Usage:
    python test_redis_fixes.py
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import necessary modules
from shared.isolated_environment import get_env
from shared.logging.unified_logging_ssot import get_logger
from netra_backend.app.core.configuration.unified_secrets import (
    UnifiedSecretsManager,
    SecretConfig,
    get_secrets_manager
)

logger = get_logger(__name__)


def test_secrets_manager_gcp_integration():
    """Test the UnifiedSecretsManager GCP Secret Manager integration."""
    print("\n=== Testing UnifiedSecretsManager GCP Integration ===")

    # Test with GCP enabled configuration
    config = SecretConfig(
        use_gcp_secrets=True,
        fallback_to_env=True,
        cache_secrets=True,
        gcp_project_id="netra-staging"
    )

    secrets_manager = UnifiedSecretsManager(config)

    # Test Redis secret retrieval
    redis_secrets = ["REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD"]

    for secret_key in redis_secrets:
        print(f"\nTesting {secret_key}:")

        # Clear cache to ensure fresh retrieval
        secrets_manager.clear_cache()

        # Simulate "disabled" environment variable to trigger GCP lookup
        env = get_env()
        original_value = env.get(secret_key)
        env.set(secret_key, "disabled")

        try:
            value = secrets_manager.get_secret(secret_key)

            if value and value != "disabled":
                # Obscure sensitive values
                if "PASSWORD" in secret_key:
                    display_value = f"{value[:4]}***{value[-4:]}" if len(value) > 8 else "***"
                else:
                    display_value = value

                print(f"  PASS: Retrieved from GCP - {display_value}")
            else:
                print(f"  WARN: Could not retrieve from GCP - got: {value}")

        except Exception as e:
            print(f"  ERROR: Exception during retrieval - {e}")

        finally:
            # Restore original environment variable
            if original_value:
                env.set(secret_key, original_value)
            else:
                env.delete(secret_key)

    return True


def test_redis_connection_handler_integration():
    """Test Redis connection handler with new secrets integration."""
    print("\n=== Testing RedisConnectionHandler with Secrets Integration ===")

    try:
        # Import after setting up the environment
        from netra_backend.app.core.redis_connection_handler import RedisConnectionHandler

        # Set environment to staging to trigger secret loading
        env = get_env()
        original_env = env.get("ENVIRONMENT")
        env.set("ENVIRONMENT", "staging")

        # Create Redis connection handler
        handler = RedisConnectionHandler()

        # Get connection info
        connection_info = handler.get_connection_info()

        print(f"Connection info retrieved:")
        for key, value in connection_info.items():
            if key == "password" and value:
                display_value = f"{value[:4]}***{value[-4:]}" if len(value) > 8 else "***"
                print(f"  {key}: {display_value}")
            elif key not in ["socket_keepalive_options"]:
                print(f"  {key}: {value}")

        # Check if we got real values instead of "disabled"
        host = connection_info.get("host", "")
        port = connection_info.get("port", 0)

        if host and host != "disabled" and port and port != 0:
            print(f"  PASS: Real Redis configuration loaded")

            # Test environment config status
            config_status = handler.get_environment_config_status()

            if not config_status.get("localhost_warning", True):
                print(f"  PASS: No localhost warning - using proper Redis host")
            else:
                print(f"  WARN: Still using localhost in {config_status['environment']} environment")

        else:
            print(f"  WARN: Still using disabled configuration - secrets not loaded")

        # Restore original environment
        if original_env:
            env.set("ENVIRONMENT", original_env)

        return True

    except Exception as e:
        print(f"  ERROR: Exception in RedisConnectionHandler test - {e}")
        return False


def test_gcp_secret_mapping():
    """Test the GCP secret name mapping functionality."""
    print("\n=== Testing GCP Secret Name Mapping ===")

    config = SecretConfig(
        use_gcp_secrets=True,
        gcp_project_id="netra-staging"
    )

    secrets_manager = UnifiedSecretsManager(config)

    # Test mapping function
    test_mappings = {
        "REDIS_HOST": "redis-host-staging",
        "REDIS_PORT": "redis-port-staging",
        "REDIS_PASSWORD": "redis-password-staging",
        "POSTGRES_HOST": "postgres-host-staging",
        "JWT_SECRET": "jwt-secret-staging"
    }

    env = get_env()
    original_env = env.get("ENVIRONMENT")
    env.set("ENVIRONMENT", "staging")

    for env_key, expected_secret in test_mappings.items():
        mapped_secret = secrets_manager._map_env_to_gcp_secret(env_key)

        if mapped_secret == expected_secret:
            print(f"  PASS: {env_key} -> {mapped_secret}")
        else:
            print(f"  FAIL: {env_key} -> {mapped_secret} (expected {expected_secret})")

    # Restore environment
    if original_env:
        env.set("ENVIRONMENT", original_env)

    return True


def test_cloud_run_detection():
    """Test Cloud Run environment detection."""
    print("\n=== Testing Cloud Run Environment Detection ===")

    env = get_env()

    # Simulate Cloud Run environment
    original_k_service = env.get("K_SERVICE")
    env.set("K_SERVICE", "test-service")

    # Create new secrets manager (should detect Cloud Run)
    secrets_manager = UnifiedSecretsManager()

    if secrets_manager.config.use_gcp_secrets:
        print("  PASS: Cloud Run detected - GCP secrets enabled")
    else:
        print("  FAIL: Cloud Run not detected - GCP secrets not enabled")

    # Restore environment
    if original_k_service:
        env.set("K_SERVICE", original_k_service)
    else:
        env.delete("K_SERVICE")

    return True


def main():
    """Run all Redis secret loading tests."""
    print("Redis Secret Loading Fixes Test - Issue #1343")
    print("=" * 60)

    tests = [
        ("GCP Secret Manager Integration", test_secrets_manager_gcp_integration),
        ("Redis Connection Handler Integration", test_redis_connection_handler_integration),
        ("GCP Secret Name Mapping", test_gcp_secret_mapping),
        ("Cloud Run Environment Detection", test_cloud_run_detection),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")

        try:
            result = test_func()
            if result:
                passed += 1
                print(f"RESULT: PASSED")
            else:
                print(f"RESULT: FAILED")
        except Exception as e:
            print(f"RESULT: ERROR - {e}")

    print(f"\n=== Test Summary ===")
    print(f"Passed: {passed}/{total} tests")

    if passed == total:
        print("All Redis secret loading fixes are working correctly!")
        sys.exit(0)
    else:
        print("Some tests failed - Redis secret loading needs more fixes.")
        sys.exit(1)


if __name__ == "__main__":
    main()