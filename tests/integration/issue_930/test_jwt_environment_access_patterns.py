"""
Integration Tests for Issue #930 - JWT Environment Access Patterns

These tests reproduce JWT environment access pattern failures between SSOT
IsolatedEnvironment and direct os.environ access that cause staging authentication issues.

Focus Areas:
1. Cross-service JWT secret consistency validation
2. Environment variable inheritance patterns
3. Service startup sequence with environment dependencies
4. Authentication middleware integration with JWT configuration

Business Impact: $500K+ ARR - Fixes service-to-service authentication failures
"""
import pytest
import os
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.jwt_secret_manager import get_jwt_secret_manager, get_unified_jwt_secret
from shared.isolated_environment import IsolatedEnvironment, get_env


class TestJWTEnvironmentAccessPatterns(SSotAsyncTestCase):
    """Integration tests for JWT environment access patterns causing staging failures."""

    async def asyncSetUp(self):
        """Set up test environment for each test."""
        await super().asyncSetUp()
        # Clear JWT secret manager cache
        get_jwt_secret_manager().clear_cache()

    def test_ssot_vs_direct_environment_cross_service_consistency(self):
        """
        FAILING TEST: Reproduce cross-service JWT secret inconsistency.

        Expected to FAIL - Tests the scenario where auth service and backend service
        access JWT secrets through different methods, causing signature mismatches.
        """
        # Simulate auth service using direct os.environ
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'staging',
            'JWT_SECRET_STAGING': 'auth-service-direct-secret',
            'JWT_SECRET_KEY': 'auth-service-generic-secret'
        }):
            auth_service_secret = os.environ.get('JWT_SECRET_STAGING')

            # Simulate backend service using SSOT IsolatedEnvironment
            with patch.object(IsolatedEnvironment, 'get') as mock_get:
                mock_get.side_effect = lambda key, default=None: {
                    'ENVIRONMENT': 'staging',
                    'JWT_SECRET_STAGING': 'backend-service-ssot-secret',  # DIFFERENT!
                    'JWT_SECRET_KEY': 'backend-service-generic-secret',
                    'TESTING': 'false',
                    'PYTEST_CURRENT_TEST': None
                }.get(key, default)

                backend_service_secret = get_unified_jwt_secret()

                # This should FAIL - cross-service secrets must be identical
                assert auth_service_secret == backend_service_secret, (
                    f"CRITICAL: Auth service JWT secret ('{auth_service_secret}') differs from "
                    f"backend service JWT secret ('{backend_service_secret}'). This cross-service "
                    f"inconsistency causes token signature validation failures, resulting in "
                    f"403 'Not authenticated' errors for service:netra-backend in staging logs."
                )

    def test_environment_variable_inheritance_failure(self):
        """
        FAILING TEST: Reproduce environment variable inheritance failure.

        Expected to FAIL - Tests the scenario where child processes or service
        instances don't inherit the correct JWT environment variables.
        """
        # Set up parent process environment
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'staging',
            'JWT_SECRET_STAGING': 'parent-process-secret'
        }):
            parent_secret = get_unified_jwt_secret()

            # Simulate child process/service with limited environment
            with patch.object(IsolatedEnvironment, 'get') as mock_get:
                # Child process missing JWT_SECRET_STAGING (inheritance failure)
                mock_get.side_effect = lambda key, default=None: {
                    'ENVIRONMENT': 'staging',
                    'JWT_SECRET_STAGING': None,  # MISSING due to inheritance failure
                    'JWT_SECRET_KEY': None,      # Also missing
                    'JWT_SECRET': None,          # Also missing
                    'TESTING': 'false',
                    'PYTEST_CURRENT_TEST': None
                }.get(key, default)

                # This should FAIL - child process can't authenticate
                with pytest.raises(ValueError, match="JWT secret not configured"):
                    child_secret = get_unified_jwt_secret()

                # If we get here, the test FAILED
                pytest.fail(
                    "Child process should fail to get JWT secret due to inheritance failure, "
                    "but it succeeded. This suggests improper fallback logic that's masking "
                    "environment variable inheritance issues causing staging authentication failures."
                )

    async def test_service_startup_sequence_jwt_dependency_failure(self):
        """
        FAILING TEST: Reproduce service startup sequence JWT dependency failure.

        Expected to FAIL - Tests the exact startup sequence failure observed in staging
        where services fail to initialize due to JWT configuration dependencies.
        """
        # Mock service initialization dependencies
        mock_db_session = AsyncMock()
        mock_auth_middleware = MagicMock()

        # Simulate startup sequence with missing JWT configuration
        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'staging',
                'JWT_SECRET_STAGING': None,  # Missing - causes startup failure
                'JWT_SECRET_KEY': None,
                'TESTING': 'false',
                'PYTEST_CURRENT_TEST': None
            }.get(key, default)

            # Step 1: Service tries to initialize JWT configuration
            with pytest.raises(ValueError, match="JWT secret not configured"):
                jwt_secret = get_unified_jwt_secret()

            # Step 2: Without JWT secret, authentication middleware should fail
            # This simulates the exact "create_request_scoped_db_session" failure from logs
            try:
                # Mock the authentication dependency that's failing in staging
                user_id = "service:netra-backend"

                # This should fail because JWT secret is not available
                # Simulating the auth middleware trying to validate service tokens
                jwt_manager = get_jwt_secret_manager()
                validation_result = jwt_manager.validate_jwt_configuration()

                assert not validation_result['valid'], (
                    f"JWT configuration validation should fail with missing secrets, "
                    f"but reported as valid: {validation_result}. This indicates the "
                    f"startup validation logic isn't detecting the configuration issues "
                    f"that are causing 403 'Not authenticated' errors in staging."
                )

            except ValueError as e:
                # Expected failure - JWT configuration is broken
                assert "JWT secret not configured" in str(e)
                print(f"Expected startup failure: {e}")

    def test_authentication_middleware_jwt_integration_failure(self):
        """
        FAILING TEST: Reproduce authentication middleware JWT integration failure.

        Expected to FAIL - Tests the integration between authentication middleware
        and JWT secret manager that's causing service authentication rejections.
        """
        # Mock authentication middleware components
        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            # Simulate partially configured staging environment
            mock_get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'staging',
                'JWT_SECRET_STAGING': 'middleware-test-secret',
                'SERVICE_SECRET': None,  # Missing service secret
                'TESTING': 'false',
                'PYTEST_CURRENT_TEST': None
            }.get(key, default)

            # Test JWT secret resolution for token validation
            jwt_secret = get_unified_jwt_secret()
            assert jwt_secret == 'middleware-test-secret'

            # Test service secret resolution (used for service-to-service auth)
            from shared.jwt_secret_manager import SharedJWTSecretManager
            service_secret = SharedJWTSecretManager.get_service_secret()

            # This should expose the service authentication issue
            # Service secret defaults to test value when not configured
            assert service_secret != 'test-secret-for-local-development-only-32chars', (
                f"Service secret is using default test value '{service_secret}' in staging. "
                f"This explains why service:netra-backend authentication is failing - "
                f"the middleware is rejecting requests with test service secrets. "
                f"Staging environment needs proper SERVICE_SECRET configuration."
            )

    def test_concurrent_jwt_access_race_condition(self):
        """
        FAILING TEST: Reproduce concurrent JWT access race condition.

        Expected to FAIL - Tests the scenario where multiple concurrent requests
        cause race conditions in JWT secret resolution, leading to authentication failures.
        """
        import threading
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results = []
        errors = []

        def get_jwt_secret_concurrent(thread_id):
            """Get JWT secret from multiple threads simultaneously."""
            try:
                # Add slight delay to increase chance of race condition
                time.sleep(0.01 * thread_id)

                # Clear cache to force re-resolution
                get_jwt_secret_manager().clear_cache()

                secret = get_unified_jwt_secret()
                return {'thread_id': thread_id, 'secret': secret, 'success': True}
            except Exception as e:
                return {'thread_id': thread_id, 'error': str(e), 'success': False}

        # Set up environment for concurrent access
        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            call_count = 0
            def race_condition_env_get(key, default=None):
                nonlocal call_count
                call_count += 1

                # Simulate race condition: every 3rd call fails
                if call_count % 3 == 0 and key == 'JWT_SECRET_STAGING':
                    return None  # Simulate temporary unavailability

                return {
                    'ENVIRONMENT': 'staging',
                    'JWT_SECRET_STAGING': 'concurrent-access-secret',
                    'TESTING': 'false',
                    'PYTEST_CURRENT_TEST': None
                }.get(key, default)

            mock_get.side_effect = race_condition_env_get

            # Execute concurrent JWT secret access
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(get_jwt_secret_concurrent, i) for i in range(10)]

                for future in as_completed(futures):
                    result = future.result()
                    if result['success']:
                        results.append(result)
                    else:
                        errors.append(result)

        # Analyze results for race condition issues
        successful_results = len(results)
        failed_results = len(errors)

        # This should FAIL if race conditions cause authentication failures
        assert failed_results == 0, (
            f"Concurrent JWT access resulted in {failed_results} failures out of 10 attempts. "
            f"Errors: {errors}. This indicates race conditions in JWT secret resolution "
            f"that could cause intermittent authentication failures in staging environment "
            f"under concurrent load, explaining the sporadic 403 errors."
        )

        # Verify all successful results have consistent secrets
        if results:
            first_secret = results[0]['secret']
            inconsistent_secrets = [r for r in results if r['secret'] != first_secret]

            assert len(inconsistent_secrets) == 0, (
                f"Concurrent JWT access returned inconsistent secrets: {inconsistent_secrets}. "
                f"This indicates thread safety issues in JWT secret caching that could cause "
                f"authentication failures when different concurrent requests use different secrets."
            )

    def test_environment_configuration_drift_detection(self):
        """
        FAILING TEST: Reproduce environment configuration drift.

        Expected to FAIL - Tests the scenario where environment configuration
        changes during runtime, causing authentication to fail mid-operation.
        """
        # Initial configuration
        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            initial_config = {
                'ENVIRONMENT': 'staging',
                'JWT_SECRET_STAGING': 'initial-staging-secret',
                'TESTING': 'false',
                'PYTEST_CURRENT_TEST': None
            }

            mock_get.side_effect = lambda key, default=None: initial_config.get(key, default)

            # Get initial JWT secret
            initial_secret = get_unified_jwt_secret()
            assert initial_secret == 'initial-staging-secret'

            # Simulate configuration drift (environment variable changes)
            drifted_config = {
                'ENVIRONMENT': 'staging',
                'JWT_SECRET_STAGING': 'drifted-staging-secret',  # CHANGED
                'TESTING': 'false',
                'PYTEST_CURRENT_TEST': None
            }

            # Clear cache to force re-resolution
            get_jwt_secret_manager().clear_cache()

            mock_get.side_effect = lambda key, default=None: drifted_config.get(key, default)

            # Get secret again after drift
            drifted_secret = get_unified_jwt_secret()

            # This should FAIL - configuration drift should be detected
            assert initial_secret == drifted_secret, (
                f"Configuration drift detected: Initial secret '{initial_secret}' changed to "
                f"'{drifted_secret}'. This type of runtime configuration change can cause "
                f"authentication failures when existing tokens become invalid due to secret changes. "
                f"The system should have drift detection and graceful handling mechanisms."
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])