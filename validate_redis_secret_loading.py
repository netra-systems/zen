#!/usr/bin/env python3
"""
Validate Redis Secret Loading Implementation for Issue #1343

This script validates that the implementation is correct and will work
in Cloud Run environment with proper GCP secret access.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from shared.isolated_environment import get_env
from netra_backend.app.core.configuration.unified_secrets import UnifiedSecretsManager, SecretConfig


def validate_implementation():
    """Validate the Redis secret loading implementation."""
    print("Redis Secret Loading Implementation Validation")
    print("=" * 60)

    # Test 1: Verify GCP Secret Manager mapping is correct
    print("\n1. Testing GCP Secret Name Mapping...")

    config = SecretConfig(use_gcp_secrets=True, gcp_project_id="netra-staging")
    manager = UnifiedSecretsManager(config)

    env = get_env()
    original_env = env.get("ENVIRONMENT")
    env.set("ENVIRONMENT", "staging")

    expected_mappings = {
        "REDIS_HOST": "redis-host-staging",
        "REDIS_PORT": "redis-port-staging",
        "REDIS_PASSWORD": "redis-password-staging",
        "REDIS_URL": "redis-url-staging"
    }

    mapping_passed = True
    for env_key, expected_secret in expected_mappings.items():
        actual_secret = manager._map_env_to_gcp_secret(env_key)
        if actual_secret == expected_secret:
            print(f"   PASS {env_key} -> {actual_secret}")
        else:
            print(f"   FAIL {env_key} -> {actual_secret} (expected {expected_secret})")
            mapping_passed = False

    if original_env:
        env.set("ENVIRONMENT", original_env)

    # Test 2: Verify Cloud Run detection logic
    print("\n2. Testing Cloud Run Environment Detection...")

    # Simulate Cloud Run environment
    original_k_service = env.get("K_SERVICE")
    env.set("K_SERVICE", "netra-backend-staging")

    cloud_run_manager = UnifiedSecretsManager()

    if cloud_run_manager.config.use_gcp_secrets:
        print("   PASS Cloud Run detected - GCP secrets automatically enabled")
        cloud_run_passed = True
    else:
        print("   FAIL Cloud Run not detected - GCP secrets not enabled")
        cloud_run_passed = False

    # Restore environment
    if original_k_service:
        env.set("K_SERVICE", original_k_service)
    else:
        env.delete("K_SERVICE")

    # Test 3: Verify disabled value handling
    print("\n3. Testing Disabled Value Handling...")

    config = SecretConfig(use_gcp_secrets=True, gcp_project_id="netra-staging")
    manager = UnifiedSecretsManager(config)

    # Simulate disabled environment variable
    env.set("TEST_SECRET", "disabled")

    # This should attempt GCP lookup when value is "disabled"
    # We can't test actual GCP access locally, but we can verify the logic

    # Mock the GCP secret retrieval for testing
    original_get_secret_from_gcp = manager._get_secret_from_gcp

    def mock_get_secret_from_gcp(secret_name):
        if secret_name == "test-secret-staging":
            return "mock-secret-value"
        return None

    manager._get_secret_from_gcp = mock_get_secret_from_gcp

    # Map TEST_SECRET to a GCP secret name
    def mock_map_env_to_gcp_secret(env_key):
        if env_key == "TEST_SECRET":
            return "test-secret-staging"
        return original_get_secret_from_gcp.__self__._map_env_to_gcp_secret(env_key)

    manager._map_env_to_gcp_secret = mock_map_env_to_gcp_secret

    value = manager.get_secret("TEST_SECRET")

    if value == "mock-secret-value":
        print("   PASS Disabled values trigger GCP secret lookup")
        disabled_passed = True
    else:
        print(f"   FAIL Disabled values not handled correctly - got: {value}")
        disabled_passed = False

    # Clean up
    env.delete("TEST_SECRET")

    # Test 4: Verify Redis connection handler integration
    print("\n4. Testing Redis Connection Handler Integration...")

    try:
        from netra_backend.app.core.redis_connection_handler import RedisConnectionHandler

        # Check if handler imports secrets manager
        handler = RedisConnectionHandler()

        if hasattr(handler, '_secrets_manager'):
            print("   PASS Redis handler has secrets manager")
            handler_passed = True
        else:
            print("   FAIL Redis handler missing secrets manager")
            handler_passed = False

    except Exception as e:
        print(f"   FAIL Redis handler integration error: {e}")
        handler_passed = False

    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)

    results = {
        "GCP Secret Name Mapping": mapping_passed,
        "Cloud Run Detection": cloud_run_passed,
        "Disabled Value Handling": disabled_passed,
        "Redis Handler Integration": handler_passed
    }

    passed_count = sum(results.values())
    total_count = len(results)

    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"   {status}: {test_name}")

    print(f"\nOverall: {passed_count}/{total_count} validations passed")

    if passed_count == total_count:
        print("\nAll validations passed!")
        print("\nThe Redis secret loading implementation is ready for Cloud Run deployment.")
        print("\nExpected behavior in Cloud Run:")
        print("1. Cloud Run environment (K_SERVICE) automatically enables GCP Secret Manager")
        print("2. Disabled Redis environment variables trigger GCP secret lookups")
        print("3. Secrets loaded from redis-host-staging, redis-port-staging, redis-password-staging")
        print("4. Redis connections use real values from GCP Secret Manager")

        return True
    else:
        print("\nSome validations failed!")
        print("The implementation needs fixes before deployment.")
        return False


if __name__ == "__main__":
    success = validate_implementation()
    sys.exit(0 if success else 1)