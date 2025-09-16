"""
Integration Tests for Issue #930 - JWT Secret Environment Access Patterns

These integration tests reproduce the real-world environment variable access patterns
that are failing in the staging deployment, causing JWT authentication failures.

Focus Areas:
1. IsolatedEnvironment vs os.environ consistency across multiple services
2. Environment variable loading during service startup sequences
3. JWT secret resolution across different configuration sources
4. Multi-service JWT secret synchronization scenarios

These tests simulate the actual staging environment configuration patterns
that are causing the authentication failures described in Issue #930.

Business Impact: P0 Critical - $500K MRR WebSocket functionality blocked
Error Pattern: Service startup fails with JWT secret configuration errors
"""

import pytest
import os
import threading
import time
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor
from shared.jwt_secret_manager import JWTSecretManager, get_jwt_secret_manager
from shared.isolated_environment import IsolatedEnvironment, get_env


@pytest.mark.integration
class JWTSecretEnvironmentAccessIntegrationTests:
    """Integration tests for JWT secret environment access patterns in staging."""

    def setup_method(self):
        """Set up clean environment state for each test."""
        # Reset JWT secret manager singleton state
        manager = get_jwt_secret_manager()
        if hasattr(manager, '_cached_secret'):
            manager._cached_secret = None
        if hasattr(manager, '_cached_algorithm'):
            manager._cached_algorithm = None

        # Reset isolated environment state
        env = get_env()
        if hasattr(env, '_env_cache'):
            env._env_cache.clear()
        if hasattr(env, '_isolation_enabled'):
            env._isolation_enabled = False

    def test_staging_environment_variable_loading_sequence_failure(self):
        """
        CRITICAL INTEGRATION: Environment variable loading sequence during service startup.

        This test reproduces the staging environment variable loading pattern that
        occurs during GCP Cloud Run service startup, where variables may not be
        immediately available or may load in unexpected order.

        Expected: SHOULD FAIL - demonstrates environment loading timing issues
        """
        # Simulate staged environment variable loading (as in Cloud Run startup)
        loading_stages = [
            # Stage 1: Only basic system variables available
            {'ENVIRONMENT': None, 'JWT_SECRET_STAGING': None, 'JWT_SECRET_KEY': None},
            # Stage 2: Environment detected but secrets not yet loaded
            {'ENVIRONMENT': 'staging', 'JWT_SECRET_STAGING': None, 'JWT_SECRET_KEY': None},
            # Stage 3: Finally all variables available
            {'ENVIRONMENT': 'staging', 'JWT_SECRET_STAGING': 'final-staging-secret-32-chars-long',
             'JWT_SECRET_KEY': 'backup-secret-also-32-chars-long'}
        ]

        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            stage_index = 0

            def staged_environment_loading(key, default=None):
                nonlocal stage_index
                current_stage = loading_stages[min(stage_index, len(loading_stages) - 1)]
                return current_stage.get(key, default)

            mock_get.side_effect = staged_environment_loading

            manager = JWTSecretManager()

            # Stage 1: Should fail - no environment detected
            try:
                secret = manager.get_jwt_secret()
                if secret:
                    pytest.fail(
                        f"STAGE 1 FAILURE: JWT secret manager returned '{secret}' when no "
                        f"environment variables were loaded. This premature success masks "
                        f"environment loading issues and can cause services to start with "
                        f"wrong JWT configuration before proper secrets are available."
                    )
            except ValueError:
                pass  # Expected during stage 1

            # Stage 2: Should fail - environment known but no secrets
            stage_index = 1
            manager._cached_secret = None  # Clear cache to force reload

            try:
                secret = manager.get_jwt_secret()
                if secret:
                    pytest.fail(
                        f"STAGE 2 FAILURE: JWT secret manager returned '{secret}' in staging "
                        f"environment before JWT secrets were loaded. This timing issue allows "
                        f"service to initialize with incomplete configuration, leading to "
                        f"authentication failures when secrets become available."
                    )
            except ValueError:
                pass  # Expected during stage 2

            # Stage 3: Should succeed with proper secret
            stage_index = 2
            manager._cached_secret = None  # Clear cache to force reload

            secret = manager.get_jwt_secret()
            expected_secret = 'final-staging-secret-32-chars-long'

            if secret != expected_secret:
                pytest.fail(
                    f"STAGE 3 FAILURE: Expected final secret '{expected_secret}' but got '{secret}'. "
                    f"This indicates the environment loading sequence is not properly handled, "
                    f"causing inconsistent JWT secret resolution during Cloud Run startup."
                )

    def test_multi_service_jwt_secret_isolation_failure(self):
        """
        CRITICAL INTEGRATION: Multi-service JWT secret isolation and consistency.

        This test reproduces the scenario where multiple services (backend, auth)
        running concurrently in staging environment get different JWT secrets,
        causing token validation failures between services.

        Expected: SHOULD FAIL - demonstrates multi-service synchronization issues
        """
        # Simulate different services accessing JWT secrets simultaneously
        service_configs = {
            'backend-staging': {
                'ENVIRONMENT': 'staging',
                'SERVICE_ID': 'netra-backend',
                'JWT_SECRET_STAGING': 'backend-sees-this-secret-32-chars',
                'JWT_SECRET_KEY': 'backend-generic-secret-32-chars'
            },
            'auth': {
                'ENVIRONMENT': 'staging',
                'SERVICE_ID': 'netra-auth',
                'JWT_SECRET_STAGING': 'auth-sees-different-secret-32-chars',  # DIFFERENT!
                'JWT_SECRET_KEY': 'auth-generic-secret-also-32-chars'        # DIFFERENT!
            }
        }

        secrets_by_service = {}
        errors_by_service = {}

        def simulate_service_jwt_access(service_name):
            """Simulate a service accessing JWT secrets during startup."""
            try:
                with patch.object(IsolatedEnvironment, 'get') as mock_get:
                    service_config = service_configs[service_name]
                    mock_get.side_effect = lambda key, default=None: service_config.get(key, default)

                    # Each service gets its own JWT manager instance
                    manager = JWTSecretManager()
                    secret = manager.get_jwt_secret()
                    secrets_by_service[service_name] = secret

            except Exception as e:
                errors_by_service[service_name] = str(e)

        # Run services concurrently (as in real staging environment)
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(simulate_service_jwt_access, 'backend-staging'),
                executor.submit(simulate_service_jwt_access, 'auth')
            ]

            # Wait for both services to complete
            for future in futures:
                future.result()

        # Analyze results
        if errors_by_service:
            pytest.fail(
                f"SERVICE ACCESS ERRORS: Some services failed to get JWT secrets: {errors_by_service}"
            )

        backend_secret = secrets_by_service.get('backend-staging')
        auth_secret = secrets_by_service.get('auth')

        # This SHOULD FAIL - services must use identical JWT secrets
        if backend_secret != auth_secret:
            pytest.fail(
                f"CRITICAL MULTI-SERVICE MISMATCH: Backend service got JWT secret '{backend_secret}' "
                f"but auth service got '{auth_secret}'. This causes backend to generate tokens "
                f"with one secret while auth service validates with another, resulting in "
                f"systematic 403 authentication failures across all user requests."
            )

    def test_staging_environment_variable_precedence_failure(self):
        """
        CRITICAL INTEGRATION: Environment variable precedence across multiple sources.

        This test reproduces the staging scenario where JWT secrets are available
        from multiple sources (os.environ, Cloud Run config, secrets manager)
        but wrong precedence order causes incorrect secret selection.

        Expected: SHOULD FAIL - demonstrates precedence order issues
        """
        # Set up multiple JWT secret sources with different values
        os_environ_secret = "os-environ-jwt-secret-32-characters"
        cloud_run_secret = "cloud-run-config-jwt-secret-32-chars"
        secrets_manager_secret = "secrets-manager-jwt-secret-32-chars"

        with patch.dict(os.environ, {
            'ENVIRONMENT': 'staging',
            'JWT_SECRET_STAGING': os_environ_secret,  # Direct os.environ
            'GCP_PROJECT_ID': 'netra-staging'
        }):
            with patch.object(IsolatedEnvironment, 'get') as mock_get:
                # Simulate Cloud Run environment config (different value)
                mock_get.side_effect = lambda key, default=None: {
                    'ENVIRONMENT': 'staging',
                    'JWT_SECRET_STAGING': cloud_run_secret,  # Cloud Run config value
                    'JWT_SECRET_KEY': 'cloud-run-generic-secret-32-chars',
                    'GCP_PROJECT_ID': 'netra-staging'
                }.get(key, default)

                # Mock secrets manager (third different value)
                with patch('shared.jwt_secret_manager.get_staging_secret') as mock_secrets:
                    mock_secrets.return_value = secrets_manager_secret

                    manager = JWTSecretManager()
                    selected_secret = manager.get_jwt_secret()

                    # Analyze which source was actually used
                    secret_sources = {
                        os_environ_secret: "os.environ direct access",
                        cloud_run_secret: "Cloud Run environment config",
                        secrets_manager_secret: "GCP Secrets Manager"
                    }

                    selected_source = secret_sources.get(selected_secret, "UNKNOWN SOURCE")

                    # Check for precedence consistency
                    # The exact precedence order should be documented and consistent
                    if selected_secret not in secret_sources:
                        pytest.fail(
                            f"CRITICAL PRECEDENCE FAILURE: JWT secret '{selected_secret}' doesn't "
                            f"match any known source. Available sources: {secret_sources}. "
                            f"This indicates improper secret resolution that could pick "
                            f"arbitrary values, causing unpredictable authentication behavior."
                        )

                    # Verify precedence consistency across multiple calls
                    manager._cached_secret = None  # Force reload
                    second_secret = manager.get_jwt_secret()

                    if selected_secret != second_secret:
                        pytest.fail(
                            f"CRITICAL PRECEDENCE INCONSISTENCY: First call returned '{selected_secret}' "
                            f"from {selected_source}, but second call returned '{second_secret}'. "
                            f"This precedence inconsistency causes different parts of the same "
                            f"service to use different JWT secrets, breaking authentication."
                        )

    def test_staging_environment_caching_invalidation_failure(self):
        """
        CRITICAL INTEGRATION: Environment variable caching invalidation during updates.

        This test reproduces the staging scenario where environment variables are
        updated (e.g., via configuration deployment) but cached values persist,
        causing services to use stale JWT secrets.

        Expected: SHOULD FAIL - demonstrates caching invalidation issues
        """
        # Initial staging configuration
        initial_secret = "initial-staging-jwt-secret-32-chars"
        updated_secret = "updated-staging-jwt-secret-32-chars"

        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            # Phase 1: Initial configuration
            mock_get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'staging',
                'JWT_SECRET_STAGING': initial_secret,
                'GCP_PROJECT_ID': 'netra-staging'
            }.get(key, default)

            manager = JWTSecretManager()
            first_secret = manager.get_jwt_secret()

            assert first_secret == initial_secret

            # Phase 2: Configuration updated (simulate deployment config change)
            mock_get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'staging',
                'JWT_SECRET_STAGING': updated_secret,  # Configuration updated
                'GCP_PROJECT_ID': 'netra-staging'
            }.get(key, default)

            # Get secret again - should pick up new configuration
            second_secret = manager.get_jwt_secret()

            # This SHOULD FAIL if caching prevents updates
            if second_secret == initial_secret:
                pytest.fail(
                    f"CRITICAL CACHING FAILURE: JWT secret manager returned cached value "
                    f"'{second_secret}' instead of updated configuration '{updated_secret}'. "
                    f"This caching issue prevents services from picking up updated JWT "
                    f"configuration, causing authentication failures when secrets are rotated "
                    f"or updated in staging environment."
                )

            # Phase 3: Clear cache and verify proper reload
            manager._cached_secret = None
            third_secret = manager.get_jwt_secret()

            if third_secret != updated_secret:
                pytest.fail(
                    f"CRITICAL CACHE INVALIDATION FAILURE: Even after clearing cache, "
                    f"got '{third_secret}' instead of updated '{updated_secret}'. This "
                    f"indicates the environment variable layer is not properly refreshing, "
                    f"causing persistent use of stale JWT secrets."
                )

    def test_staging_concurrent_service_startup_race_condition(self):
        """
        CRITICAL INTEGRATION: Concurrent service startup race conditions.

        This test reproduces the staging scenario where multiple services start
        simultaneously and compete for JWT secret initialization, potentially
        causing race conditions in secret resolution.

        Expected: SHOULD FAIL - demonstrates race condition issues
        """
        # Shared state to track concurrent access patterns
        access_log = []
        access_lock = threading.Lock()

        def log_access(service_name, action, value):
            with access_lock:
                access_log.append({
                    'service': service_name,
                    'action': action,
                    'value': value,
                    'timestamp': time.time()
                })

        def simulate_concurrent_service_startup(service_name):
            """Simulate a service starting up and accessing JWT secrets."""
            try:
                log_access(service_name, 'startup_begin', None)

                with patch.object(IsolatedEnvironment, 'get') as mock_get:
                    # Simulate slight timing variations in environment loading
                    if service_name == 'backend-staging':
                        time.sleep(0.01)  # Backend starts slightly later

                    mock_get.side_effect = lambda key, default=None: {
                        'ENVIRONMENT': 'staging',
                        'SERVICE_ID': service_name,
                        'JWT_SECRET_STAGING': f'shared-staging-secret-for-{service_name}-32chars',
                        'GCP_PROJECT_ID': 'netra-staging'
                    }.get(key, default)

                    log_access(service_name, 'environment_loaded', None)

                    # Each service gets its own JWT manager instance
                    manager = JWTSecretManager()
                    log_access(service_name, 'manager_created', None)

                    secret = manager.get_jwt_secret()
                    log_access(service_name, 'secret_loaded', secret)

                    return secret

            except Exception as e:
                log_access(service_name, 'error', str(e))
                raise

        # Start multiple services concurrently
        services = ['backend-staging', 'auth', 'websocket-staging']
        secrets = {}

        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_service = {
                executor.submit(simulate_concurrent_service_startup, service): service
                for service in services
            }

            for future in future_to_service:
                service = future_to_service[future]
                try:
                    secrets[service] = future.result()
                except Exception as e:
                    pytest.fail(f"Service {service} failed during concurrent startup: {e}")

        # Analyze concurrent access patterns
        unique_secrets = set(secrets.values())

        # All services should get the same JWT secret (or at least consistent ones)
        if len(unique_secrets) > 1:
            pytest.fail(
                f"CRITICAL RACE CONDITION: Concurrent service startup resulted in different "
                f"JWT secrets: {secrets}. Access log: {access_log}. This race condition "
                f"causes services to use different JWT secrets, leading to token validation "
                f"failures and authentication breakdowns across the system."
            )

        # Check for proper initialization order
        error_logs = [log for log in access_log if log['action'] == 'error']
        if error_logs:
            pytest.fail(
                f"CONCURRENT STARTUP ERRORS: {error_logs}. Concurrent service startup "
                f"should not cause errors in JWT secret resolution."
            )

    def test_staging_environment_isolation_boundary_failure(self):
        """
        CRITICAL INTEGRATION: Environment isolation boundary violations.

        This test reproduces the staging scenario where environment isolation
        boundaries are not properly maintained, causing JWT secrets to leak
        between different service contexts or configurations.

        Expected: SHOULD FAIL - demonstrates isolation boundary violations
        """
        # Test environment isolation across different service configurations
        service_a_env = get_env()
        service_b_env = get_env()  # Should be same singleton but with isolation

        # Enable isolation for service A
        service_a_env.enable_isolation()
        service_a_env.set('ENVIRONMENT', 'staging', 'service_a')
        service_a_env.set('JWT_SECRET_STAGING', 'service-a-secret-32-chars-long', 'service_a')
        service_a_env.set('SERVICE_ID', 'service-a', 'service_a')

        # Service A gets JWT secret
        manager_a = JWTSecretManager()
        secret_a = manager_a.get_jwt_secret()

        # Enable isolation for service B (simulate different service context)
        service_b_env.enable_isolation()
        service_b_env.set('ENVIRONMENT', 'staging', 'service_b')
        service_b_env.set('JWT_SECRET_STAGING', 'service-b-secret-32-chars-long', 'service_b')
        service_b_env.set('SERVICE_ID', 'service-b', 'service_b')

        # Service B gets JWT secret
        manager_b = JWTSecretManager()
        secret_b = manager_b.get_jwt_secret()

        # Clear caches to test isolation
        manager_a._cached_secret = None
        manager_b._cached_secret = None

        # Get secrets again to test isolation persistence
        secret_a_reload = manager_a.get_jwt_secret()
        secret_b_reload = manager_b.get_jwt_secret()

        # Clean up isolation
        service_a_env.disable_isolation()
        service_b_env.disable_isolation()

        # This SHOULD FAIL if isolation boundaries are violated
        if secret_a == secret_b:
            pytest.fail(
                f"CRITICAL ISOLATION FAILURE: Both services got identical JWT secret "
                f"'{secret_a}' despite different isolated configurations. This isolation "
                f"violation causes services to share JWT secrets when they should be "
                f"independent, leading to security issues and authentication confusion."
            )

        if secret_a != secret_a_reload or secret_b != secret_b_reload:
            pytest.fail(
                f"CRITICAL ISOLATION PERSISTENCE FAILURE: Service A secret changed from "
                f"'{secret_a}' to '{secret_a_reload}' or Service B changed from '{secret_b}' "
                f"to '{secret_b_reload}'. This indicates isolation boundaries are not "
                f"properly maintained, causing configuration contamination between services."
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--no-header"])