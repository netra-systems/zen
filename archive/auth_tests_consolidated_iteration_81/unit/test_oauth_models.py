"""
Unit tests for OAuth models and validation
Tests Pydantic models used in OAuth flows
"""
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from auth_service.auth_core.models.auth_models import (
    AuthConfigResponse,
    AuthEndpoints,
    AuthProvider,
    LoginRequest,
    LoginResponse,
    TokenResponse,
)
import pytest


@pytest.mark.env_test
class TestAuthProvider:
    """Test AuthProvider enum"""
    
    def test_provider_values(self):
        """Test all provider values are correct"""
        assert AuthProvider.LOCAL == "local"
        assert AuthProvider.GOOGLE == "google"
        assert AuthProvider.GITHUB == "github"
        assert AuthProvider.API_KEY == "api_key"
    
    def test_provider_count(self):
        """Test expected number of providers"""
        providers = list(AuthProvider)
        assert len(providers) == 4

@pytest.mark.env_test
class TestLoginRequest:
    """Test LoginRequest model validation"""
    
    def test_valid_local_login(self):
        """Test valid local login request"""
        request = LoginRequest(
            email="test@example.com",
            password="test_password",
            provider=AuthProvider.LOCAL
        )
        assert request.email == "test@example.com"
        assert request.password == "test_password"
        assert request.provider == AuthProvider.LOCAL
    
    def test_valid_oauth_login(self):
        """Test valid OAuth login request"""
        request = LoginRequest(
            email="test@example.com",
            provider=AuthProvider.GOOGLE,
            oauth_token="oauth_token_123"
        )
        assert request.email == "test@example.com"
        assert request.provider == AuthProvider.GOOGLE
        assert request.oauth_token == "oauth_token_123"
        assert request.password is None
    
    def test_local_login_requires_password(self):
        """Test local login requires password"""
        with pytest.raises(ValidationError) as exc_info:
            LoginRequest(
                email="test@example.com",
                provider=AuthProvider.LOCAL
            )
        
        assert "Password required for local auth" in str(exc_info.value)
    
    def test_invalid_email_format(self):
        """Test invalid email format validation"""
        with pytest.raises(ValidationError):
            LoginRequest(
                email="invalid-email",
                password="test_password",
                provider=AuthProvider.LOCAL
            )

@pytest.mark.env_test
class TestLoginResponse:
    """Test LoginResponse model"""
    
    def test_valid_login_response(self):
        """Test valid login response creation"""
        response = LoginResponse(
            access_token="access_token_123",
            refresh_token="refresh_token_123", 
            expires_in=900,
            user={
                "id": "user_123",
                "email": "test@example.com",
                "name": "Test User"
            }
        )
        
        assert response.access_token == "access_token_123"
        assert response.refresh_token == "refresh_token_123"
        assert response.token_type == "Bearer"
        assert response.expires_in == 900
        assert response.user["id"] == "user_123"

@pytest.mark.env_test
class TestTokenResponse:
    """Test TokenResponse model"""
    
    def test_valid_token_response(self):
        """Test valid token response"""
        response = TokenResponse(
            valid=True,
            user_id="user_123",
            email="test@example.com",
            permissions=["read", "write"],
            expires_at=datetime.now(UTC)
        )
        
        assert response.valid is True
        assert response.user_id == "user_123"
        assert response.email == "test@example.com"
        assert "read" in response.permissions
        assert "write" in response.permissions
    
    def test_invalid_token_response(self):
        """Test invalid token response"""
        response = TokenResponse(valid=False)
        
        assert response.valid is False
        assert response.user_id is None
        assert response.email is None
        assert response.permissions == []

@pytest.mark.env_test
class TestAuthEndpoints:
    """Test AuthEndpoints model"""
    
    def test_required_endpoints(self):
        """Test required endpoints are set"""
        endpoints = AuthEndpoints(
            login="https://auth.example.com/auth/login",
            logout="https://auth.example.com/auth/logout",
            callback="https://app.example.com/auth/callback",
            token="https://auth.example.com/auth/token",
            user="https://auth.example.com/auth/verify"
        )
        
        assert endpoints.login.startswith("https://")
        assert endpoints.logout.startswith("https://")
        assert endpoints.callback.startswith("https://")
        assert endpoints.token.startswith("https://")
        assert endpoints.user.startswith("https://")
    
    def test_optional_endpoints(self):
        """Test optional endpoints can be None"""
        endpoints = AuthEndpoints(
            login="https://auth.example.com/auth/login",
            logout="https://auth.example.com/auth/logout", 
            callback="https://app.example.com/auth/callback",
            token="https://auth.example.com/auth/token",
            user="https://auth.example.com/auth/verify",
            dev_login=None,
            validate_token=None
        )
        
        assert endpoints.dev_login is None
        assert endpoints.validate_token is None

@pytest.mark.env_test
class TestAuthConfigResponse:
    """Test AuthConfigResponse model"""
    
    def test_full_auth_config(self):
        """Test complete auth configuration"""
        endpoints = AuthEndpoints(
            login="https://auth.example.com/auth/login",
            logout="https://auth.example.com/auth/logout",
            callback="https://app.example.com/auth/callback", 
            token="https://auth.example.com/auth/token",
            user="https://auth.example.com/auth/verify"
        )
        
        config = AuthConfigResponse(
            google_client_id="google_client_123",
            endpoints=endpoints,
            development_mode=False,
            authorized_javascript_origins=["https://app.example.com"],
            authorized_redirect_uris=["https://app.example.com/auth/callback"]
        )
        
        assert config.google_client_id == "google_client_123"
        assert config.development_mode is False
        assert len(config.authorized_javascript_origins) == 1
        assert len(config.authorized_redirect_uris) == 1
    
    def test_development_config(self):
        """Test development mode configuration"""
        endpoints = AuthEndpoints(
            login="http://localhost:8081/auth/login",
            logout="http://localhost:8081/auth/logout",
            callback="http://localhost:3000/auth/callback",
            token="http://localhost:8081/auth/token", 
            user="http://localhost:8081/auth/verify",
            dev_login="http://localhost:8081/auth/dev/login"
        )
        
        config = AuthConfigResponse(
            google_client_id="dev_google_client_123",
            endpoints=endpoints,
            development_mode=True,
            authorized_javascript_origins=["http://localhost:3000"],
            authorized_redirect_uris=["http://localhost:3000/auth/callback"]
        )
        
        assert config.development_mode is True
        assert config.endpoints.dev_login is not None
        assert "localhost" in config.authorized_javascript_origins[0]

@pytest.mark.env_test
class TestOAuthStateValidation:
    """Test OAuth state parameter handling"""
    
    def test_state_parameter_length(self):
        """Test state parameter meets security requirements"""
        import secrets
        
        # Generate state like in production
        state = secrets.token_urlsafe(32)
        
        # Should be at least 32 characters for security
        assert len(state) >= 32
        
        # Should be URL safe
        import string
        url_safe_chars = string.ascii_letters + string.digits + '-_'
        assert all(c in url_safe_chars for c in state)
    
    def test_state_uniqueness(self):
        """Test state parameters are unique"""
        import secrets
        
        states = [secrets.token_urlsafe(32) for _ in range(100)]
        
        # All states should be unique
        assert len(set(states)) == 100

if __name__ == "__main__":
    pytest.main([__file__, "-v"])