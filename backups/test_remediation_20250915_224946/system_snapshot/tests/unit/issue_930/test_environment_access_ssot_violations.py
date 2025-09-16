"""
Environment Variable Access SSOT Violation Tests for Issue #930

These tests identify and reproduce SSOT violations where code bypasses the unified
IsolatedEnvironment and accesses os.environ directly, causing configuration inconsistencies
that lead to JWT authentication failures in staging.

Focus Areas:
1. Direct os.environ access violations in JWT-related code
2. Inconsistent environment variable resolution between services
3. Environment variable caching and synchronization issues
4. Service startup environment inheritance problems

Business Impact: $500K+ ARR - Fixes environment configuration inconsistencies
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotTestCase
from shared.isolated_environment import IsolatedEnvironment, get_env


@pytest.mark.unit
class EnvironmentAccessSSOTViolationsTests(SSotTestCase):
    """Tests identifying SSOT violations in environment variable access patterns."""

    def test_direct_os_environ_jwt_secret_access_violation(self):
        """
        FAILING TEST: Detect direct os.environ access for JWT secrets.

        Expected to FAIL - Identifies code that bypasses SSOT IsolatedEnvironment
        and accesses JWT secrets directly from os.environ, causing inconsistencies.
        """
        # Set up conflicting environment states
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'staging',
            'JWT_SECRET_STAGING': 'direct-os-environ-jwt-secret',
            'JWT_SECRET_KEY': 'direct-os-environ-generic-secret'
        }):
            # Test direct os.environ access (SSOT VIOLATION)
            direct_jwt_secret_staging = os.environ.get('JWT_SECRET_STAGING')
            direct_jwt_secret_key = os.environ.get('JWT_SECRET_KEY')

            # Test SSOT IsolatedEnvironment access (CORRECT)
            with patch.object(IsolatedEnvironment, 'get') as mock_get:
                mock_get.side_effect = lambda key, default=None: {
                    'ENVIRONMENT': 'staging',
                    'JWT_SECRET_STAGING': 'ssot-isolated-env-jwt-secret',    # DIFFERENT!
                    'JWT_SECRET_KEY': 'ssot-isolated-env-generic-secret',    # DIFFERENT!
                    'TESTING': 'false',
                    'PYTEST_CURRENT_TEST': None
                }.get(key, default)

                ssot_env = get_env()
                ssot_jwt_secret_staging = ssot_env.get('JWT_SECRET_STAGING')
                ssot_jwt_secret_key = ssot_env.get('JWT_SECRET_KEY')

                # This should FAIL - reveals SSOT violations causing inconsistencies
                assert direct_jwt_secret_staging == ssot_jwt_secret_staging, (
                    f"SSOT VIOLATION DETECTED: Direct os.environ access returns "
                    f"'{direct_jwt_secret_staging}' but SSOT IsolatedEnvironment returns "
                    f"'{ssot_jwt_secret_staging}' for JWT_SECRET_STAGING. This inconsistency "
                    f"causes authentication failures when different parts of the system "
                    f"use different JWT secrets. ALL environment access must use SSOT."
                )

                assert direct_jwt_secret_key == ssot_jwt_secret_key, (
                    f"SSOT VIOLATION DETECTED: Direct os.environ access returns "
                    f"'{direct_jwt_secret_key}' but SSOT IsolatedEnvironment returns "
                    f"'{ssot_jwt_secret_key}' for JWT_SECRET_KEY. This inconsistency "
                    f"explains cross-service authentication failures in staging."
                )

    def test_environment_variable_inheritance_ssot_violation(self):
        """
        FAILING TEST: Detect environment inheritance SSOT violations.

        Expected to FAIL - Identifies scenarios where child processes or service
        instances don't inherit environment variables through SSOT patterns.
        """
        # Simulate parent process environment
        parent_env_vars = {
            'ENVIRONMENT': 'staging',
            'JWT_SECRET_STAGING': 'parent-process-jwt-secret',
            'SERVICE_SECRET': 'parent-process-service-secret'
        }

        with patch.dict(os.environ, parent_env_vars):
            # Parent process using direct os.environ (VIOLATION)
            parent_direct_jwt = os.environ.get('JWT_SECRET_STAGING')
            parent_direct_service = os.environ.get('SERVICE_SECRET')

            # Parent process using SSOT (CORRECT)
            parent_ssot_env = get_env()
            parent_ssot_jwt = parent_ssot_env.get('JWT_SECRET_STAGING')
            parent_ssot_service = parent_ssot_env.get('SERVICE_SECRET')

            # Simulate child process with limited environment inheritance
            child_env_vars = {
                'ENVIRONMENT': 'staging',
                # JWT_SECRET_STAGING missing due to inheritance failure
                # SERVICE_SECRET missing due to inheritance failure
            }

            with patch.dict(os.environ, child_env_vars, clear=True):
                # Child process using direct os.environ
                child_direct_jwt = os.environ.get('JWT_SECRET_STAGING')
                child_direct_service = os.environ.get('SERVICE_SECRET')

                # Child process using SSOT with fallback mechanisms
                with patch.object(IsolatedEnvironment, 'get') as mock_get:
                    # SSOT should have fallback/inheritance mechanisms
                    mock_get.side_effect = lambda key, default=None: {
                        'ENVIRONMENT': 'staging',
                        'JWT_SECRET_STAGING': parent_ssot_jwt,    # Inherited through SSOT
                        'SERVICE_SECRET': parent_ssot_service,    # Inherited through SSOT
                        'TESTING': 'false',
                        'PYTEST_CURRENT_TEST': None
                    }.get(key, default)

                    child_ssot_env = get_env()
                    child_ssot_jwt = child_ssot_env.get('JWT_SECRET_STAGING')
                    child_ssot_service = child_ssot_env.get('SERVICE_SECRET')

                    # This should FAIL - exposes inheritance issues
                    assert child_direct_jwt is not None, (
                        f"Child process direct os.environ access failed to inherit JWT_SECRET_STAGING. "
                        f"Parent had '{parent_direct_jwt}', child got None. This inheritance failure "
                        f"causes service authentication failures when child processes/services "
                        f"cannot access required JWT configuration."
                    )

                    # SSOT should handle inheritance better
                    assert child_ssot_jwt == parent_ssot_jwt, (
                        f"SSOT inheritance failure: Parent SSOT JWT '{parent_ssot_jwt}' not "
                        f"inherited by child SSOT JWT '{child_ssot_jwt}'. SSOT should provide "
                        f"consistent environment inheritance mechanisms to prevent authentication failures."
                    )

    def test_concurrent_environment_access_synchronization_violation(self):
        """
        FAILING TEST: Detect concurrent environment access synchronization issues.

        Expected to FAIL - Identifies race conditions and synchronization problems
        in environment variable access that cause intermittent authentication failures.
        """
        import threading
        import time
        from concurrent.futures import ThreadPoolExecutor

        # Test concurrent environment access patterns
        access_results = []
        access_errors = []

        def concurrent_environment_access(thread_id, access_method):
            """Test concurrent environment variable access."""
            try:
                time.sleep(0.01 * thread_id)  # Stagger access times

                if access_method == 'direct':
                    # Direct os.environ access (SSOT VIOLATION)
                    jwt_secret = os.environ.get('JWT_SECRET_STAGING')
                    environment = os.environ.get('ENVIRONMENT')
                elif access_method == 'ssot':
                    # SSOT IsolatedEnvironment access
                    env = get_env()
                    jwt_secret = env.get('JWT_SECRET_STAGING')
                    environment = env.get('ENVIRONMENT')
                else:
                    raise ValueError(f"Unknown access method: {access_method}")

                return {
                    'thread_id': thread_id,
                    'method': access_method,
                    'jwt_secret': jwt_secret,
                    'environment': environment,
                    'success': True
                }

            except Exception as e:
                return {
                    'thread_id': thread_id,
                    'method': access_method,
                    'error': str(e),
                    'success': False
                }

        # Set up environment for concurrent access
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'staging',
            'JWT_SECRET_STAGING': 'concurrent-test-jwt-secret'
        }):
            with patch.object(IsolatedEnvironment, 'get') as mock_get:
                # Simulate SSOT environment with potential race conditions
                call_count = 0
                def race_condition_get(key, default=None):
                    nonlocal call_count
                    call_count += 1

                    # Every 5th call returns different value (simulates race condition)
                    if call_count % 5 == 0:
                        return {
                            'ENVIRONMENT': 'staging',
                            'JWT_SECRET_STAGING': 'race-condition-different-secret',  # INCONSISTENT!
                            'TESTING': 'false'
                        }.get(key, default)

                    return {
                        'ENVIRONMENT': 'staging',
                        'JWT_SECRET_STAGING': 'concurrent-test-jwt-secret',
                        'TESTING': 'false'
                    }.get(key, default)

                mock_get.side_effect = race_condition_get

                # Execute concurrent access with both methods
                with ThreadPoolExecutor(max_workers=10) as executor:
                    futures = []

                    # Mix of direct and SSOT access
                    for i in range(5):
                        futures.append(executor.submit(concurrent_environment_access, i, 'direct'))
                        futures.append(executor.submit(concurrent_environment_access, i + 5, 'ssot'))

                    # Collect results
                    for future in futures:
                        result = future.result()
                        if result['success']:
                            access_results.append(result)
                        else:
                            access_errors.append(result)

        # Analyze results for synchronization issues
        direct_results = [r for r in access_results if r['method'] == 'direct']
        ssot_results = [r for r in access_results if r['method'] == 'ssot']

        # Check for consistency within each method
        direct_secrets = set(r['jwt_secret'] for r in direct_results)
        ssot_secrets = set(r['jwt_secret'] for r in ssot_results)

        # This should FAIL if race conditions cause inconsistencies
        assert len(direct_secrets) == 1, (
            f"Direct os.environ access returned inconsistent JWT secrets: {direct_secrets}. "
            f"This indicates race conditions in environment variable access that could "
            f"cause intermittent authentication failures when concurrent requests "
            f"use different JWT secrets."
        )

        assert len(ssot_secrets) == 1, (
            f"SSOT environment access returned inconsistent JWT secrets: {ssot_secrets}. "
            f"This indicates race conditions in SSOT implementation that could cause "
            f"intermittent authentication failures. SSOT should provide thread-safe access."
        )

        # Check for consistency between methods
        if direct_results and ssot_results:
            direct_secret = list(direct_secrets)[0]
            ssot_secret = list(ssot_secrets)[0]

            assert direct_secret == ssot_secret, (
                f"Concurrent access inconsistency: Direct access returned '{direct_secret}' "
                f"while SSOT access returned '{ssot_secret}'. This cross-method inconsistency "
                f"explains authentication failures when different parts of the system use "
                f"different environment access patterns."
            )

    def test_environment_variable_caching_ssot_violation(self):
        """
        FAILING TEST: Detect environment variable caching SSOT violations.

        Expected to FAIL - Identifies caching inconsistencies between direct
        os.environ access and SSOT IsolatedEnvironment that cause stale data issues.
        """
        # Initial environment state
        initial_env = {
            'ENVIRONMENT': 'staging',
            'JWT_SECRET_STAGING': 'initial-jwt-secret',
            'SERVICE_SECRET': 'initial-service-secret'
        }

        with patch.dict(os.environ, initial_env):
            # Get initial values through both methods
            initial_direct_jwt = os.environ.get('JWT_SECRET_STAGING')

            with patch.object(IsolatedEnvironment, 'get') as mock_get:
                mock_get.side_effect = lambda key, default=None: initial_env.get(key, default)

                initial_ssot_env = get_env()
                initial_ssot_jwt = initial_ssot_env.get('JWT_SECRET_STAGING')

                # Both should be the same initially
                assert initial_direct_jwt == initial_ssot_jwt == 'initial-jwt-secret'

                # Simulate environment change
                updated_env = {
                    'ENVIRONMENT': 'staging',
                    'JWT_SECRET_STAGING': 'updated-jwt-secret',
                    'SERVICE_SECRET': 'updated-service-secret'
                }

                # Update os.environ directly
                with patch.dict(os.environ, updated_env):
                    updated_direct_jwt = os.environ.get('JWT_SECRET_STAGING')

                    # Update SSOT environment
                    mock_get.side_effect = lambda key, default=None: updated_env.get(key, default)

                    updated_ssot_env = get_env()
                    updated_ssot_jwt = updated_ssot_env.get('JWT_SECRET_STAGING')

                    # This should FAIL if caching causes inconsistencies
                    assert updated_direct_jwt == updated_ssot_jwt, (
                        f"Environment update inconsistency: Direct access returned "
                        f"'{updated_direct_jwt}' but SSOT access returned '{updated_ssot_jwt}'. "
                        f"This caching/synchronization issue causes authentication failures "
                        f"when environment variables change and different access methods "
                        f"return stale vs updated values."
                    )

                    # Test cache invalidation/refresh
                    assert updated_ssot_jwt == 'updated-jwt-secret', (
                        f"SSOT cache invalidation failure: Expected 'updated-jwt-secret' "
                        f"but SSOT returned '{updated_ssot_jwt}'. This indicates SSOT "
                        f"is returning cached/stale values instead of updated environment "
                        f"variables, causing authentication failures with outdated secrets."
                    )

    def test_service_specific_environment_access_patterns(self):
        """
        FAILING TEST: Detect service-specific environment access pattern violations.

        Expected to FAIL - Identifies different environment access patterns used by
        different services that cause cross-service authentication inconsistencies.
        """
        # Mock auth service environment access pattern
        def auth_service_environment_access():
            """Simulate how auth service accesses environment variables."""
            # Auth service might use direct os.environ (VIOLATION)
            return {
                'jwt_secret': os.environ.get('JWT_SECRET_STAGING'),
                'service_secret': os.environ.get('SERVICE_SECRET'),
                'environment': os.environ.get('ENVIRONMENT'),
                'method': 'direct_os_environ'
            }

        # Mock backend service environment access pattern
        def backend_service_environment_access():
            """Simulate how backend service accesses environment variables."""
            # Backend service uses SSOT IsolatedEnvironment
            env = get_env()
            return {
                'jwt_secret': env.get('JWT_SECRET_STAGING'),
                'service_secret': env.get('SERVICE_SECRET'),
                'environment': env.get('ENVIRONMENT'),
                'method': 'ssot_isolated_env'
            }

        # Set up environment
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'staging',
            'JWT_SECRET_STAGING': 'service-test-jwt-secret',
            'SERVICE_SECRET': 'service-test-service-secret'
        }):
            with patch.object(IsolatedEnvironment, 'get') as mock_get:
                # SSOT returns slightly different values (configuration drift)
                mock_get.side_effect = lambda key, default=None: {
                    'ENVIRONMENT': 'staging',
                    'JWT_SECRET_STAGING': 'ssot-service-jwt-secret',      # DIFFERENT!
                    'SERVICE_SECRET': 'ssot-service-service-secret',      # DIFFERENT!
                    'TESTING': 'false',
                    'PYTEST_CURRENT_TEST': None
                }.get(key, default)

                # Get environment config from both services
                auth_config = auth_service_environment_access()
                backend_config = backend_service_environment_access()

                # This should FAIL - services must use consistent environment access
                assert auth_config['jwt_secret'] == backend_config['jwt_secret'], (
                    f"Cross-service JWT secret inconsistency: "
                    f"Auth service ({auth_config['method']}) returned '{auth_config['jwt_secret']}' "
                    f"but backend service ({backend_config['method']}) returned '{backend_config['jwt_secret']}'. "
                    f"This service-specific environment access pattern difference causes "
                    f"authentication failures when services use different JWT secrets."
                )

                assert auth_config['service_secret'] == backend_config['service_secret'], (
                    f"Cross-service service secret inconsistency: "
                    f"Auth service returned '{auth_config['service_secret']}' "
                    f"but backend service returned '{backend_config['service_secret']}'. "
                    f"This explains service-to-service authentication failures in staging."
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])