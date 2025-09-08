"""
Test JWT Secret Synchronization Between Services

CRITICAL: This test validates that auth service and backend service
use IDENTICAL JWT secrets for cross-service authentication.

This test was created to reproduce and verify the fix for the
JWT secret mismatch issue that was causing authentication failures.
"""

import os
import sys
from pathlib import Path
import pytest
from unittest.mock import patch
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.jwt_secret_manager import SharedJWTSecretManager
from shared.isolated_environment import get_env
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient


class TestJWTSecretSynchronization:
    """Test JWT secret consistency across all services."""
    
    def setup_method(self):
        """Setup test environment."""
        # Clear any cached JWT secrets
        SharedJWTSecretManager.clear_cache()
        
    def teardown_method(self):
        """Cleanup after tests."""
        # Clear caches after each test
        SharedJWTSecretManager.clear_cache()
    
    def test_auth_service_uses_shared_jwt_manager(self):
        """Test that auth service correctly uses SharedJWTSecretManager."""
        test_secret = "test-jwt-secret-for-sync-validation-32-chars"
        
        with patch.dict(os.environ, {"JWT_SECRET_KEY": test_secret, "ENVIRONMENT": "development"}):
            # Clear cache to force fresh load
            SharedJWTSecretManager.clear_cache()
            
            # Import auth service config
            from auth_service.auth_core.config import AuthConfig
            
            # Get JWT secret from auth service
            auth_jwt_secret = AuthConfig.get_jwt_secret()
            
            # Should match the SharedJWTSecretManager
            shared_jwt_secret = SharedJWTSecretManager.get_jwt_secret()
            
            assert auth_jwt_secret == shared_jwt_secret, \
                f"Auth service JWT secret mismatch: {auth_jwt_secret} != {shared_jwt_secret}"
            assert auth_jwt_secret == test_secret, \
                f"Auth service not loading test secret: {auth_jwt_secret}"
    
    def test_backend_service_uses_shared_jwt_manager(self):
        """Test that backend service now uses SharedJWTSecretManager after fix."""
        test_secret = "test-backend-jwt-secret-sync-32-chars"
        
        with patch.dict(os.environ, {"JWT_SECRET_KEY": test_secret, "ENVIRONMENT": "development"}):
            # Clear cache to force fresh load
            SharedJWTSecretManager.clear_cache()
            
            # Import backend configuration system
            from netra_backend.app.core.configuration.secrets import SecretManager
            from netra_backend.app.schemas.config import DevelopmentConfig
            
            # Create config and populate secrets
            config = DevelopmentConfig()
            secret_manager = SecretManager()
            secret_manager.populate_secrets(config)
            
            # Backend JWT secret should now come from SharedJWTSecretManager
            backend_jwt_secret = config.jwt_secret_key
            shared_jwt_secret = SharedJWTSecretManager.get_jwt_secret()
            
            assert backend_jwt_secret == shared_jwt_secret, \
                f"Backend JWT secret not using SharedJWTSecretManager: {backend_jwt_secret} != {shared_jwt_secret}"
            assert backend_jwt_secret == test_secret, \
                f"Backend not loading test secret: {backend_jwt_secret}"
    
    def test_cross_service_jwt_secret_synchronization(self):
        """Test that both services use IDENTICAL JWT secrets."""
        test_secret = "cross-service-sync-test-jwt-secret-32"
        
        with patch.dict(os.environ, {"JWT_SECRET_KEY": test_secret, "ENVIRONMENT": "development"}):
            # Clear all caches
            SharedJWTSecretManager.clear_cache()
            
            # Get JWT secret from auth service
            from auth_service.auth_core.config import AuthConfig
            auth_jwt_secret = AuthConfig.get_jwt_secret()
            
            # Get JWT secret from backend service
            from netra_backend.app.core.configuration.secrets import SecretManager
            from netra_backend.app.schemas.config import DevelopmentConfig
            
            config = DevelopmentConfig()
            secret_manager = SecretManager()
            secret_manager.populate_secrets(config)
            backend_jwt_secret = config.jwt_secret_key
            
            # CRITICAL: Both services MUST use identical JWT secrets
            assert auth_jwt_secret == backend_jwt_secret, \
                f"JWT secret mismatch between services! Auth: {auth_jwt_secret}, Backend: {backend_jwt_secret}"
            
            # Both should match the test secret
            assert auth_jwt_secret == test_secret
            assert backend_jwt_secret == test_secret
            
            # Verify they both use SharedJWTSecretManager
            shared_secret = SharedJWTSecretManager.get_jwt_secret()
            assert auth_jwt_secret == shared_secret
            assert backend_jwt_secret == shared_secret
    
    def test_jwt_secret_fallback_in_development(self):
        """Test JWT secret fallback behavior in development environment."""
        # Test with no JWT_SECRET_KEY environment variable
        env_without_jwt = {k: v for k, v in os.environ.items() if not k.startswith('JWT_SECRET')}
        env_without_jwt["ENVIRONMENT"] = "development"
        
        with patch.dict(os.environ, env_without_jwt, clear=True):
            SharedJWTSecretManager.clear_cache()
            
            # Both services should still get a JWT secret (fallback)
            from auth_service.auth_core.config import AuthConfig
            from netra_backend.app.core.configuration.secrets import SecretManager
            from netra_backend.app.schemas.config import DevelopmentConfig
            
            auth_jwt_secret = AuthConfig.get_jwt_secret()
            
            config = DevelopmentConfig()
            secret_manager = SecretManager()
            secret_manager.populate_secrets(config)
            backend_jwt_secret = config.jwt_secret_key
            
            # Both should have some JWT secret (fallback)
            assert auth_jwt_secret is not None
            assert backend_jwt_secret is not None
            assert len(auth_jwt_secret) >= 32
            assert len(backend_jwt_secret) >= 32
            
            # CRITICAL: They should still be identical
            assert auth_jwt_secret == backend_jwt_secret, \
                f"JWT secret fallback mismatch! Auth: {auth_jwt_secret}, Backend: {backend_jwt_secret}"
    
    def test_jwt_secret_production_requirements(self):
        """Test that production environment enforces JWT secret requirements."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True):
            SharedJWTSecretManager.clear_cache()
            
            # Production should require JWT_SECRET_KEY to be set
            with pytest.raises(ValueError, match="JWT secret is REQUIRED in production"):
                SharedJWTSecretManager.get_jwt_secret()
    
    def test_jwt_secret_staging_requirements(self):
        """Test that staging environment enforces JWT secret requirements."""
        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}, clear=True):
            SharedJWTSecretManager.clear_cache()
            
            # Staging should require JWT_SECRET_KEY to be set
            with pytest.raises(ValueError, match="JWT secret is REQUIRED in staging"):
                SharedJWTSecretManager.get_jwt_secret()
    
    def test_shared_jwt_manager_environment_precedence(self):
        """Test SharedJWTSecretManager environment-specific precedence."""
        staging_secret = "staging-specific-jwt-secret-32chars"
        generic_secret = "generic-jwt-secret-for-testing-32"
        
        # Test staging environment precedence
        with patch.dict(os.environ, {
            "ENVIRONMENT": "staging",
            "JWT_SECRET_STAGING": staging_secret,
            "JWT_SECRET_KEY": generic_secret
        }):
            SharedJWTSecretManager.clear_cache()
            
            secret = SharedJWTSecretManager.get_jwt_secret()
            # Should use staging-specific secret, not generic
            assert secret == staging_secret, f"Expected staging secret, got: {secret}"
    
    def test_backend_unified_secrets_compatibility(self):
        """Test that backend UnifiedSecrets also uses SharedJWTSecretManager."""
        test_secret = "unified-secrets-test-jwt-32-chars"
        
        with patch.dict(os.environ, {"JWT_SECRET_KEY": test_secret, "ENVIRONMENT": "development"}):
            SharedJWTSecretManager.clear_cache()
            
            # Test UnifiedSecretManager (should also use SharedJWTSecretManager)
            from netra_backend.app.core.configuration.unified_secrets import get_jwt_secret
            
            unified_jwt_secret = get_jwt_secret()
            shared_jwt_secret = SharedJWTSecretManager.get_jwt_secret()
            
            assert unified_jwt_secret == shared_jwt_secret, \
                f"UnifiedSecrets not using SharedJWTSecretManager: {unified_jwt_secret} != {shared_jwt_secret}"
            assert unified_jwt_secret == test_secret


class TestJWTSecretValidation:
    """Test JWT secret validation and security requirements."""
    
    def test_jwt_secret_minimum_length_validation(self):
        """Test that JWT secrets are validated for minimum length."""
        short_secret = "short"  # Too short
        
        with patch.dict(os.environ, {"JWT_SECRET_KEY": short_secret, "ENVIRONMENT": "production"}):
            SharedJWTSecretManager.clear_cache()
            
            # Should fail in production with short secret
            with pytest.raises(ValueError, match="must be at least 32 characters"):
                SharedJWTSecretManager.get_jwt_secret()
    
    def test_jwt_secret_whitespace_handling(self):
        """Test that JWT secrets handle whitespace correctly."""
        secret_with_whitespace = "  jwt-secret-with-whitespace-32chars  "
        expected_secret = "jwt-secret-with-whitespace-32chars"
        
        with patch.dict(os.environ, {"JWT_SECRET_KEY": secret_with_whitespace, "ENVIRONMENT": "development"}):
            SharedJWTSecretManager.clear_cache()
            
            secret = SharedJWTSecretManager.get_jwt_secret()
            assert secret == expected_secret, f"Whitespace not stripped: '{secret}'"
    
    def test_jwt_secret_caching(self):
        """Test that JWT secrets are properly cached."""
        test_secret = "caching-test-jwt-secret-32-chars"
        
        with patch.dict(os.environ, {"JWT_SECRET_KEY": test_secret, "ENVIRONMENT": "development"}):
            SharedJWTSecretManager.clear_cache()
            
            # First call should load and cache
            secret1 = SharedJWTSecretManager.get_jwt_secret()
            
            # Second call should return cached value
            secret2 = SharedJWTSecretManager.get_jwt_secret()
            
            assert secret1 == secret2 == test_secret
            
            # Cache should work across multiple calls
            for _ in range(5):
                secret = SharedJWTSecretManager.get_jwt_secret()
                assert secret == test_secret


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])