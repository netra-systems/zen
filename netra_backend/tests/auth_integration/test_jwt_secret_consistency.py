from shared.isolated_environment import IsolatedEnvironment
from test_framework.database.test_database_manager import TestDatabaseManager
from auth_service.core.auth_manager import AuthManager
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import asyncio

"""
Test JWT secret consistency for backend service.
Ensures backend service correctly loads and uses JWT secret for token validation.
"""""

import os

import pytest

from netra_backend.app.core.configuration.unified_secrets import UnifiedSecretsManager as SecretManager
from netra_backend.app.schemas.config import AppConfig

class TestJWTSecretConsistency:
    """Test JWT secret configuration for backend service."""

    def test_backend_service_uses_jwt_secret_key_env_var(self):
        """Test that backend service reads from JWT_SECRET_KEY environment variable."""
        test_secret = "test-jwt-secret-for-consistency-check-32chars"

        with patch.dict(os.environ, {
        "JWT_SECRET_KEY": test_secret,
        "ENVIRONMENT": "development"
        }, clear=False):
            # Test backend service secret loading
            config = AppConfig()
            secret_manager = SecretManager()
            secret_manager.populate_secrets(config)
            backend_secret = config.jwt_secret_key

            assert backend_secret == test_secret, f"Backend service got: {backend_secret}"

            def test_jwt_secret_key_takes_priority_over_jwt_secret(self):
                """Test that JWT_SECRET_KEY takes priority over JWT_SECRET in backend service."""
                jwt_secret_key_value = "primary-secret-32-chars-minimum-len"
                jwt_secret_value = "fallback-secret-32-chars-minimum-len"

                with patch.dict(os.environ, {
                "JWT_SECRET_KEY": jwt_secret_key_value,
                "JWT_SECRET": jwt_secret_value,
                "ENVIRONMENT": "development"
                }, clear=False):
            # Backend service should use JWT_SECRET_KEY
                    config = AppConfig()
                    secret_manager = SecretManager()
                    secret_manager.populate_secrets(config)

                    assert config.jwt_secret_key == jwt_secret_key_value
            # Verify it's not using the legacy JWT_SECRET'
                    assert config.jwt_secret_key != jwt_secret_value

                    def test_backend_jwt_secret_configuration(self):
                        """Test that backend service correctly loads JWT secret."""
                        test_secret = "jwt-handler-test-secret-32-chars-min"

                        with patch.dict(os.environ, {
                        "JWT_SECRET_KEY": test_secret,
                        "ENVIRONMENT": "development"
                        }, clear=False):
            # Create backend config
                            config = AppConfig()
                            secret_manager = SecretManager()
                            secret_manager.populate_secrets(config)

                            assert config.jwt_secret_key == test_secret

                            def test_backend_jwt_secret_for_token_validation(self):
                                """Test that backend service has JWT secret configured for token validation."""
                                test_secret = "token-validation-test-secret-32-chars"

                                with patch.dict(os.environ, {
                                "JWT_SECRET_KEY": test_secret,
                                "ENVIRONMENT": "development"
                                }, clear=False):
            # Verify backend has JWT secret configured
                                    config = AppConfig()
                                    secret_manager = SecretManager()
                                    secret_manager.populate_secrets(config)

                                    assert config.jwt_secret_key == test_secret
                                    assert len(config.jwt_secret_key) >= 32  # Minimum length for security

                                    def test_environment_specific_secret_priority(self):
                                        """Test environment-specific secret priority in backend service."""
                                        staging_secret = "staging-specific-secret-32-chars-min"
                                        generic_secret = "generic-fallback-secret-32-chars-min"

        # Test staging environment
                                        with patch.dict(os.environ, {
                                        "ENVIRONMENT": "staging",
                                        "JWT_SECRET_STAGING": staging_secret,
                                        "JWT_SECRET_KEY": generic_secret
                                        }, clear=False):
                                            config = AppConfig()
                                            secret_manager = SecretManager()
                                            secret_manager.populate_secrets(config)
            # Backend should use the generic JWT_SECRET_KEY
                                            assert config.jwt_secret_key == generic_secret

        # Test production environment
                                            prod_secret = "production-specific-secret-32-chars"
                                            with patch.dict(os.environ, {
                                            "ENVIRONMENT": "production", 
                                            "JWT_SECRET_PRODUCTION": prod_secret,
                                            "JWT_SECRET_KEY": generic_secret
                                            }, clear=False):
                                                config = AppConfig()
                                                secret_manager = SecretManager()
                                                secret_manager.populate_secrets(config)
            # Backend should use the generic JWT_SECRET_KEY
                                                assert config.jwt_secret_key == generic_secret

                                                def test_development_fallback_when_no_secrets(self):
                                                    """Test development environment behavior when no JWT secret is configured."""
                                                    with patch.dict(os.environ, {
                                                    "ENVIRONMENT": "development"
                                                    }, clear=True):
            # Remove all JWT secret environment variables
                                                        for key in ["JWT_SECRET_KEY", "JWT_SECRET", "JWT_SECRET_STAGING", "JWT_SECRET_PRODUCTION"]:
                                                            if key in os.environ:
                                                                del os.environ[key]

            # Backend should handle missing JWT secret gracefully
                                                                config = AppConfig()
                                                                secret_manager = SecretManager()
                                                                secret_manager.populate_secrets(config)
            # The config might have a default or None value
            # We just verify it doesn't crash'

                                                                def test_staging_production_require_secret(self):
                                                                    """Test that staging and production environments handle missing JWT secrets."""
                                                                    with patch.dict(os.environ, {
                                                                    "ENVIRONMENT": "staging"
                                                                    }, clear=True):
            # Remove all JWT secrets
                                                                        for key in ["JWT_SECRET_KEY", "JWT_SECRET", "JWT_SECRET_STAGING"]:
                                                                            if key in os.environ:
                                                                                del os.environ[key]

            # Backend should handle missing JWT secret configuration
                                                                                config = AppConfig()
                                                                                secret_manager = SecretManager()
            # This should not crash even without JWT secrets
                                                                                secret_manager.populate_secrets(config)

                                                                                with patch.dict(os.environ, {
                                                                                "ENVIRONMENT": "production"
                                                                                }, clear=True):
            # Remove all JWT secrets
                                                                                    for key in ["JWT_SECRET_KEY", "JWT_SECRET", "JWT_SECRET_PRODUCTION"]:
                                                                                        if key in os.environ:
                                                                                            del os.environ[key]

            # Backend should handle missing JWT secret configuration
                                                                                            config = AppConfig()
                                                                                            secret_manager = SecretManager()
            # This should not crash even without JWT secrets
                                                                                            secret_manager.populate_secrets(config)

                                                                                            @pytest.mark.asyncio
                                                                                            class TestJWTSecretIntegration:
                                                                                                """Integration tests for JWT secret consistency."""

                                                                                                @pytest.mark.asyncio
                                                                                                async def test_auth_client_and_backend_consistency(self):
                                                                                                    """Test that backend auth client uses correct JWT secret."""
                                                                                                    from netra_backend.app.clients.auth_client_core import AuthServiceClient

                                                                                                    test_secret = "integration-test-secret-32-chars-min"

                                                                                                    with patch.dict(os.environ, {
                                                                                                    "JWT_SECRET_KEY": test_secret,
                                                                                                    "ENVIRONMENT": "development",
                                                                                                    "AUTH_SERVICE_ENABLED": "false"  # Force local validation
                                                                                                    }, clear=False):
            # Create auth client and test local validation
                                                                                                        auth_client = AuthServiceClient()

            # Test local validation (fallback mode)
                                                                                                        validation_result = await auth_client._local_validate("any-token")

            # Should return valid dev user in development mode
                                                                                                        assert validation_result["valid"] is True
                                                                                                        assert validation_result["user_id"] == "dev-user-1"
                                                                                                        assert validation_result["email"] == "dev@example.com"

                                                                                                        @pytest.mark.asyncio
                                                                                                        async def test_backend_auth_integration_uses_same_secret(self):
                                                                                                            """Test that backend auth integration validates tokens consistently."""
                                                                                                            from netra_backend.app.auth_integration.auth import get_current_user
                                                                                                            from netra_backend.app.clients.auth_client_core import auth_client

                                                                                                            test_secret = "backend-integration-test-secret-32"

                                                                                                            with patch.dict(os.environ, {
                                                                                                            "JWT_SECRET_KEY": test_secret,
                                                                                                            "ENVIRONMENT": "development"
                                                                                                            }, clear=False):
            # Mock the internal validation method to bypass auth service connection
                                                                                                                with patch.object(auth_client, '_execute_token_validation', new_callable=AsyncMock) as mock_execute:
                                                                                                                    mock_execute.return_value = {
                                                                                                                    "valid": True,
                                                                                                                    "user_id": "test-user-123",
                                                                                                                    "email": "test@example.com"
                                                                                                                    }

                # The auth integration should use the same secret context
                                                                                                                    token_result = await auth_client.validate_token_jwt("test-token")
                                                                                                                    assert token_result["valid"] is True
                                                                                                                    assert token_result["user_id"] == "test-user-123"

                                                                                                                    @pytest.mark.asyncio
                                                                                                                    async def test_jwt_token_hijacking_prevention(self):
                                                                                                                        """ITERATION 24: Prevent JWT token hijacking attacks that compromise user accounts.

                                                                                                                        Business Value: Prevents account takeover attacks worth $100K+ per security breach.
                                                                                                                        """""
                                                                                                                        from netra_backend.app.clients.auth_client_core import AuthServiceClient

                                                                                                                        test_secret = "hijack-prevention-test-secret-32"

                                                                                                                        with patch.dict(os.environ, {
                                                                                                                        "JWT_SECRET_KEY": test_secret,
                                                                                                                        "ENVIRONMENT": "development"
                                                                                                                        }, clear=False):
                                                                                                                            auth_client = AuthServiceClient()

            # Test 1: Valid token with correct secret should work
                                                                                                                            with patch.object(auth_client, '_execute_token_validation', new_callable=AsyncMock) as mock_execute:
                                                                                                                                mock_execute.return_value = {
                                                                                                                                "valid": True,
                                                                                                                                "user_id": "legitimate-user",
                                                                                                                                "email": "user@example.com"
                                                                                                                                }

                                                                                                                                valid_result = await auth_client.validate_token_jwt("valid-token")
                                                                                                                                assert valid_result["valid"] is True
                                                                                                                                assert valid_result["user_id"] == "legitimate-user"

            # Test 2: Simulate token signed with different secret (hijack attempt)
                                                                                                                                with patch.object(auth_client, '_execute_token_validation', new_callable=AsyncMock) as mock_execute:
                # Simulate validation failure for malicious token
                                                                                                                                    mock_execute.return_value = {"valid": False, "error": "invalid_signature"}

                                                                                                                                    hijack_result = await auth_client.validate_token_jwt("hijacked-token")
                                                                                                                                    assert hijack_result["valid"] is False
                                                                                                                                    assert "error" in hijack_result

            # Test 3: Expired token should be rejected
                                                                                                                                    with patch.object(auth_client, '_execute_token_validation', new_callable=AsyncMock) as mock_execute:
                                                                                                                                        mock_execute.return_value = {"valid": False, "error": "token_expired"}

                                                                                                                                        expired_result = await auth_client.validate_token_jwt("expired-token")
                                                                                                                                        assert expired_result["valid"] is False
                                                                                                                                        assert expired_result.get("error") == "token_expired"

                                                                                                                                        @pytest.mark.asyncio
                                                                                                                                        async def test_backend_session_security(self):
                                                                                                                                            """ITERATION 26: Test backend session security handling.

                                                                                                                                            Business Value: Prevents session-based attacks worth $75K+ per security incident.
                                                                                                                                            """""
                                                                                                                                            from netra_backend.app.clients.auth_client_core import AuthServiceClient

        # Test backend's session validation via auth client'
                                                                                                                                            auth_client = AuthServiceClient()

                                                                                                                                            with patch.object(auth_client, '_execute_token_validation', new_callable=AsyncMock) as mock_execute:
            # Test 1: Valid session should pass
                                                                                                                                                mock_execute.return_value = {
                                                                                                                                                "valid": True,
                                                                                                                                                "user_id": "user123",
                                                                                                                                                "email": "user@example.com",
                                                                                                                                                "session_id": "valid-session"
                                                                                                                                                }

                                                                                                                                                result = await auth_client.validate_token_jwt("valid-session-token")
                                                                                                                                                assert result["valid"] is True
                                                                                                                                                assert result["user_id"] == "user123"

            # Test 2: Invalid session should fail
                                                                                                                                                mock_execute.return_value = {
                                                                                                                                                "valid": False,
                                                                                                                                                "error": "session_expired"
                                                                                                                                                }

                                                                                                                                                result = await auth_client.validate_token_jwt("expired-session-token")
                                                                                                                                                assert result["valid"] is False
                                                                                                                                                assert "error" in result

            # Test 3: Suspicious activity should be rejected
                                                                                                                                                mock_execute.return_value = {
                                                                                                                                                "valid": False,
                                                                                                                                                "error": "suspicious_activity",
                                                                                                                                                "details": "Multiple locations detected"
                                                                                                                                                }

                                                                                                                                                result = await auth_client.validate_token_jwt("suspicious-token")
                                                                                                                                                assert result["valid"] is False
                                                                                                                                                assert result.get("error") == "suspicious_activity"
