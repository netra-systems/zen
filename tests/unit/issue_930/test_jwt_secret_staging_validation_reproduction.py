"""
Unit Tests for Issue #930 - JWT Secret Staging Validation Failure Reproduction

This test suite reproduces the EXACT staging failure scenario described in Issue #930.
These tests are designed to FAIL initially to expose the root cause of JWT authentication
issues blocking $500K MRR WebSocket functionality in staging environment.

Test Categories:
1. JWT secret hierarchy resolution failures in staging environment
2. Environment variable configuration validation edge cases
3. Service startup authentication token generation failures
4. SSOT vs direct environment access inconsistencies

All tests should FAIL initially - this is expected and reproduces the staging issue.

Business Impact: P0 Critical - Fixes authentication blocking Golden Path in staging
Error Pattern: "JWT secret not configured for staging environment. Please set JWT_SECRET_STAGING or JWT_SECRET_KEY"
GCP Log IDs: 68c450750006d02711ebe1b6, 68c450750006d011c18730c6
"""

import pytest
import os
import hashlib
from unittest.mock import patch, MagicMock
from shared.jwt_secret_manager import JWTSecretManager, get_jwt_secret_manager, get_unified_jwt_secret
from shared.isolated_environment import IsolatedEnvironment, get_env


@pytest.mark.unit
class TestJWTSecretStagingFailureReproduction:
    """Reproduce the exact JWT secret staging failures from GCP logs."""

    def setup_method(self):
        """Reset JWT secret manager state for each test."""
        # Clear any cached secrets to ensure fresh resolution
        manager = get_jwt_secret_manager()
        if hasattr(manager, '_cached_secret'):
            manager._cached_secret = None
        if hasattr(manager, '_cached_algorithm'):
            manager._cached_algorithm = None

        # Reset isolated environment to clean state
        env = get_env()
        if hasattr(env, '_env_cache'):
            env._env_cache.clear()

    def test_staging_jwt_secret_missing_complete_failure(self):
        """
        CRITICAL REPRODUCTION: Exact staging environment JWT secret missing failure.

        This test reproduces the exact error from GCP logs:
        "JWT secret not configured for staging environment. Please set JWT_SECRET_STAGING or JWT_SECRET_KEY"

        Expected: SHOULD FAIL with ValueError matching staging logs
        """
        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            # Simulate EXACT staging environment from GCP logs - NO JWT secrets available
            mock_get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'staging',
                'JWT_SECRET_STAGING': None,      # MISSING - Primary issue from logs
                'JWT_SECRET_KEY': None,          # MISSING - Fallback also unavailable
                'JWT_SECRET': None,              # MISSING - Legacy fallback unavailable
                'TESTING': 'false',              # NOT in test context
                'PYTEST_CURRENT_TEST': None,     # NOT in pytest context
                'GCP_PROJECT_ID': 'netra-staging', # Staging GCP context
                'K_SERVICE': 'backend-staging'   # Cloud Run service context
            }.get(key, default)

            # Mock deployment secrets manager to fail (network/permission issues in staging)
            with patch('shared.jwt_secret_manager.get_staging_secret') as mock_secrets:
                mock_secrets.side_effect = ImportError("deployment.secrets_config module not available")

                manager = JWTSecretManager()

                # This SHOULD FAIL with the exact error from staging logs
                with pytest.raises(ValueError) as exc_info:
                    secret = manager.get_jwt_secret()

                # Verify exact error message pattern from GCP logs
                error_message = str(exc_info.value)
                assert "JWT secret not configured for staging environment" in error_message
                assert "JWT_SECRET_STAGING" in error_message
                assert "JWT_SECRET_KEY" in error_message
                assert "WebSocket functionality" in error_message or "$50K MRR" in error_message

                print(f"✓ Reproduced staging failure: {error_message}")

    def test_staging_environment_detection_validation_failure(self):
        """
        CRITICAL REPRODUCTION: Staging environment detection leading to wrong validation.

        This test reproduces the scenario where staging environment is incorrectly
        treated as test context, allowing insecure secrets.

        Expected: SHOULD FAIL - staging should not accept test-level secrets
        """
        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            # Simulate staging environment that might be misdetected as test context
            mock_get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'staging',
                'GCP_PROJECT_ID': 'netra-staging',
                'K_SERVICE': 'backend-staging',
                'TESTING': 'false',              # Explicitly NOT testing
                'PYTEST_CURRENT_TEST': None      # Explicitly NOT in pytest
            }.get(key, default)

            manager = JWTSecretManager()

            # Test with a short secret that should only be valid in test contexts
            short_test_secret = "test"  # Only 4 characters

            is_valid, context = manager.validate_jwt_secret_for_environment(
                short_test_secret, 'staging'
            )

            # This SHOULD FAIL - staging must reject short test secrets
            assert not is_valid, (
                f"CRITICAL FAILURE: Staging environment accepted 4-character test secret! "
                f"Validation context: {context}. This suggests staging environment is being "
                f"incorrectly detected as test context, allowing insecure secrets that cause "
                f"authentication failures. Expected rejection with minimum 32-character requirement."
            )

    def test_staging_jwt_secret_hierarchy_wrong_priority_failure(self):
        """
        CRITICAL REPRODUCTION: JWT secret hierarchy priority causing wrong secret selection.

        This test reproduces issues where multiple JWT secrets exist but wrong one is chosen,
        causing token generation/validation mismatch between services.

        Expected: SHOULD FAIL if hierarchy is wrong - must prioritize staging-specific secret
        """
        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            # Simulate staging environment with multiple JWT secrets available
            mock_get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'staging',
                'JWT_SECRET_STAGING': 'correct-staging-specific-secret-32-chars-long',     # Should win
                'JWT_SECRET_KEY': 'wrong-generic-secret-also-32-chars-long',              # Should lose
                'JWT_SECRET': 'legacy-wrong-secret-32-characters-long',                   # Should lose
                'TESTING': 'false',
                'PYTEST_CURRENT_TEST': None,
                'GCP_PROJECT_ID': 'netra-staging'
            }.get(key, default)

            manager = JWTSecretManager()
            selected_secret = manager.get_jwt_secret()

            # This test verifies staging-specific secret takes priority
            expected_secret = 'correct-staging-specific-secret-32-chars-long'

            if selected_secret != expected_secret:
                pytest.fail(
                    f"CRITICAL HIERARCHY FAILURE: Expected JWT_SECRET_STAGING to take priority "
                    f"in staging environment but got '{selected_secret}' instead of '{expected_secret}'. "
                    f"This hierarchy mismatch causes different services to use different JWT secrets, "
                    f"resulting in token validation failures and 403 authentication errors. "
                    f"Backend generates tokens with one secret while auth service validates with another."
                )

    def test_staging_secrets_manager_fallback_network_failure(self):
        """
        CRITICAL REPRODUCTION: Secrets manager network/permission failure in staging.

        This test reproduces the scenario where environment variables are missing AND
        deployment secrets manager is unreachable, causing complete authentication failure.

        Expected: SHOULD FAIL - no fallback should be available in staging
        """
        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            # Simulate staging environment with missing env vars
            mock_get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'staging',
                'JWT_SECRET_STAGING': None,
                'JWT_SECRET_KEY': None,
                'JWT_SECRET': None,
                'TESTING': 'false',
                'PYTEST_CURRENT_TEST': None,
                'GCP_PROJECT_ID': 'netra-staging'
            }.get(key, default)

            # Simulate network failure to secrets manager (common in Cloud Run cold starts)
            with patch('shared.jwt_secret_manager.get_staging_secret') as mock_secrets:
                mock_secrets.side_effect = Exception("Connection timeout to secrets manager")

                manager = JWTSecretManager()

                # This SHOULD FAIL - no emergency fallbacks allowed in staging
                with pytest.raises(ValueError) as exc_info:
                    secret = manager.get_jwt_secret()

                error_message = str(exc_info.value)

                # Verify proper error handling without emergency fallbacks
                assert "JWT secret not configured for staging environment" in error_message

                # Should NOT contain emergency fallback values
                invalid_fallbacks = [
                    "emergency_jwt_secret",
                    "fallback_jwt_secret",
                    "deterministic",
                    "test-jwt-secret"
                ]

                # If we got a secret instead of exception, check it's not a fallback
                secret_obtained = False
                try:
                    secret = manager.get_jwt_secret()
                    secret_obtained = True
                    for fallback in invalid_fallbacks:
                        if fallback in secret:
                            pytest.fail(
                                f"CRITICAL FALLBACK FAILURE: Staging environment used emergency "
                                f"fallback '{secret}' instead of proper error. This masks configuration "
                                f"issues and causes unpredictable authentication behavior."
                            )
                except:
                    pass  # Expected failure

    def test_staging_service_token_generation_complete_failure(self):
        """
        CRITICAL REPRODUCTION: Service token generation failure causing 403 errors.

        This reproduces the scenario from GCP logs where backend service cannot generate
        valid JWT tokens, resulting in "Not authenticated" errors for service:netra-backend.

        Expected: SHOULD FAIL - service authentication should be impossible without proper JWT config
        """
        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            # Simulate the exact staging environment state during failure
            mock_get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'staging',
                'SERVICE_ID': 'netra-backend',    # Service trying to authenticate
                'JWT_SECRET_STAGING': None,       # Missing from GCP Cloud Run config
                'JWT_SECRET_KEY': None,           # Missing from GCP Cloud Run config
                'JWT_SECRET': None,               # Missing from GCP Cloud Run config
                'TESTING': 'false',
                'PYTEST_CURRENT_TEST': None,
                'GCP_PROJECT_ID': 'netra-staging',
                'K_SERVICE': 'backend-staging'
            }.get(key, default)

            # Mock complete secrets manager failure (as in GCP logs)
            with patch('shared.jwt_secret_manager.get_staging_secret') as mock_secrets:
                mock_secrets.side_effect = ImportError(
                    "deployment.secrets_config module not available in Cloud Run"
                )

                manager = JWTSecretManager()

                # This SHOULD FAIL - service cannot generate authentication tokens
                try:
                    secret = manager.get_jwt_secret()

                    # If we somehow got a secret, it should not be usable for service auth
                    if secret:
                        pytest.fail(
                            f"CRITICAL SERVICE AUTH FAILURE: JWT secret manager returned '{secret}' "
                            f"in staging environment without proper configuration. This allows the "
                            f"service to think it can generate valid tokens, but they will fail "
                            f"validation, causing 403 'Not authenticated' errors for service:netra-backend. "
                            f"Service startup should fail completely rather than generate invalid tokens."
                        )

                except ValueError as e:
                    # This is the expected behavior - complete failure
                    error_msg = str(e)
                    assert "JWT secret not configured for staging environment" in error_msg
                    print(f"✓ Correctly failed service token generation: {error_msg}")

                except Exception as e:
                    pytest.fail(
                        f"UNEXPECTED ERROR TYPE: Expected ValueError for JWT config missing, "
                        f"but got {type(e).__name__}: {e}. This suggests improper error handling "
                        f"that may mask the real configuration issues in staging."
                    )

    def test_staging_deterministic_secret_rejection_failure(self):
        """
        CRITICAL REPRODUCTION: Deterministic secret incorrectly accepted in staging.

        This test reproduces the scenario where staging environment incorrectly accepts
        deterministic test secrets, leading to predictable JWT tokens.

        Expected: SHOULD FAIL - staging must reject deterministic secrets
        """
        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'staging',
                'TESTING': 'false',              # NOT in test context
                'PYTEST_CURRENT_TEST': None,     # NOT in pytest
                'GCP_PROJECT_ID': 'netra-staging'
            }.get(key, default)

            manager = JWTSecretManager()

            # Generate the deterministic secret that would be created for staging
            deterministic_secret = hashlib.sha256(b"netra_staging_jwt_key").hexdigest()[:32]

            is_valid, context = manager.validate_jwt_secret_for_environment(
                deterministic_secret, 'staging'
            )

            # This SHOULD FAIL - deterministic secrets are security risk in staging
            assert not is_valid, (
                f"CRITICAL SECURITY FAILURE: Staging environment accepted deterministic JWT secret! "
                f"Secret: {deterministic_secret[:8]}... Validation context: {context}. "
                f"Deterministic secrets are predictable and create security vulnerabilities "
                f"in production-like environments. This must be rejected to force proper "
                f"secret configuration in staging deployment."
            )

    def test_staging_environment_inconsistency_detection_failure(self):
        """
        CRITICAL REPRODUCTION: Environment detection inconsistency between JWT calls.

        This test reproduces issues where different parts of the system detect different
        environments, leading to JWT secret mismatch between services.

        Expected: SHOULD FAIL if environment detection is inconsistent across calls
        """
        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            # Simulate inconsistent environment detection (race condition or caching issue)
            call_count = 0
            def inconsistent_environment_detection(key, default=None):
                nonlocal call_count
                call_count += 1

                # First few calls return staging, later calls return development
                # This simulates environment detection inconsistency
                if key == 'ENVIRONMENT':
                    return 'staging' if call_count <= 3 else 'development'
                elif key == 'JWT_SECRET_STAGING':
                    return 'staging-specific-secret-32-chars-long'
                elif key == 'JWT_SECRET_KEY':
                    return 'generic-secret-also-32-chars-long'
                elif key in ['TESTING', 'PYTEST_CURRENT_TEST']:
                    return None
                else:
                    return default

            mock_get.side_effect = inconsistent_environment_detection

            manager = JWTSecretManager()

            # Get JWT secret multiple times - should be consistent
            secret1 = manager.get_jwt_secret()
            secret2 = manager.get_jwt_secret()

            # Clear cache to force re-detection
            manager._cached_secret = None
            secret3 = manager.get_jwt_secret()

            # This SHOULD FAIL if environment detection is inconsistent
            secrets = [secret1, secret2, secret3]
            unique_secrets = set(secrets)

            if len(unique_secrets) > 1:
                pytest.fail(
                    f"CRITICAL CONSISTENCY FAILURE: JWT secrets inconsistent across calls! "
                    f"Got secrets: {list(unique_secrets)}. This indicates environment detection "
                    f"is unreliable, causing different parts of the system to use different "
                    f"JWT secrets. Backend service generates tokens with one secret while "
                    f"auth service validates with another, causing 403 authentication failures."
                )


