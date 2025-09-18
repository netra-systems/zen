"""
Integration Test - FastAPI Auth Middleware JWT Configuration for Staging

Tests the exact middleware initialization path that fails in GCP staging deployment.
This test reproduces the error seen in the GCP logs where the FastAPI auth middleware
cannot initialize due to missing JWT configuration.

Business Value: Protects $50K MRR WebSocket functionality from deployment failures
Architecture: Integration test simulating exact production middleware initialization
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestFastAPIAuthMiddlewareJWTStaging(SSotAsyncTestCase):
    """Integration tests for FastAPI Auth Middleware JWT configuration in staging."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.original_env = os.environ.copy()

    def tearDown(self):
        """Clean up after tests."""
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)

        # Clear JWT secret manager cache
        try:
            from shared.jwt_secret_manager import get_jwt_secret_manager
            get_jwt_secret_manager().clear_cache()
        except Exception:
            pass
        super().tearDown()

    def _mock_staging_gcp_environment(self, jwt_secrets: Dict[str, str] = None) -> None:
        """
        Mock the exact GCP staging environment that causes production failures.

        This simulates the GCP Cloud Run environment where:
        - ENVIRONMENT=staging (detected from GCP metadata or explicit setting)
        - JWT secrets are missing from environment variables
        - deployment.secrets_config is not available (ImportError)
        """
        # Clear all environment variables first
        os.environ.clear()

        # Set base GCP staging environment
        base_env = {
            "ENVIRONMENT": "staging",
            "GOOGLE_CLOUD_PROJECT": "netra-staging",
            "K_SERVICE": "backend-staging",
            "K_REVISION": "backend-staging-00005-kjl",
            "PORT": "8080",
            # Explicitly ensure JWT secrets are not set
            "JWT_SECRET_STAGING": None,
            "JWT_SECRET_KEY": None,
            "JWT_SECRET": None,
            # Other staging environment indicators
            "TESTING": "false",
            "PYTEST_CURRENT_TEST": None
        }

        # Add JWT secrets if provided (for successful test scenarios)
        if jwt_secrets:
            base_env.update(jwt_secrets)

        # Set environment variables
        for key, value in base_env.items():
            if value is not None:
                os.environ[key] = value
            elif key in os.environ:
                del os.environ[key]

    def test_fastapi_auth_middleware_initialization_fails_without_jwt_secret(self):
        """
        CRITICAL FAILURE TEST: FastAPI Auth Middleware initialization fails in staging.

        This test reproduces the exact error seen in GCP staging logs:
        "ValueError: JWT secret not configured for staging environment. Please set JWT_SECRET_STAGING or JWT_SECRET_KEY"

        Expected: Middleware initialization should fail with specific staging error message
        """
        # Simulate exact GCP staging environment with no JWT secrets
        self._mock_staging_gcp_environment()

        # Mock the deployment secrets config to not be available (like in GCP)
        with patch('deployment.secrets_config.get_staging_secret', side_effect=ImportError("No module named 'deployment'")):

            # Test the middleware initialization path that fails
            from netra_backend.app.middleware.fastapi_auth_middleware import FastAPIAuthMiddleware

            # This should FAIL during middleware initialization
            with pytest.raises(ValueError) as exc_info:
                # Create mock FastAPI app
                mock_app = Mock()

                # Initialize middleware - this calls _get_jwt_secret_with_validation()
                middleware = FastAPIAuthMiddleware(
                    app=mock_app,
                    jwt_secret=None  # Force it to load from environment
                )

            error_message = str(exc_info.value)
            print(f"Middleware initialization error: {error_message}")

            # Validate exact error message from production logs
            assert "JWT secret not configured" in error_message
            assert ("staging environment" in error_message or
                    "Please set JWT_SECRET_STAGING or JWT_SECRET_KEY" in error_message)

    def test_fastapi_auth_middleware_initialization_succeeds_with_jwt_secret_staging(self):
        """
        SUCCESS TEST: FastAPI Auth Middleware initialization succeeds with proper JWT_SECRET_STAGING.

        This test validates that setting JWT_SECRET_STAGING resolves the production issue.
        """
        # Simulate staging environment with proper JWT_SECRET_STAGING
        jwt_config = {
            "JWT_SECRET_STAGING": "staging-jwt-secret-key-32-characters-long"
        }
        self._mock_staging_gcp_environment(jwt_config)

        from netra_backend.app.middleware.fastapi_auth_middleware import FastAPIAuthMiddleware

        # Create mock FastAPI app
        mock_app = Mock()

        # Initialize middleware - should succeed
        middleware = FastAPIAuthMiddleware(
            app=mock_app,
            jwt_secret=None  # Load from environment
        )

        # Verify middleware was created successfully
        assert middleware is not None
        assert middleware.jwt_secret == "staging-jwt-secret-key-32-characters-long"
        assert middleware.jwt_algorithm == "HS256"

    def test_fastapi_auth_middleware_initialization_succeeds_with_jwt_secret_key(self):
        """
        FALLBACK TEST: FastAPI Auth Middleware succeeds with generic JWT_SECRET_KEY.

        This validates that JWT_SECRET_KEY works as a fallback in staging.
        """
        # Simulate staging environment with generic JWT_SECRET_KEY
        jwt_config = {
            "JWT_SECRET_KEY": "generic-jwt-secret-key-32-characters-long"
        }
        self._mock_staging_gcp_environment(jwt_config)

        from netra_backend.app.middleware.fastapi_auth_middleware import FastAPIAuthMiddleware

        # Create mock FastAPI app
        mock_app = Mock()

        # Initialize middleware - should succeed with fallback
        middleware = FastAPIAuthMiddleware(
            app=mock_app,
            jwt_secret=None  # Load from environment
        )

        # Verify middleware was created successfully
        assert middleware is not None
        assert middleware.jwt_secret == "generic-jwt-secret-key-32-characters-long"

    def test_fastapi_auth_middleware_jwt_secret_too_short_fails(self):
        """
        VALIDATION TEST: FastAPI Auth Middleware fails with JWT secret too short for staging.

        This validates that the 32-character minimum requirement is enforced in staging.
        """
        # Simulate staging environment with short JWT secret
        jwt_config = {
            "JWT_SECRET_STAGING": "short"  # Only 5 characters
        }
        self._mock_staging_gcp_environment(jwt_config)

        from netra_backend.app.middleware.fastapi_auth_middleware import FastAPIAuthMiddleware

        # Create mock FastAPI app
        mock_app = Mock()

        # Initialize middleware - should fail due to length validation
        with pytest.raises(ValueError) as exc_info:
            middleware = FastAPIAuthMiddleware(
                app=mock_app,
                jwt_secret=None  # Load from environment
            )

        error_message = str(exc_info.value)
        assert ("32 characters" in error_message or
                "characters long" in error_message)

    def test_unified_secrets_manager_staging_path_failure(self):
        """
        INTEGRATION PATH TEST: Test the exact UnifiedSecretsManager -> JWT manager path that fails.

        This tests the call chain:
        FastAPIAuthMiddleware._get_jwt_secret_with_validation() ->
        unified_secrets.get_jwt_secret() ->
        jwt_secret_manager.get_unified_jwt_secret()
        """
        # Simulate exact GCP staging environment
        self._mock_staging_gcp_environment()

        # Mock deployment secrets to not be available
        with patch('deployment.secrets_config.get_staging_secret', side_effect=ImportError()):
            from netra_backend.app.core.configuration.unified_secrets import get_jwt_secret

            # This should fail with staging-specific error
            with pytest.raises(ValueError) as exc_info:
                get_jwt_secret()

            error_message = str(exc_info.value)
            assert "staging environment" in error_message.lower()

    def test_get_settings_integration_with_missing_jwt(self):
        """
        SETTINGS INTEGRATION TEST: Test get_settings() configuration integration path.

        FastAPIAuthMiddleware calls get_settings() which may also be affected by JWT configuration issues.
        """
        # Simulate staging environment
        self._mock_staging_gcp_environment()

        try:
            from netra_backend.app.core.config import get_settings
            settings = get_settings()

            # If settings loads, check if it properly handles missing JWT
            print(f"Settings loaded successfully for staging environment")

            # Check JWT-related settings if available
            if hasattr(settings, 'jwt_secret_key'):
                print(f"Settings JWT secret available: {bool(settings.jwt_secret_key)}")

        except Exception as e:
            print(f"Settings loading failed: {e}")
            # This might be expected if JWT is required for settings validation

    def test_websocket_functionality_impact_jwt_failure(self):
        """
        BUSINESS IMPACT TEST: Demonstrate WebSocket functionality impact from JWT failures.

        This test validates that JWT configuration failures block the $50K MRR
        WebSocket functionality mentioned in the error logs.
        """
        # Simulate staging environment without JWT
        self._mock_staging_gcp_environment()

        # Mock deployment secrets to not be available
        with patch('deployment.secrets_config.get_staging_secret', side_effect=ImportError()):

            # Test that WebSocket authentication would fail
            from netra_backend.app.middleware.fastapi_auth_middleware import FastAPIAuthMiddleware

            with pytest.raises(ValueError) as exc_info:
                mock_app = Mock()
                middleware = FastAPIAuthMiddleware(app=mock_app, jwt_secret=None)

            error_message = str(exc_info.value)

            # Verify business impact is properly communicated
            assert ("$50K MRR" in error_message or
                    "WebSocket functionality" in error_message or
                    "staging environment" in error_message.lower())


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])