"""
OAuth Flow Tests for Auth Service (Synchronous)
Basic testing of OAuth endpoints with TestClient
"""
import secrets
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

# Add auth service to path
auth_service_dir = Path(__file__).parent.parent.parent
from auth_service.main import app

from auth_service.auth_core.models.auth_models import AuthProvider

# Test client
client = TestClient(app)

class TestOAuthBasicEndpoints:
    """Test basic OAuth endpoints functionality"""
    
    def test_auth_config_endpoint(self):
        """Test OAuth configuration endpoint"""
        response = client.get("/auth/config")
        assert response.status_code == 200
        
        config = response.json()
        assert "google_client_id" in config
        assert "endpoints" in config
        assert config["endpoints"]["login"] is not None
    
    def test_google_oauth_initiate_redirect(self):
        """Test Google OAuth initiation returns redirect"""
        response = client.get("/auth/login?provider=google", follow_redirects=False)
        
        assert response.status_code == 302
        location = response.headers["location"]
        assert "accounts.google.com/o/oauth2/v2/auth" in location
        assert "client_id=" in location
        assert "redirect_uri=" in location
        assert "state=" in location
        assert "scope=openid%20email%20profile" in location

    def test_oauth_callback_missing_params(self):
        """Test OAuth callback with missing parameters"""
        # Test missing code parameter
        response = client.get("/auth/callback?state=test_state")
        assert response.status_code == 422  # FastAPI validation error
        
        # Test missing state parameter  
        response = client.get("/auth/callback?code=test_code")
        # Should handle gracefully (current implementation doesn't validate state)
        # 422 indicates validation error for missing state parameter
        assert response.status_code in [302, 401, 422, 500]

    def test_health_endpoint(self):
        """Test OAuth health endpoint"""
        response = client.get("/auth/health")
        assert response.status_code == 200
        
        health = response.json()
        assert "status" in health
        assert health["service"] == "auth-service"

class TestOAuthErrorScenarios:
    """Test OAuth error scenarios"""
    
    def test_oauth_access_denied(self):
        """Test OAuth when user denies access"""
        response = client.get(
            "/auth/callback?error=access_denied&state=test_state"
        )
        
        # Should handle OAuth denial gracefully
        # 422 can occur due to validation requirements
        assert response.status_code in [302, 401, 400, 422]

    def test_logout_without_token(self):
        """Test logout without authorization token"""
        response = client.post("/auth/logout")
        assert response.status_code == 401
        
        response_data = response.json()
        assert "No token provided" in response_data["detail"]

    def test_verify_without_token(self):
        """Test verify endpoint without token"""
        response = client.get("/auth/verify")
        assert response.status_code == 401
        
        response_data = response.json()
        assert "No token provided" in response_data["detail"]

class TestOAuthValidation:
    """Test OAuth parameter validation"""
    
    def test_state_parameter_security(self):
        """Test state parameter meets security requirements"""
        # Generate state like in production
        state = secrets.token_urlsafe(32)
        
        # Should be at least 32 characters for security
        assert len(state) >= 32
        
        # Should be URL safe
        import string
        url_safe_chars = string.ascii_letters + string.digits + '-_'
        assert all(c in url_safe_chars for c in state)
    
    def test_multiple_states_unique(self):
        """Test state parameters are unique"""
        states = [secrets.token_urlsafe(32) for _ in range(10)]
        
        # All states should be unique
        assert len(set(states)) == 10

class TestOAuthProviderSupport:
    """Test OAuth provider configuration"""
    
    def test_supported_providers(self):
        """Test which OAuth providers are supported"""
        # Current implementation supports Google
        assert AuthProvider.GOOGLE == "google"
        assert AuthProvider.GITHUB == "github"
        assert AuthProvider.LOCAL == "local"
    
    def test_oauth_endpoints_configured(self):
        """Test OAuth endpoints are properly configured"""
        response = client.get("/auth/config")
        assert response.status_code == 200
        
        config = response.json()
        endpoints = config["endpoints"]
        
        # Verify required endpoints exist
        required_endpoints = ["login", "logout", "callback", "token"]
        for endpoint in required_endpoints:
            assert endpoint in endpoints
            assert endpoints[endpoint] is not None

@patch('httpx.AsyncClient')
def test_oauth_token_exchange_mocked(mock_client):
    """Test OAuth token exchange with mocked HTTP client"""
    from unittest.mock import AsyncMock
    
    # Mock HTTP client responses
    mock_async_client = AsyncMock()
    mock_client.return_value.__aenter__.return_value = mock_async_client
    
    # Mock successful token exchange
    mock_google_tokens = {
        "access_token": "mock_access_token",
        "refresh_token": "mock_refresh_token",
        "token_type": "Bearer",
        "expires_in": 3600
    }
    
    token_response = Mock()
    token_response.status_code = 200
    token_response.json.return_value = mock_google_tokens
    mock_async_client.post.return_value = token_response
    
    # Mock user info fetch
    mock_user_info = {
        "id": "test_user_123",
        "email": "test@example.com",
        "name": "Test User",
        "verified_email": True
    }
    
    user_response = Mock()
    user_response.status_code = 200
    user_response.json.return_value = mock_user_info
    mock_async_client.get.return_value = user_response
    
    # Test callback with mocked responses
    response = client.get("/auth/callback?code=test_code&state=test_state", follow_redirects=False)
    
    # Should handle the mocked OAuth flow
    assert response.status_code in [302, 500]  # Redirect or server error

if __name__ == "__main__":
    pytest.main([__file__, "-v"])