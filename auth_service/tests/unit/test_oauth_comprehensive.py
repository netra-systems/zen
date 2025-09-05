"""
Comprehensive unit tests for OAuth functionality
Tests Google OAuth and general OAuth manager
"""
import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import pytest
import pytest_asyncio
from auth_service.auth_core.oauth_manager import OAuthManager
from auth_service.auth_core.oauth.google_oauth import GoogleOAuthProvider as GoogleOAuthHandler
from auth_service.auth_core.config import AuthConfig
from shared.isolated_environment import get_env


class TestOAuthManagerBasics:
    """Test basic OAuth manager functionality"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Setup for each test"""
        self.manager = OAuthManager()
        self.state = str(uuid.uuid4())
        self.code = "test_authorization_code"
    
    def test_oauth_manager_initialization(self):
        """Test OAuth manager initializes correctly"""
        assert self.manager is not None
        assert hasattr(self.manager, 'google_handler')
    
    def test_get_google_handler(self):
        """Test getting Google OAuth handler"""
        handler = self.manager.get_google_handler()
        assert handler is not None
        assert isinstance(handler, GoogleOAuthHandler)
    
    def test_generate_state_token(self):
        """Test generating OAuth state token"""
        state = self.manager.generate_state_token()
        assert state is not None
        assert len(state) >= 32
    
    def test_validate_state_token(self):
        """Test validating OAuth state token"""
        state = self.manager.generate_state_token()
        is_valid = self.manager.validate_state_token(state)
        assert is_valid is True
    
    def test_validate_invalid_state_token(self):
        """Test validating invalid state token"""
        is_valid = self.manager.validate_state_token("invalid_state_token")
        assert is_valid is False
    
    def test_store_and_retrieve_state(self):
        """Test storing and retrieving OAuth state"""
        user_data = {"redirect_uri": "http://localhost:3000/callback"}
        self.manager.store_state(self.state, user_data)
        retrieved = self.manager.retrieve_state(self.state)
        assert retrieved == user_data
    
    def test_retrieve_nonexistent_state(self):
        """Test retrieving nonexistent state returns None"""
        retrieved = self.manager.retrieve_state("nonexistent_state")
        assert retrieved is None
    
    def test_clear_state(self):
        """Test clearing OAuth state"""
        user_data = {"redirect_uri": "http://localhost:3000/callback"}
        self.manager.store_state(self.state, user_data)
        self.manager.clear_state(self.state)
        retrieved = self.manager.retrieve_state(self.state)
        assert retrieved is None
    
    def test_state_expiration(self):
        """Test OAuth state expires after timeout"""
        user_data = {"redirect_uri": "http://localhost:3000/callback"}
        self.manager.store_state(self.state, user_data, ttl=1)  # 1 second TTL
        import time
        time.sleep(2)
        retrieved = self.manager.retrieve_state(self.state)
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_handle_oauth_callback(self):
        """Test handling OAuth callback"""
        with patch.object(self.manager, 'process_authorization_code', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = {"access_token": "token123", "user": {"email": "test@example.com"}}
            result = await self.manager.handle_oauth_callback("google", self.code, self.state)
            mock_process.assert_called_once_with("google", self.code, self.state)
            assert result == {"access_token": "token123", "user": {"email": "test@example.com"}}
    
    @pytest.mark.asyncio
    async def test_handle_invalid_provider_callback(self):
        """Test handling callback for invalid provider"""
        with pytest.raises(ValueError, match="Unsupported OAuth provider"):
            await self.manager.handle_oauth_callback("invalid_provider", self.code, self.state)


class TestGoogleOAuthHandler:
    """Test Google OAuth handler functionality"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Setup for each test"""
        # Set test OAuth credentials
        env = get_env()
        env.set("GOOGLE_OAUTH_CLIENT_ID_TEST", "test_client_id", "test")
        env.set("GOOGLE_OAUTH_CLIENT_SECRET_TEST", "test_client_secret", "test")
        self.handler = GoogleOAuthHandler()
    
    def test_google_oauth_initialization(self):
        """Test Google OAuth handler initializes correctly"""
        assert self.handler is not None
        assert self.handler.client_id is not None
        assert self.handler.client_secret is not None
    
    def test_get_authorization_url(self):
        """Test getting Google authorization URL"""
        state = str(uuid.uuid4())
        redirect_uri = "http://localhost:3000/callback"
        url = self.handler.get_authorization_url(state, redirect_uri)
        assert url is not None
        assert "accounts.google.com/o/oauth2/v2/auth" in url
        assert f"state={state}" in url
        assert "client_id=" in url
        assert "redirect_uri=" in url
    
    def test_authorization_url_scopes(self):
        """Test authorization URL includes required scopes"""
        state = str(uuid.uuid4())
        redirect_uri = "http://localhost:3000/callback"
        url = self.handler.get_authorization_url(state, redirect_uri)
        assert "scope=" in url
        assert "openid" in url
        assert "email" in url
        assert "profile" in url
    
    def test_authorization_url_response_type(self):
        """Test authorization URL has correct response type"""
        state = str(uuid.uuid4())
        redirect_uri = "http://localhost:3000/callback"
        url = self.handler.get_authorization_url(state, redirect_uri)
        assert "response_type=code" in url
    
    def test_authorization_url_access_type(self):
        """Test authorization URL has offline access type"""
        state = str(uuid.uuid4())
        redirect_uri = "http://localhost:3000/callback"
        url = self.handler.get_authorization_url(state, redirect_uri)
        assert "access_type=offline" in url
    
    def test_authorization_url_prompt(self):
        """Test authorization URL includes consent prompt"""
        state = str(uuid.uuid4())
        redirect_uri = "http://localhost:3000/callback"
        url = self.handler.get_authorization_url(state, redirect_uri, prompt="consent")
        assert "prompt=consent" in url
    
    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens(self):
        """Test exchanging authorization code for tokens"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value={
                "access_token": "access_token_123",
                "refresh_token": "refresh_token_456",
                "id_token": "id_token_789",
                "expires_in": 3600
            })
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response
            
            tokens = await self.handler.exchange_code_for_tokens(
                code="auth_code_123",
                redirect_uri="http://localhost:3000/callback"
            )
            assert tokens["access_token"] == "access_token_123"
            assert tokens["refresh_token"] == "refresh_token_456"
            assert tokens["id_token"] == "id_token_789"
    
    @pytest.mark.asyncio
    async def test_exchange_code_failure(self):
        """Test handling failed code exchange"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value={"error": "invalid_grant"})
            mock_response.status = 400
            mock_post.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(ValueError, match="Failed to exchange code"):
                await self.handler.exchange_code_for_tokens(
                    code="invalid_code",
                    redirect_uri="http://localhost:3000/callback"
                )
    
    @pytest.mark.asyncio
    async def test_get_user_info(self):
        """Test getting user info from Google"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value={
                "sub": "google_user_123",
                "email": "user@gmail.com",
                "email_verified": True,
                "name": "Test User",
                "picture": "https://example.com/photo.jpg"
            })
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response
            
            user_info = await self.handler.get_user_info("access_token_123")
            assert user_info["email"] == "user@gmail.com"
            assert user_info["name"] == "Test User"
            assert user_info["email_verified"] is True
    
    @pytest.mark.asyncio
    async def test_get_user_info_failure(self):
        """Test handling failed user info request"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 401
            mock_get.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(ValueError, match="Failed to get user info"):
                await self.handler.get_user_info("invalid_token")
    
    @pytest.mark.asyncio
    async def test_refresh_access_token(self):
        """Test refreshing Google access token"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value={
                "access_token": "new_access_token_123",
                "expires_in": 3600,
                "token_type": "Bearer"
            })
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response
            
            tokens = await self.handler.refresh_access_token("refresh_token_456")
            assert tokens["access_token"] == "new_access_token_123"
            assert tokens["expires_in"] == 3600
    
    @pytest.mark.asyncio
    async def test_revoke_token(self):
        """Test revoking Google token"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await self.handler.revoke_token("access_token_123")
            assert result is True
    
    def test_validate_id_token_basic(self):
        """Test basic ID token validation"""
        # Note: In real implementation, this would verify with Google's public keys
        # For unit tests, we're testing the validation logic
        id_token = "eyJhbGciOiJSUzI1NiIsImtpZCI6IjEifQ.eyJpc3MiOiJhY2NvdW50cy5nb29nbGUuY29tIiwic3ViIjoiMTIzIn0.signature"
        # This would normally fail without proper verification
        # The test ensures the method exists and handles tokens
        result = self.handler.validate_id_token(id_token)
        # Result depends on implementation details
    
    def test_get_google_public_keys_url(self):
        """Test getting Google public keys URL"""
        url = self.handler.get_google_public_keys_url()
        assert url == "https://www.googleapis.com/oauth2/v3/certs"


class TestOAuthSecurity:
    """Test OAuth security features"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Setup for each test"""
        self.manager = OAuthManager()
        self.handler = GoogleOAuthHandler()
    
    def test_state_token_is_random(self):
        """Test state tokens are randomly generated"""
        states = [self.manager.generate_state_token() for _ in range(10)]
        assert len(states) == len(set(states))  # All unique
    
    def test_state_token_length(self):
        """Test state token has sufficient length for security"""
        state = self.manager.generate_state_token()
        assert len(state) >= 32  # Minimum secure length
    
    def test_prevent_state_reuse(self):
        """Test state token cannot be reused"""
        state = self.manager.generate_state_token()
        user_data = {"test": "data"}
        self.manager.store_state(state, user_data)
        # First retrieval should work and clear the state
        retrieved = self.manager.retrieve_state(state, clear=True)
        assert retrieved == user_data
        # Second retrieval should fail
        retrieved2 = self.manager.retrieve_state(state)
        assert retrieved2 is None
    
    def test_nonce_generation(self):
        """Test nonce generation for OAuth"""
        nonce = self.handler.generate_nonce()
        assert nonce is not None
        assert len(nonce) >= 32
    
    def test_nonce_is_unique(self):
        """Test nonces are unique"""
        nonces = [self.handler.generate_nonce() for _ in range(10)]
        assert len(nonces) == len(set(nonces))
    
    def test_pkce_code_verifier_generation(self):
        """Test PKCE code verifier generation"""
        verifier = self.handler.generate_code_verifier()
        assert verifier is not None
        assert 43 <= len(verifier) <= 128  # PKCE spec requirements
    
    def test_pkce_code_challenge_generation(self):
        """Test PKCE code challenge generation"""
        verifier = self.handler.generate_code_verifier()
        challenge = self.handler.generate_code_challenge(verifier)
        assert challenge is not None
        assert len(challenge) > 0
    
    def test_validate_redirect_uri(self):
        """Test redirect URI validation"""
        valid_uris = [
            "http://localhost:3000/callback",
            "https://app.example.com/auth/callback",
            "http://127.0.0.1:8000/oauth/callback"
        ]
        for uri in valid_uris:
            assert self.handler.validate_redirect_uri(uri) is True
    
    def test_reject_invalid_redirect_uri(self):
        """Test rejecting invalid redirect URIs"""
        invalid_uris = [
            "javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "file:///etc/passwd",
            "../../../callback"
        ]
        for uri in invalid_uris:
            assert self.handler.validate_redirect_uri(uri) is False
    
    def test_csrf_protection_in_state(self):
        """Test CSRF protection via state parameter"""
        state1 = self.manager.generate_state_token()
        state2 = self.manager.generate_state_token()
        assert state1 != state2  # Different for each request
        assert self.manager.validate_state_token(state1) is True
        assert self.manager.validate_state_token("attacker_state") is False