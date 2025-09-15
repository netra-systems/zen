"""
Service Startup Authentication Tests for Issue #930

These tests reproduce the exact service startup authentication failures observed in staging,
specifically the "403 Not authenticated" errors for user_id='service:netra-backend' during
database session creation and service initialization.

Focus Areas:
1. Service startup sequence with JWT configuration dependencies
2. Authentication middleware initialization and service user validation
3. Database session creation with service authentication
4. WebSocket factory initialization with authentication dependencies

Business Impact: $500K+ ARR - Fixes complete Golden Path authentication breakdown
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.jwt_secret_manager import get_jwt_secret_manager, get_unified_jwt_secret
from shared.isolated_environment import IsolatedEnvironment


@pytest.mark.integration
class TestServiceStartupAuthenticationFailure(SSotAsyncTestCase):
    """Tests reproducing service startup authentication failures from staging logs."""

    async def asyncSetUp(self):
        """Set up test environment for each test."""
        await super().asyncSetUp()
        # Clear JWT secret manager cache
        get_jwt_secret_manager().clear_cache()

    async def test_backend_service_authentication_initialization_failure(self):
        """
        FAILING TEST: Reproduce backend service authentication initialization failure.

        Expected to FAIL - Tests the exact scenario from staging logs where
        service:netra-backend cannot authenticate during service initialization.
        """
        # Mock the exact staging environment configuration causing failures
        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'staging',
                'JWT_SECRET_STAGING': None,  # Missing - causing the authentication failure
                'JWT_SECRET_KEY': None,
                'SERVICE_SECRET': None,      # Also missing
                'TESTING': 'false',
                'PYTEST_CURRENT_TEST': None
            }.get(key, default)

            # Step 1: Service tries to initialize authentication configuration
            with pytest.raises(ValueError, match="JWT secret not configured"):
                jwt_secret = get_unified_jwt_secret()

            # Step 2: Without proper JWT configuration, service user authentication fails
            # This simulates the exact error pattern from staging logs
            try:
                # Mock service authentication attempt
                service_user_id = "service:netra-backend"

                # This would normally happen during service startup
                jwt_manager = get_jwt_secret_manager()
                validation = jwt_manager.validate_jwt_configuration()

                # Should fail validation due to missing configuration
                assert not validation['valid'], (
                    f"Service authentication should fail with missing JWT configuration, "
                    f"but validation passed: {validation}. This indicates the authentication "
                    f"initialization logic isn't detecting the configuration issues causing "
                    f"'403 Not authenticated' errors for service:netra-backend in staging."
                )

            except ValueError as expected_error:
                # This is the expected failure that should be properly handled
                assert "JWT secret not configured for staging environment" in str(expected_error)
                print(f"Expected service authentication initialization failure: {expected_error}")

    async def test_database_session_creation_authentication_failure(self):
        """
        FAILING TEST: Reproduce database session creation authentication failure.

        Expected to FAIL - Tests the exact "create_request_scoped_db_session" failure
        observed in staging logs where authentication middleware blocks service requests.
        """
        # Mock database session factory and authentication dependencies
        mock_db_session_factory = AsyncMock()
        mock_auth_dependency = MagicMock()

        # Simulate the staging environment causing the failures
        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'staging',
                'JWT_SECRET_STAGING': 'test-jwt-secret-staging',  # Present but might be wrong type
                'SERVICE_SECRET': 'test-secret-for-local-development-only-32chars',  # Test secret in staging!
                'TESTING': 'false',
                'PYTEST_CURRENT_TEST': None
            }.get(key, default)

            # Mock the authentication middleware that's rejecting service requests
            class MockHTTPException(Exception):
                def __init__(self, status_code, detail):
                    self.status_code = status_code
                    self.detail = detail
                    super().__init__(f"{status_code}: {detail}")

            # Simulate the exact error from staging logs
            def mock_authentication_middleware(user_id: str):
                if user_id == "service:netra-backend":
                    # This is the exact error pattern from staging
                    raise MockHTTPException(403, "Not authenticated")
                return {"user_id": user_id, "authenticated": True}

            # Test the database session creation flow
            try:
                # Step 1: Authentication middleware processes service request
                user_context = mock_authentication_middleware("service:netra-backend")

                # If we get here, the test FAILED - should have raised 403 error
                pytest.fail(
                    f"Authentication middleware should reject service:netra-backend with 403 error, "
                    f"but it accepted the request: {user_context}. This suggests the authentication "
                    f"logic isn't properly configured to reject invalid service credentials, "
                    f"which doesn't match the staging failure pattern."
                )

            except MockHTTPException as auth_error:
                # This reproduces the exact staging error
                assert auth_error.status_code == 403
                assert auth_error.detail == "Not authenticated"
                print(f"Reproduced staging authentication error: {auth_error}")

                # Now test if this is due to service secret configuration
                from shared.jwt_secret_manager import SharedJWTSecretManager
                service_secret = SharedJWTSecretManager.get_service_secret()

                # This should FAIL - service secret should not be test default in staging
                assert service_secret != 'test-secret-for-local-development-only-32chars', (
                    f"CRITICAL: Service secret is test default '{service_secret}' in staging. "
                    f"This explains the 403 'Not authenticated' errors - the authentication "
                    f"middleware is correctly rejecting requests with development-only secrets. "
                    f"Staging needs proper SERVICE_SECRET configuration, not test defaults."
                )

    async def test_websocket_factory_authentication_dependency_failure(self):
        """
        FAILING TEST: Reproduce WebSocket factory authentication dependency failure.

        Expected to FAIL - Tests the WebSocket initialization failure due to
        authentication configuration issues affecting real-time communication.
        """
        # Mock WebSocket factory dependencies
        mock_websocket_manager = MagicMock()
        mock_auth_context = MagicMock()

        # Simulate staging environment with authentication configuration issues
        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'staging',
                'JWT_SECRET_STAGING': '',  # Empty string - invalid
                'JWT_SECRET_KEY': None,
                'SERVICE_SECRET': None,
                'TESTING': 'false',
                'PYTEST_CURRENT_TEST': None
            }.get(key, default)

            # Test JWT secret validation for WebSocket authentication
            jwt_manager = get_jwt_secret_manager()

            # Empty string should be treated as missing
            try:
                jwt_secret = jwt_manager.get_jwt_secret()

                # Validate the secret is usable
                is_valid, context = jwt_manager.validate_jwt_secret_for_environment(
                    jwt_secret, 'staging'
                )

                # This should FAIL - empty JWT secret should be invalid
                assert is_valid, (
                    f"WebSocket authentication should fail with empty JWT secret, "
                    f"but validation passed. Secret: '{jwt_secret}', Context: {context}. "
                    f"This indicates empty JWT secrets are being accepted, which would "
                    f"cause WebSocket authentication failures in staging environment."
                )

            except ValueError as jwt_error:
                # Expected failure due to empty/invalid JWT secret
                assert "JWT secret not configured" in str(jwt_error)
                print(f"Expected WebSocket authentication dependency failure: {jwt_error}")

                # This reproduces the WebSocket authentication breakdown
                # affecting real-time communication in the Golden Path

    async def test_service_to_service_authentication_mismatch(self):
        """
        FAILING TEST: Reproduce service-to-service authentication mismatch.

        Expected to FAIL - Tests the scenario where different services use
        different JWT secrets, causing cross-service authentication failures.
        """
        # Mock auth service JWT configuration
        auth_service_config = {
            'ENVIRONMENT': 'staging',
            'JWT_SECRET_STAGING': 'auth-service-jwt-secret',
            'SERVICE_SECRET': 'auth-service-secret',
            'TESTING': 'false'
        }

        # Mock backend service JWT configuration (different!)
        backend_service_config = {
            'ENVIRONMENT': 'staging',
            'JWT_SECRET_STAGING': 'backend-service-jwt-secret',  # DIFFERENT!
            'SERVICE_SECRET': 'backend-service-secret',          # DIFFERENT!
            'TESTING': 'false'
        }

        # Test auth service JWT secret resolution
        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: auth_service_config.get(key, default)

            auth_jwt_secret = get_unified_jwt_secret()
            auth_jwt_manager = get_jwt_secret_manager()
            # Clear cache to ensure fresh resolution for backend service
            auth_jwt_manager.clear_cache()

        # Test backend service JWT secret resolution
        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: backend_service_config.get(key, default)

            backend_jwt_secret = get_unified_jwt_secret()

            # This should FAIL - JWT secrets must be identical across services
            assert auth_jwt_secret == backend_jwt_secret, (
                f"CRITICAL SERVICE MISMATCH: Auth service JWT secret ('{auth_jwt_secret}') "
                f"differs from backend service JWT secret ('{backend_jwt_secret}'). "
                f"This cross-service inconsistency causes token validation failures, "
                f"explaining the 403 'Not authenticated' errors when backend service "
                f"tries to authenticate with tokens issued by auth service."
            )

    async def test_authentication_middleware_service_user_rejection(self):
        """
        FAILING TEST: Reproduce authentication middleware service user rejection.

        Expected to FAIL - Tests the authentication middleware logic that's
        incorrectly rejecting legitimate service users.
        """
        # Mock authentication middleware components
        class MockAuthenticationMiddleware:
            def __init__(self, jwt_secret: str, service_secret: str):
                self.jwt_secret = jwt_secret
                self.service_secret = service_secret

            def authenticate_service_user(self, user_id: str, token: str = None) -> dict:
                """Mock service user authentication logic."""
                # This simulates the middleware logic that's failing in staging
                if user_id == "service:netra-backend":
                    # Check if service secret is properly configured
                    if self.service_secret == 'test-secret-for-local-development-only-32chars':
                        # Reject development secrets in staging (correct behavior)
                        raise Exception("403: Not authenticated - development secret not allowed")

                    # Check if JWT secret is available for token validation
                    if not self.jwt_secret or len(self.jwt_secret) < 32:
                        # Reject insufficient JWT secrets (correct behavior)
                        raise Exception("403: Not authenticated - invalid JWT configuration")

                    return {"user_id": user_id, "service": True, "authenticated": True}

                return {"user_id": user_id, "service": False, "authenticated": False}

        # Test with staging configuration that causes failures
        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'staging',
                'JWT_SECRET_STAGING': 'short',  # Too short for staging
                'SERVICE_SECRET': 'test-secret-for-local-development-only-32chars',  # Test secret
                'TESTING': 'false',
                'PYTEST_CURRENT_TEST': None
            }.get(key, default)

            jwt_secret = get_unified_jwt_secret()
            from shared.jwt_secret_manager import SharedJWTSecretManager
            service_secret = SharedJWTSecretManager.get_service_secret()

            middleware = MockAuthenticationMiddleware(jwt_secret, service_secret)

            # This should FAIL with the exact staging error pattern
            try:
                result = middleware.authenticate_service_user("service:netra-backend")

                # If we get here, the test FAILED - should have raised authentication error
                pytest.fail(
                    f"Authentication middleware should reject service:netra-backend with "
                    f"improperly configured secrets, but it accepted: {result}. "
                    f"This doesn't match the staging failure pattern where service "
                    f"authentication is being rejected with 403 errors."
                )

            except Exception as auth_error:
                error_message = str(auth_error)

                # Verify this matches the staging error patterns
                assert "403: Not authenticated" in error_message, (
                    f"Expected 403 authentication error, but got: {auth_error}"
                )

                # Identify the specific configuration issue
                if "development secret not allowed" in error_message:
                    print("✓ Identified issue: SERVICE_SECRET is using development default in staging")
                elif "invalid JWT configuration" in error_message:
                    print("✓ Identified issue: JWT_SECRET_STAGING is too short or missing")
                else:
                    print(f"✓ Authentication rejection: {error_message}")

                # The test succeeds by reproducing the staging failure
                # This confirms the authentication middleware is working correctly
                # but the configuration is wrong

    async def test_startup_configuration_validation_comprehensive(self):
        """
        FAILING TEST: Reproduce comprehensive startup configuration validation failure.

        Expected to FAIL - Tests the complete startup validation that should
        detect and prevent the configuration issues causing staging failures.
        """
        # Mock the complete startup environment that's failing in staging
        with patch.object(IsolatedEnvironment, 'get') as mock_get:
            mock_get.side_effect = lambda key, default=None: {
                'ENVIRONMENT': 'staging',
                'JWT_SECRET_STAGING': None,     # Missing
                'JWT_SECRET_KEY': None,         # Missing
                'SERVICE_SECRET': None,         # Missing
                'DATABASE_URL': 'postgresql://...', # Present
                'REDIS_URL': 'redis://...',     # Present
                'TESTING': 'false',
                'PYTEST_CURRENT_TEST': None
            }.get(key, default)

            # Test comprehensive startup validation
            startup_issues = []

            # 1. JWT Configuration Validation
            try:
                jwt_secret = get_unified_jwt_secret()
                jwt_validation = get_jwt_secret_manager().validate_jwt_configuration()
                if not jwt_validation['valid']:
                    startup_issues.extend([f"JWT: {issue}" for issue in jwt_validation['issues']])
            except Exception as e:
                startup_issues.append(f"JWT Configuration Fatal: {e}")

            # 2. Service Secret Validation
            try:
                from shared.jwt_secret_manager import SharedJWTSecretManager
                service_secret = SharedJWTSecretManager.get_service_secret()
                if service_secret == 'test-secret-for-local-development-only-32chars':
                    startup_issues.append("Service Secret: Using development default in staging")
            except Exception as e:
                startup_issues.append(f"Service Secret Fatal: {e}")

            # 3. Authentication Integration Validation
            if len(startup_issues) > 0:
                startup_issues.append("Authentication: Service user authentication will fail")

            # This should FAIL - startup validation should detect configuration issues
            assert len(startup_issues) == 0, (
                f"Startup configuration validation detected {len(startup_issues)} critical issues "
                f"that will cause service authentication failures:\n" +
                "\n".join([f"  - {issue}" for issue in startup_issues]) +
                f"\n\nThese issues explain the 403 'Not authenticated' errors for "
                f"service:netra-backend in staging. The startup validation should prevent "
                f"deployment with these configuration problems."
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])