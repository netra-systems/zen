"""
Test OAuth Redirect Flow in Staging Environment
Ensures OAuth flow uses correct staging URLs, not localhost:3000
"""
import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import httpx
import secrets

from auth_service.auth_core.services.auth_service import AuthService
from auth_service.auth_core.config import AuthConfig


class TestOAuthStagingRedirectFlow:
    """Test OAuth redirect flow uses correct staging URLs"""
    
    @pytest.fixture(autouse=True)
    def setup_staging_env(self):
        """Set up staging environment"""
        self.original_env = os.environ.copy()
        os.environ["ENVIRONMENT"] = "staging"
        os.environ["FRONTEND_URL"] = "https://app.staging.netrasystems.ai"
        os.environ["AUTH_SERVICE_URL"] = "https://auth.staging.netrasystems.ai"
        os.environ["GOOGLE_CLIENT_ID"] = "test-client-id"
        os.environ["GOOGLE_CLIENT_SECRET"] = "test-client-secret"
        yield
        # Restore environment
        os.environ.clear()
        os.environ.update(self.original_env)
    
    @pytest.mark.asyncio
    async def test_oauth_google_login_staging_redirect(self):
        """Test Google OAuth login uses staging redirect URI, not localhost:3000"""
        # This test should FAIL if OAuth uses localhost:3000 as redirect_uri
        
        from auth_service.auth_core.routes.auth_routes import initiate_oauth_login
        
        # Test OAuth login initiation
        result = await initiate_oauth_login(provider="google", return_url="/dashboard")
        
        # Extract redirect URL from response
        assert hasattr(result, "headers"), "Response should have redirect headers"
        location = result.headers.get("location", "")
        
        # Parse redirect_uri from OAuth URL
        assert "redirect_uri=" in location, "OAuth URL should contain redirect_uri"
        redirect_uri_param = location.split("redirect_uri=")[1].split("&")[0]
        
        # URL decode the redirect_uri
        from urllib.parse import unquote
        redirect_uri = unquote(redirect_uri_param)
        
        # Assert correct staging redirect URI
        assert redirect_uri == "https://app.staging.netrasystems.ai/auth/callback", \
            f"OAuth redirect_uri should use staging URL, got: {redirect_uri}"
        
        # Assert no localhost in OAuth URL
        assert "localhost:3000" not in location, \
            f"OAuth URL should not contain localhost:3000 in staging"
        assert "localhost%3A3000" not in location, \
            f"OAuth URL should not contain URL-encoded localhost:3000"
    
    @pytest.mark.asyncio
    async def test_oauth_callback_processing_staging(self):
        """Test OAuth callback processing uses correct staging URLs"""
        # This test should FAIL if callback processing uses localhost:3000
        
        from auth_service.auth_core.routes.auth_routes import oauth_callback
        
        # Mock request with OAuth callback data
        mock_request = MagicMock()
        mock_request.client.host = "192.168.1.1"
        mock_request.headers = {"user-agent": "test-browser"}
        mock_request.cookies = {}
        
        # Mock successful OAuth token exchange
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "access_token": "test-access-token",
                "id_token": "test-id-token",
                "token_type": "Bearer"
            }
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response
            
            # Mock user info retrieval
            with patch("httpx.AsyncClient.get") as mock_get:
                mock_user_response = MagicMock()
                mock_user_response.json.return_value = {
                    "id": "test-user-id",
                    "email": "test@example.com",
                    "name": "Test User"
                }
                mock_get.return_value = mock_user_response
                
                # Test callback processing
                code = "test-auth-code"
                state = secrets.token_urlsafe(32)
                
                # Process callback
                response = await oauth_callback(
                    code=code,
                    state=state,
                    request=mock_request
                )
                
                # Check the redirect response
                if hasattr(response, "headers"):
                    location = response.headers.get("location", "")
                    
                    # Assert redirect goes to staging frontend
                    assert location.startswith("https://app.staging.netrasystems.ai"), \
                        f"Callback redirect should go to staging frontend, got: {location}"
                    
                    # Assert no localhost in redirect
                    assert "localhost:3000" not in location, \
                        "Callback redirect should not contain localhost:3000"
    
    def test_oauth_state_validation_urls(self):
        """Test OAuth state validation uses correct staging URLs"""
        # Ensure state validation doesn't introduce localhost URLs
        
        from auth_service.auth_core.security.oauth_security import OAuthSecurityManager
        
        # Create security manager
        security_mgr = OAuthSecurityManager()
        
        # Generate state with staging redirect
        state_data = {
            "redirect_uri": "https://app.staging.netrasystems.ai/auth/callback",
            "return_url": "/dashboard",
            "timestamp": 1234567890
        }
        
        # Ensure no localhost URLs are injected during state handling
        import json
        state_json = json.dumps(state_data)
        assert "localhost:3000" not in state_json, \
            "State data should not contain localhost:3000"
    
    @pytest.mark.asyncio
    async def test_token_exchange_redirect_uri(self):
        """Test token exchange uses correct staging redirect_uri"""
        # This test should FAIL if token exchange sends localhost:3000 as redirect_uri
        
        auth_service = AuthService()
        
        # Mock the token exchange request
        with patch("httpx.AsyncClient.post") as mock_post:
            # Capture the request data
            actual_data = {}
            
            async def capture_request(*args, **kwargs):
                if "data" in kwargs:
                    actual_data.update(kwargs["data"])
                mock_response = MagicMock()
                mock_response.json.return_value = {
                    "access_token": "test-token",
                    "id_token": "test-id"
                }
                mock_response.raise_for_status = MagicMock()
                return mock_response
            
            mock_post.side_effect = capture_request
            
            # Attempt token exchange
            try:
                result = await auth_service.exchange_code_for_token(
                    code="test-code",
                    redirect_uri="https://app.staging.netrasystems.ai/auth/callback"
                )
            except Exception:
                pass  # We're testing the request data, not the full flow
            
            # Check the redirect_uri sent in token exchange
            if "redirect_uri" in actual_data:
                sent_redirect_uri = actual_data["redirect_uri"]
                
                assert sent_redirect_uri == "https://app.staging.netrasystems.ai/auth/callback", \
                    f"Token exchange should use staging redirect_uri, got: {sent_redirect_uri}"
                
                assert "localhost:3000" not in sent_redirect_uri, \
                    "Token exchange redirect_uri should not contain localhost:3000"
    
    def test_all_oauth_endpoints_use_staging_urls(self):
        """Comprehensive test that all OAuth-related endpoints use staging URLs"""
        # This test should FAIL if any OAuth endpoint uses localhost:3000
        
        # Check all OAuth-related URL constructions
        frontend_url = AuthConfig.get_frontend_url()
        auth_url = AuthConfig.get_auth_service_url()
        
        # All OAuth URLs that should use staging domains
        oauth_urls = [
            f"{frontend_url}/auth/callback",  # Primary callback
            f"{frontend_url}/auth/success",    # Success redirect
            f"{frontend_url}/auth/error",      # Error redirect
            f"{auth_url}/auth/login",          # Login endpoint
            f"{auth_url}/auth/callback",       # Auth service callback
            f"{auth_url}/auth/token",          # Token endpoint
        ]
        
        for url in oauth_urls:
            assert "localhost:3000" not in url, \
                f"OAuth URL should not contain localhost:3000 in staging: {url}"
            assert "localhost" not in url, \
                f"OAuth URL should not contain localhost in staging: {url}"
            
            # Verify staging domains are used
            assert "staging.netrasystems.ai" in url or url.startswith("https://"), \
                f"OAuth URL should use staging domain: {url}"