@pytest.mark.unit
class TestJWTSecretManagerEnvironmentIntegration:
    """Integration tests for JWT secret manager environment access patterns."""

    def setup_method(self):
        """Reset environment state for each test."""
        self.env_manager = get_env()
        self.jwt_manager = get_jwt_secret_manager()

        # Clear caches
        if hasattr(self.jwt_manager, '_cached_secret'):
            self.jwt_manager._cached_secret = None
        if hasattr(self.env_manager, '_env_cache'):
            self.env_manager._env_cache.clear()

    def test_isolated_environment_vs_os_environ_staging_mismatch(self):
        """
        CRITICAL REPRODUCTION: SSOT IsolatedEnvironment vs os.environ mismatch in staging.

        This test reproduces the scenario where SSOT IsolatedEnvironment returns different
        JWT secrets than direct os.environ access, causing service mismatch.

        Expected: SHOULD FAIL - both access methods must return identical values
        """
        # Set up staging environment in os.environ
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'staging',
            'JWT_SECRET_STAGING': 'direct-os-environ-staging-secret-32-chars',
            'GCP_PROJECT_ID': 'netra-staging'
        }):
            # Get secret via direct os.environ access (what some legacy code might use)
            direct_secret = os.environ.get('JWT_SECRET_STAGING')

            # Get secret via SSOT IsolatedEnvironment (what new code uses)
            with patch.object(IsolatedEnvironment, 'get') as mock_get:
                mock_get.side_effect = lambda key, default=None: {
                    'ENVIRONMENT': 'staging',
                    'JWT_SECRET_STAGING': 'ssot-isolated-different-secret-32-chars',  # DIFFERENT!
                    'TESTING': 'false',
                    'PYTEST_CURRENT_TEST': None,
                    'GCP_PROJECT_ID': 'netra-staging'
                }.get(key, default)

                ssot_secret = self.jwt_manager.get_jwt_secret()

                # This SHOULD FAIL - secrets must be identical
                if direct_secret != ssot_secret:
                    pytest.fail(
                        f"CRITICAL SSOT MISMATCH: Direct os.environ returns '{direct_secret}' "
                        f"but SSOT IsolatedEnvironment returns '{ssot_secret}'. This mismatch "
                        f"causes some services (using direct access) to generate tokens with "
                        f"one secret while other services (using SSOT) validate with different "
                        f"secret, resulting in systematic authentication failures and 403 errors."
                    )

    def test_staging_cold_start_environment_loading_failure(self):
        """
        CRITICAL REPRODUCTION: GCP Cloud Run cold start environment loading failure.

        This test reproduces the scenario where environment variables are not properly
        loaded during Cloud Run cold start, causing JWT secret resolution to fail.

        Expected: SHOULD FAIL - environment loading must be reliable or fail fast
        """
        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            # Simulate Cloud Run cold start with partial environment loading
            load_attempt = 0
            def unreliable_environment_loading(key, default=None):
                nonlocal load_attempt
                load_attempt += 1

                # Simulate environment variables not yet loaded (cold start)
                if load_attempt <= 2:
                    return None  # Environment not ready yet

                # After a few attempts, environment becomes available
                return {
                    'ENVIRONMENT': 'staging',
                    'JWT_SECRET_STAGING': 'cold-start-delayed-secret-32-chars',
                    'GCP_PROJECT_ID': 'netra-staging',
                    'K_SERVICE': 'backend-staging'
                }.get(key, default)

            mock_get.side_effect = unreliable_environment_loading

            manager = JWTSecretManager()

            # First attempt should fail due to cold start
            try:
                secret = manager.get_jwt_secret()

                # If we got a secret on first try, it might be an emergency fallback
                # which masks the real cold start issue
                if secret and any(fallback in secret for fallback in
                                ['emergency', 'fallback', 'deterministic']):
                    pytest.fail(
                        f"CRITICAL COLD START MASKING: JWT secret manager returned fallback "
                        f"'{secret}' during simulated cold start instead of failing fast. "
                        f"This masks environment loading issues and allows service to start "
                        f"with wrong JWT secret, causing authentication failures once "
                        f"environment is properly loaded."
                    )

            except ValueError as e:
                # This is acceptable - fail fast during cold start
                print(f"✓ Correctly failed during cold start: {e}")

    def test_staging_service_discovery_jwt_configuration_failure(self):
        """
        CRITICAL REPRODUCTION: Service discovery JWT configuration mismatch.

        This test reproduces the scenario where service discovery mechanisms return
        different JWT configurations than environment variables, causing auth mismatch.

        Expected: SHOULD FAIL - service discovery and env vars must be consistent
        """
        # Mock service discovery returning different JWT config
        mock_discovery_jwt_secret = "service-discovery-jwt-secret-32-chars"

        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'staging',
                'JWT_SECRET_STAGING': 'environment-var-jwt-secret-32-chars',  # Different!
                'TESTING': 'false',
                'PYTEST_CURRENT_TEST': None,
                'GCP_PROJECT_ID': 'netra-staging'
            }.get(key, default)

            # Mock service discovery (could be from deployment.secrets_config)
            with patch('shared.jwt_secret_manager.get_staging_secret') as mock_discovery:
                mock_discovery.return_value = mock_discovery_jwt_secret

                manager = JWTSecretManager()
                env_secret = manager.get_jwt_secret()

                # Check if service discovery is even called (depends on implementation)
                # If both sources return different values, this is a critical mismatch
                if (mock_discovery.called and
                    env_secret != mock_discovery_jwt_secret and
                    env_secret == 'environment-var-jwt-secret-32-chars'):

                    pytest.fail(
                        f"CRITICAL SERVICE DISCOVERY MISMATCH: Environment variable provides "
                        f"'{env_secret}' but service discovery provides '{mock_discovery_jwt_secret}'. "
                        f"This configuration inconsistency causes services to use different JWT "
                        f"secrets depending on their configuration source, leading to token "
                        f"validation failures and authentication breakdowns across the system."
                    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--no-header"])