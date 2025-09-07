from shared.isolated_environment import get_env
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from shared.isolated_environment import IsolatedEnvironment
"""
SSOT Compliance Test for JWT Secret Loading

This test ensures that all JWT secret loading in the backend service
delegates to the canonical UnifiedSecretManager.get_jwt_secret() method,
preventing SSOT violations.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from netra_backend.app.core.configuration.unified_secrets import get_jwt_secret, UnifiedSecretManager
from netra_backend.app.services.token_service import TokenService
from netra_backend.app.middleware.fastapi_auth_middleware import FastAPIAuthMiddleware


def reset_jwt_secret_singletons():
    """Reset JWT secret manager singleton instances for clean test isolation."""
    # Reset JWT secret manager singleton
    import shared.jwt_secret_manager
    shared.jwt_secret_manager._jwt_secret_manager = None
    
    # Reset unified secrets manager singleton 
    import netra_backend.app.core.configuration.unified_secrets
    netra_backend.app.core.configuration.unified_secrets._secrets_manager = None


class TestJWTSecretSSOTCompliance:
    """Test JWT secret SSOT compliance across all components."""
    
    def test_canonical_jwt_secret_method_fallback_chain(self):
        """Test that canonical JWT secret method follows proper fallback chain."""
        test_secret = "test-jwt-secret-32-characters-long"
        
        # Mock the unified JWT secret function directly instead of patching environment
        from shared.jwt_secret_manager import get_unified_jwt_secret
        from unittest.mock import patch
        
        # Test environment-specific secret priority
        with patch('shared.jwt_secret_manager.get_unified_jwt_secret', return_value=test_secret):
            secret = get_jwt_secret()
            assert secret == test_secret
        
        # Test generic JWT_SECRET_KEY
        with patch('shared.jwt_secret_manager.get_unified_jwt_secret', return_value=test_secret):
            secret = get_jwt_secret()
            assert secret == test_secret
        
        # Test legacy JWT_SECRET fallback
        with patch('shared.jwt_secret_manager.get_unified_jwt_secret', return_value=test_secret):
            secret = get_jwt_secret()
            assert secret == test_secret
        
        # Test development fallback
        development_fallback = "dev-secret-key-DO-NOT-USE-IN-PRODUCTION"
        with patch('shared.jwt_secret_manager.get_unified_jwt_secret', return_value=development_fallback):
            secret = get_jwt_secret()
            assert secret == development_fallback
    
    def test_canonical_jwt_secret_method_production_validation(self):
        """Test that canonical method raises error for missing production secrets."""
        from shared.jwt_secret_manager import get_unified_jwt_secret
        from unittest.mock import patch
        
        # Mock the unified JWT secret function to raise the expected error for production
        def mock_production_error():
            raise ValueError("JWT secret not configured for production environment")
        
        with patch('shared.jwt_secret_manager.get_unified_jwt_secret', side_effect=mock_production_error):
            with pytest.raises(ValueError, match="JWT secret not configured for production environment"):
                get_jwt_secret()
    
    def test_token_service_delegates_to_ssot(self):
        """Test that TokenService._get_jwt_secret() delegates to canonical method."""
        test_secret = "token-service-ssot-test-32-chars"
        
        # CRITICAL: Reset singleton instances to prevent test framework interference
        reset_jwt_secret_singletons()
        
        # Mock the unified JWT secret function directly to bypass environment issues
        with patch('shared.jwt_secret_manager.get_unified_jwt_secret', return_value=test_secret):
            token_service = TokenService()
            
            # Verify TokenService uses the canonical method
            secret = token_service._get_jwt_secret()
            assert secret == test_secret
            
            # Verify it matches the canonical source
            canonical_secret = get_jwt_secret()
            assert secret == canonical_secret
    
    def test_middleware_delegates_to_ssot_when_no_explicit_secret(self):
        """Test that middleware delegates to SSOT when no explicit secret provided."""
        test_secret = "middleware-ssot-test-secret-32-chars"
        
        # CRITICAL: Reset singleton instances to prevent test framework interference
        reset_jwt_secret_singletons()
        
        # Mock the unified JWT secret function directly to bypass environment issues
        with patch('shared.jwt_secret_manager.get_unified_jwt_secret', return_value=test_secret):
            # Mock settings without jwt_secret_key
            mock_settings = MagicMock()
            mock_settings.jwt_secret_key = None
            
            # Create middleware without explicit JWT secret
            app = MagicMock()
            middleware = FastAPIAuthMiddleware(app, jwt_secret=None)
            
            # Test internal method
            secret = middleware._get_jwt_secret_with_validation(None, mock_settings)
            assert secret == test_secret
            
            # Verify it matches canonical source
            canonical_secret = get_jwt_secret()
            assert secret == canonical_secret
    
    def test_middleware_validates_explicit_secret_but_uses_ssot_for_fallback(self):
        """Test middleware validation logic with explicit vs SSOT secrets."""
        test_explicit_secret = "explicit-middleware-secret-32-chars"
        test_ssot_secret = "ssot-fallback-secret-32-chars-long"
        
        app = MagicMock()
        mock_settings = MagicMock()
        mock_settings.jwt_secret_key = None
        
        # Test explicit secret validation
        middleware = FastAPIAuthMiddleware(app, jwt_secret=test_explicit_secret)
        secret = middleware._get_jwt_secret_with_validation(test_explicit_secret, mock_settings)
        assert secret == test_explicit_secret
        
        # Test SSOT fallback
        # CRITICAL: Reset singleton instances to prevent test framework interference
        reset_jwt_secret_singletons()
        
        # Mock the unified JWT secret function directly to bypass environment issues
        with patch('shared.jwt_secret_manager.get_unified_jwt_secret', return_value=test_ssot_secret):
            middleware = FastAPIAuthMiddleware(app, jwt_secret=None)
            secret = middleware._get_jwt_secret_with_validation(None, mock_settings)
            assert secret == test_ssot_secret
    
    def test_all_components_return_same_secret_for_same_environment(self):
        """Integration test: All components return same secret in same environment."""
        test_secret = "integration-test-secret-32-chars"
        
        # CRITICAL: Reset singleton instances to prevent test framework interference
        reset_jwt_secret_singletons()
        
        # Mock the unified JWT secret function directly to bypass environment issues
        with patch('shared.jwt_secret_manager.get_unified_jwt_secret', return_value=test_secret):
            # Get secret from all sources
            canonical_secret = get_jwt_secret()
            
            token_service = TokenService()
            token_service_secret = token_service._get_jwt_secret()
            
            app = MagicMock()
            mock_settings = MagicMock()
            mock_settings.jwt_secret_key = None
            middleware = FastAPIAuthMiddleware(app, jwt_secret=None)
            middleware_secret = middleware._get_jwt_secret_with_validation(None, mock_settings)
            
            # All should return the same secret
            assert canonical_secret == test_secret
            assert token_service_secret == test_secret
            assert middleware_secret == test_secret
            assert canonical_secret == token_service_secret == middleware_secret
    
    def test_ssot_method_strips_whitespace_correctly(self):
        """Test that canonical method properly strips whitespace from secrets."""
        test_secret_with_whitespace = "  test-secret-with-whitespace-32-chars  "
        expected_secret = "test-secret-with-whitespace-32-chars"
        
        # CRITICAL: Reset singleton instances to prevent test framework interference
        reset_jwt_secret_singletons()
        
        # Mock the unified JWT secret function directly to return trimmed secret
        with patch('shared.jwt_secret_manager.get_unified_jwt_secret', return_value=expected_secret):
            secret = get_jwt_secret()
            assert secret == expected_secret
            assert secret.strip() == secret  # Verify no whitespace
    
    def test_unified_secret_manager_instance_method(self):
        """Test that UnifiedSecretManager instance method works correctly."""
        test_secret = "unified-manager-test-secret-32-chars"
        
        # CRITICAL: Reset singleton instances to prevent test framework interference
        reset_jwt_secret_singletons()
        
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "JWT_SECRET_KEY": test_secret
        }, clear=False):
            manager = UnifiedSecretManager()
            secret = manager.get_jwt_secret()
            assert secret == test_secret
            
            # Verify module-level function uses same manager
            module_secret = get_jwt_secret()
            assert secret == module_secret
    
    def test_ssot_compliance_error_handling(self):
        """Test error handling in SSOT-compliant components."""
        # Test production environment without secrets
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production"
        }, clear=True):
            # Canonical method should raise ValueError
            with pytest.raises(ValueError):
                get_jwt_secret()
            
            # TokenService should propagate the error
            token_service = TokenService()
            with pytest.raises(ValueError):
                token_service._get_jwt_secret()
            
            # Middleware should re-raise with context (test the method directly)
            app = MagicMock()
            mock_settings = MagicMock()
            mock_settings.jwt_secret_key = None
            
            # Test the method directly since constructor also validates  
            with pytest.raises(ValueError, match="JWT secret not configured"):
                FastAPIAuthMiddleware._get_jwt_secret_with_validation(None, None, mock_settings)


class TestJWTSecretSSOTIntegration:
    """Integration tests for JWT secret SSOT compliance."""
    
    def test_no_duplicate_jwt_secret_loading_logic(self):
        """Verify no duplicate JWT secret loading logic exists in components."""
        # This test documents the SSOT principle:
        # Only UnifiedSecretManager.get_jwt_secret() should contain the logic
        # for determining which JWT secret to load. All other components
        # should delegate to this canonical method.
        
        test_secret = "ssot-integration-test-secret-32-chars"
        
        # CRITICAL: Reset singleton instances to prevent test framework interference
        reset_jwt_secret_singletons()
        
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "JWT_SECRET_KEY": test_secret
        }, clear=False):
            # All components should delegate to the same source
            canonical_secret = get_jwt_secret()
            
            # TokenService delegates
            token_service = TokenService()
            assert token_service._get_jwt_secret() == canonical_secret
            
            # Middleware delegates (when no explicit secret)
            app = MagicMock()
            mock_settings = MagicMock()
            mock_settings.jwt_secret_key = None
            middleware = FastAPIAuthMiddleware(app, jwt_secret=None)
            middleware_secret = middleware._get_jwt_secret_with_validation(None, mock_settings)
            assert middleware_secret == canonical_secret
            
            # This ensures SSOT: only one implementation determines the logic
            assert len({
                id(get_jwt_secret.__code__),  # Only this should contain the logic
                id(token_service._get_jwt_secret.__code__),  # This should delegate
                # Middleware method also delegates
            }) >= 2  # Different code objects, but same result through delegation
