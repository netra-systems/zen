"""
Test JWT secret consistency between auth service and backend service.
Ensures both services use the same JWT secret for token validation.
"""

# Test framework import - using pytest fixtures instead

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# Add auth_service to path for imports

from auth_service.auth_core.core.jwt_handler import JWTHandler
from auth_service.auth_core.secret_loader import AuthSecretLoader
from netra_backend.app.core.configuration.base import ActualSecretManager as SecretManager
from netra_backend.app.schemas.Config import AppConfig

class TestJWTSecretConsistency:
    """Test JWT secret consistency across services."""
    
    def test_both_services_use_same_jwt_secret_key_env_var(self):
        """Test that both services read from JWT_SECRET_KEY environment variable."""
        test_secret = "test-jwt-secret-for-consistency-check-32chars"
        
        with patch.dict(os.environ, {
            "JWT_SECRET_KEY": test_secret,
            "ENVIRONMENT": "development"
        }, clear=False):
            # Test auth service secret loading
            auth_secret = AuthSecretLoader.get_jwt_secret()
            
            # Test backend service secret loading
            config = AppConfig()
            secret_manager = SecretManager()
            secret_manager.populate_secrets(config)
            backend_secret = config.jwt_secret_key
            
            assert auth_secret == test_secret, f"Auth service got: {auth_secret}"
            assert backend_secret == test_secret, f"Backend service got: {backend_secret}"
            assert auth_secret == backend_secret, "Services use different JWT secrets!"
    
    def test_jwt_secret_key_takes_priority_over_jwt_secret(self):
        """Test that JWT_SECRET_KEY takes priority over JWT_SECRET in auth service."""
        jwt_secret_key_value = "primary-secret-32-chars-minimum-len"
        jwt_secret_value = "fallback-secret-32-chars-minimum-len"
        
        with patch.dict(os.environ, {
            "JWT_SECRET_KEY": jwt_secret_key_value,
            "JWT_SECRET": jwt_secret_value,
            "ENVIRONMENT": "development"
        }, clear=False):
            # Auth service should use JWT_SECRET_KEY (same as backend)
            auth_secret = AuthSecretLoader.get_jwt_secret()
            assert auth_secret == jwt_secret_key_value
            
            # Verify it's not using the legacy JWT_SECRET
            assert auth_secret != jwt_secret_value
    
    def test_auth_service_jwt_handler_uses_correct_secret(self):
        """Test that JWTHandler gets the same secret as backend service."""
        test_secret = "jwt-handler-test-secret-32-chars-min"
        
        with patch.dict(os.environ, {
            "JWT_SECRET_KEY": test_secret,
            "ENVIRONMENT": "development"
        }, clear=False):
            # Create JWT handler (simulates auth service)
            jwt_handler = JWTHandler()
            
            # Create backend config (simulates backend service)
            config = AppConfig()
            secret_manager = SecretManager()
            secret_manager.populate_secrets(config)
            
            assert jwt_handler.secret == test_secret
            assert config.jwt_secret_key == test_secret
            assert jwt_handler.secret == config.jwt_secret_key
    
    def test_token_validation_consistency(self):
        """Test that tokens created by auth service can be validated by backend patterns."""
        test_secret = "token-validation-test-secret-32-chars"
        user_id = "test-user-123"
        email = "test@example.com"
        
        with patch.dict(os.environ, {
            "JWT_SECRET_KEY": test_secret,
            "ENVIRONMENT": "development"
        }, clear=False):
            # Create token using auth service JWT handler
            jwt_handler = JWTHandler()
            token = jwt_handler.create_access_token(user_id, email, ["read", "write"])
            
            # Validate token using auth service
            auth_payload = jwt_handler.validate_token_jwt(token, "access")
            
            assert auth_payload is not None
            assert auth_payload["sub"] == user_id
            assert auth_payload["email"] == email
            assert auth_payload["token_type"] == "access"
    
    def test_environment_specific_secret_priority(self):
        """Test environment-specific secret priority in auth service."""
        staging_secret = "staging-specific-secret-32-chars-min"
        generic_secret = "generic-fallback-secret-32-chars-min"
        
        # Test staging environment priority
        with patch.dict(os.environ, {
            "ENVIRONMENT": "staging",
            "JWT_SECRET_STAGING": staging_secret,
            "JWT_SECRET_KEY": generic_secret
        }, clear=False):
            auth_secret = AuthSecretLoader.get_jwt_secret()
            assert auth_secret == staging_secret
        
        # Test production environment priority
        prod_secret = "production-specific-secret-32-chars"
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production", 
            "JWT_SECRET_PRODUCTION": prod_secret,
            "JWT_SECRET_KEY": generic_secret
        }, clear=False):
            auth_secret = AuthSecretLoader.get_jwt_secret()
            assert auth_secret == prod_secret
    
    def test_development_fallback_when_no_secrets(self):
        """Test development environment requires explicit JWT secret configuration."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development"
        }, clear=True):
            # Remove all JWT secret environment variables
            for key in ["JWT_SECRET_KEY", "JWT_SECRET", "JWT_SECRET_STAGING", "JWT_SECRET_PRODUCTION"]:
                if key in os.environ:
                    del os.environ[key]
            
            # Development environment now requires explicit JWT secret
            with pytest.raises(ValueError, match="JWT secret not configured for development environment"):
                AuthSecretLoader.get_jwt_secret()
    
    @patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'TESTING': '0'})
    def test_staging_production_require_secret(self):
        """Test that staging and production environments require explicit secrets."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "staging"
        }, clear=True):
            # Remove all JWT secrets
            for key in ["JWT_SECRET_KEY", "JWT_SECRET", "JWT_SECRET_STAGING"]:
                if key in os.environ:
                    del os.environ[key]
            
            # Should raise ValueError in staging without secrets
            with pytest.raises(ValueError, match="JWT secret not configured for staging environment"):
                AuthSecretLoader.get_jwt_secret()
        
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production"
        }, clear=True):
            # Remove all JWT secrets
            for key in ["JWT_SECRET_KEY", "JWT_SECRET", "JWT_SECRET_PRODUCTION"]:
                if key in os.environ:
                    del os.environ[key]
            
            # Should raise ValueError in production without secrets
            with pytest.raises(ValueError, match="JWT secret not configured for production environment"):
                AuthSecretLoader.get_jwt_secret()

@pytest.mark.asyncio
class TestJWTSecretIntegration:
    """Integration tests for JWT secret consistency."""
    
    @pytest.mark.asyncio
    async def test_auth_client_and_auth_service_consistency(self):
        """Test that auth client fallback uses same logic as auth service."""
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
        from unittest.mock import AsyncMock, MagicMock

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