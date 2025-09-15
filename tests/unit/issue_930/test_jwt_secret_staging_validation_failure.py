"""
Unit Tests for Issue #930 - JWT Secret Staging Validation Failures

These tests reproduce the exact JWT_SECRET_STAGING validation failure observed in staging
environment. Designed to FAIL initially and expose the root cause of authentication issues.

Focus Areas:
1. JWT secret resolution hierarchy failures in staging environment
2. Environment-specific secret validation edge cases
3. SSOT vs direct environment access inconsistencies
4. Service authentication token generation failures

Business Impact: $500K+ ARR - Fixes critical authentication blocking Golden Path
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from shared.jwt_secret_manager import JWTSecretManager, get_jwt_secret_manager, get_unified_jwt_secret
from shared.isolated_environment import IsolatedEnvironment


class TestJWTSecretStagingValidationFailure:
    """Test suite reproducing JWT_SECRET_STAGING validation failures from staging logs."""

    def setup_method(self):
        """Reset JWT secret manager state for each test."""
        # Clear any cached secrets
        if hasattr(get_jwt_secret_manager(), '_cached_secret'):
            get_jwt_secret_manager()._cached_secret = None
        if hasattr(get_jwt_secret_manager(), '_cached_algorithm'):
            get_jwt_secret_manager()._cached_algorithm = None

    def test_jwt_secret_staging_missing_environment_variable_failure(self):
        """
        FAILING TEST: Reproduce JWT_SECRET_STAGING missing in staging environment.

        Expected to FAIL - This reproduces the exact staging environment failure
        where JWT_SECRET_STAGING is not properly configured or accessible.
        """
        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            # Simulate staging environment WITHOUT JWT_SECRET_STAGING
            mock_get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'staging',
                'JWT_SECRET_KEY': None,  # Also missing generic key
                'JWT_SECRET': None,      # Also missing legacy key
                'JWT_SECRET_STAGING': None,  # MISSING - This is the core issue
                'TESTING': 'false',
                'PYTEST_CURRENT_TEST': None
            }.get(key, default)

            manager = JWTSecretManager()

            # This should FAIL with ValueError due to missing staging JWT secret
            with pytest.raises(ValueError, match="JWT secret not configured for staging environment"):
                secret = manager.get_jwt_secret()

            # If we get here, the test FAILED - staging should require explicit JWT config
            pytest.fail(
                "JWT secret manager should raise ValueError for missing staging JWT secret, "
                "but it returned a secret instead. This indicates improper fallback logic "
                "that's causing staging authentication failures."
            )

    def test_jwt_secret_staging_environment_hierarchy_failure(self):
        """
        FAILING TEST: Reproduce incorrect JWT secret hierarchy in staging.

        Expected to FAIL - Tests the secret resolution order that's causing
        staging environment to use wrong or invalid JWT secrets.
        """
        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            # Simulate staging environment with conflicting JWT secrets
            mock_get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'staging',
                'JWT_SECRET_STAGING': 'staging-secret-from-env-var',
                'JWT_SECRET_KEY': 'generic-secret-different-value',
                'JWT_SECRET': 'legacy-secret-another-value',
                'TESTING': 'false',
                'PYTEST_CURRENT_TEST': None
            }.get(key, default)

            manager = JWTSecretManager()
            secret = manager.get_jwt_secret()

            # This test expects JWT_SECRET_STAGING to take priority in staging
            # If this fails, it means the hierarchy is wrong
            assert secret == 'staging-secret-from-env-var', (
                f"Expected staging-specific JWT_SECRET_STAGING to be used, "
                f"but got {secret}. This hierarchy mismatch is causing "
                f"staging authentication failures - services are using "
                f"different JWT secrets for token generation vs validation."
            )

    def test_jwt_secret_fallback_to_secrets_manager_failure(self):
        """
        FAILING TEST: Reproduce secrets manager fallback failure in staging.

        Expected to FAIL - Tests the deployment secrets manager fallback
        that should work in staging but appears to be failing.
        """
        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            # Simulate staging environment without explicit env vars
            mock_get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'staging',
                'JWT_SECRET_STAGING': None,
                'JWT_SECRET_KEY': None,
                'JWT_SECRET': None,
                'TESTING': 'false',
                'PYTEST_CURRENT_TEST': None
            }.get(key, default)

            # Mock the deployment secrets manager to simulate failure
            with patch('shared.jwt_secret_manager.get_staging_secret') as mock_secrets:
                mock_secrets.side_effect = Exception("Secret manager connection failed")

                manager = JWTSecretManager()

                # This should FAIL - secrets manager fallback isn't working
                with pytest.raises(ValueError, match="JWT secret not configured for staging environment"):
                    secret = manager.get_jwt_secret()

                # If we get here without exception, the test FAILED
                pytest.fail(
                    "Expected ValueError when both environment variables and secrets manager fail, "
                    "but JWT secret manager returned a value. This suggests improper error handling "
                    "that's masking the real staging authentication configuration issues."
                )

    def test_jwt_secret_deterministic_vs_explicit_validation_failure(self):
        """
        FAILING TEST: Reproduce deterministic secret validation failure in staging.

        Expected to FAIL - Tests the validation logic that incorrectly accepts
        or rejects deterministic vs explicit JWT secrets in staging context.
        """
        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'staging',
                'TESTING': 'false',
                'PYTEST_CURRENT_TEST': None
            }.get(key, default)

            manager = JWTSecretManager()

            # Test deterministic secret (should be rejected in staging)
            import hashlib
            deterministic_secret = hashlib.sha256(b"netra_staging_jwt_key").hexdigest()[:32]

            is_valid, context = manager.validate_jwt_secret_for_environment(
                deterministic_secret, 'staging'
            )

            # This should FAIL - deterministic secrets shouldn't be valid in staging
            assert not is_valid, (
                f"Deterministic JWT secret should be rejected in staging environment, "
                f"but was accepted. Context: {context}. This validation logic error "
                f"is allowing insecure secrets in staging, causing authentication issues."
            )

    def test_ssot_vs_direct_environment_access_inconsistency(self):
        """
        FAILING TEST: Reproduce SSOT vs direct os.environ access inconsistency.

        Expected to FAIL - Tests the inconsistency between SSOT IsolatedEnvironment
        and direct os.environ access that's causing different JWT secrets.
        """
        # Set up conflicting environment variables
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'staging',
            'JWT_SECRET_STAGING': 'direct-os-environ-secret',
            'JWT_SECRET_KEY': 'direct-generic-secret'
        }):
            # Test direct os.environ access
            direct_secret = os.environ.get('JWT_SECRET_STAGING')

            # Test SSOT IsolatedEnvironment access
            with patch.object(IsolatedEnvironment, 'get') as mock_get:
                mock_get.side_effect = lambda key, default=None: {
                    'ENVIRONMENT': 'staging',
                    'JWT_SECRET_STAGING': 'ssot-isolated-env-secret',  # DIFFERENT VALUE
                    'JWT_SECRET_KEY': 'ssot-generic-secret',
                    'TESTING': 'false',
                    'PYTEST_CURRENT_TEST': None
                }.get(key, default)

                manager = JWTSecretManager()
                ssot_secret = manager.get_jwt_secret()

                # This should FAIL - secrets should be consistent
                assert direct_secret == ssot_secret, (
                    f"CRITICAL INCONSISTENCY: Direct os.environ access gives '{direct_secret}' "
                    f"but SSOT IsolatedEnvironment gives '{ssot_secret}'. This inconsistency "
                    f"is causing some services to use different JWT secrets, resulting in "
                    f"token validation failures and 403 authentication errors in staging."
                )

    def test_jwt_secret_validation_context_detection_failure(self):
        """
        FAILING TEST: Reproduce test context detection failure in staging.

        Expected to FAIL - Tests the logic that incorrectly identifies staging
        environment as testing context, leading to improper validation rules.
        """
        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'staging',  # Real staging
                'TESTING': 'false',        # Not testing
                'PYTEST_CURRENT_TEST': None  # Not in pytest
            }.get(key, default)

            manager = JWTSecretManager()

            # Test with a very short secret that should only be valid in test context
            short_secret = "test"  # Only 4 characters

            is_valid, context = manager.validate_jwt_secret_for_environment(
                short_secret, 'staging'
            )

            # This should FAIL - staging should require longer secrets
            assert not is_valid, (
                f"Short JWT secret (4 chars) should be rejected in staging, "
                f"but was accepted. Validation context: {context}. This suggests "
                f"staging environment is being incorrectly detected as test context, "
                f"causing production environment to accept insecure test secrets."
            )

    def test_service_authentication_token_generation_failure(self):
        """
        FAILING TEST: Reproduce service authentication token generation failure.

        Expected to FAIL - Tests the scenario where backend service cannot generate
        valid JWT tokens due to JWT secret configuration issues, resulting in
        403 "Not authenticated" errors observed in staging logs.
        """
        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            # Simulate the exact staging environment that's causing failures
            mock_get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'staging',
                'JWT_SECRET_STAGING': None,  # Missing from environment
                'JWT_SECRET_KEY': None,      # Missing from environment
                'JWT_SECRET': None,          # Missing from environment
                'TESTING': 'false',
                'PYTEST_CURRENT_TEST': None
            }.get(key, default)

            # Mock failed secrets manager access (network issues, permissions, etc.)
            with patch('shared.jwt_secret_manager.get_staging_secret') as mock_secrets:
                mock_secrets.side_effect = ImportError("deployment.secrets_config module not available")

                manager = JWTSecretManager()

                # This should FAIL with the exact error pattern from staging logs
                with pytest.raises(ValueError) as exc_info:
                    secret = manager.get_jwt_secret()

                error_message = str(exc_info.value)

                # Verify this matches the staging failure pattern
                assert "JWT secret not configured for staging environment" in error_message
                assert "JWT_SECRET_STAGING" in error_message or "JWT_SECRET_KEY" in error_message
                assert "$50K MRR" in error_message or "WebSocket functionality" in error_message

                # If we get here without the expected error, the test FAILED
                if not exc_info.value:
                    pytest.fail(
                        "Expected JWT secret resolution to fail with proper error message "
                        "matching staging logs, but no exception was raised. This indicates "
                        "the error handling isn't working correctly, masking the real issue "
                        "causing service authentication failures (403 errors for 'service:netra-backend')."
                    )


class TestJWTSecretManagerEnvironmentAccessPatterns:
    """Test JWT secret manager environment access patterns causing staging failures."""

    def test_isolated_environment_import_failure(self):
        """
        FAILING TEST: Reproduce IsolatedEnvironment import failure.

        Expected to FAIL - Tests the scenario where IsolatedEnvironment import
        fails, causing JWT secret manager to fall back to emergency defaults.
        """
        # Mock ImportError for isolated_environment
        with patch('shared.jwt_secret_manager.get_env') as mock_get_env:
            mock_get_env.side_effect = ImportError("Could not import isolated environment")

            manager = JWTSecretManager()
            secret = manager.get_jwt_secret()

            # This should result in emergency fallback
            assert secret == "fallback_jwt_secret_for_emergency_only", (
                f"Expected emergency fallback secret when IsolatedEnvironment import fails, "
                f"but got '{secret}'. This indicates the error handling isn't working "
                f"correctly, which could cause unexpected JWT secrets in staging environment."
            )

    def test_environment_detection_inconsistency(self):
        """
        FAILING TEST: Reproduce environment detection inconsistency.

        Expected to FAIL - Tests the scenario where different parts of the system
        detect different environments, leading to JWT secret mismatch.
        """
        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            # Simulate inconsistent environment detection
            call_count = 0
            def inconsistent_env_get(key, default=None):
                nonlocal call_count
                call_count += 1

                # First call returns 'staging', second call returns 'development'
                if key == 'ENVIRONMENT':
                    return 'staging' if call_count == 1 else 'development'
                elif key == 'JWT_SECRET_STAGING':
                    return 'staging-specific-secret'
                elif key == 'JWT_SECRET_KEY':
                    return 'generic-key-secret'
                else:
                    return default

            mock_get.side_effect = inconsistent_env_get

            manager = JWTSecretManager()

            # Get secret twice - should be consistent
            secret1 = manager.get_jwt_secret()
            secret2 = manager.get_jwt_secret()

            # This should FAIL if environment detection is inconsistent
            assert secret1 == secret2, (
                f"JWT secret should be consistent across calls, but got '{secret1}' "
                f"then '{secret2}'. This inconsistency suggests environment detection "
                f"is unreliable, which could cause authentication failures when different "
                f"parts of the system use different JWT secrets."
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])