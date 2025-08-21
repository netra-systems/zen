"""
L3 Integration Test: OAuth Authentication Flow
Tests OAuth 2.0 authentication flows
"""

import pytest
import asyncio
import jwt
from unittest.mock import patch, AsyncMock, MagicMock
from netra_backend.app.services.auth_service import AuthService
from netra_backend.app.services.oauth_service import OAuthService
from netra_backend.app.config import settings
import time

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()



class TestAuthOAuthFlowL3:
    """Test OAuth authentication flow scenarios"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_oauth_authorization_code_flow(self):
        """Test OAuth authorization code flow"""
        oauth_service = OAuthService()
        
        # Generate authorization code
        auth_code = await oauth_service.generate_authorization_code(
            client_id="test_client",
            user_id="123",
            redirect_uri="http://localhost/callback"
        )
        
        assert auth_code is not None
        
        # Exchange code for token
        token_response = await oauth_service.exchange_code_for_token(
            code=auth_code,
            client_id="test_client",
            client_secret="test_secret",
            redirect_uri="http://localhost/callback"
        )
        
        assert "access_token" in token_response
        assert "refresh_token" in token_response
        assert "token_type" in token_response
        assert token_response["token_type"] == "Bearer"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_oauth_implicit_flow(self):
        """Test OAuth implicit flow for SPAs"""
        oauth_service = OAuthService()
        
        # Direct token generation for implicit flow
        token_response = await oauth_service.generate_implicit_token(
            client_id="spa_client",
            user_id="123",
            redirect_uri="http://localhost:3000/callback"
        )
        
        assert "access_token" in token_response
        assert "token_type" in token_response
        assert "expires_in" in token_response
        # No refresh token in implicit flow
        assert "refresh_token" not in token_response
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_oauth_client_credentials_flow(self):
        """Test OAuth client credentials flow for machine-to-machine"""
        oauth_service = OAuthService()
        
        # Client credentials flow
        token_response = await oauth_service.client_credentials_grant(
            client_id="service_client",
            client_secret="service_secret",
            scope="api:read api:write"
        )
        
        assert "access_token" in token_response
        assert "token_type" in token_response
        assert token_response["token_type"] == "Bearer"
        
        # Verify token has correct scope
        decoded = jwt.decode(
            token_response["access_token"],
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )
        assert "api:read" in decoded["scope"]
        assert "api:write" in decoded["scope"]
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_oauth_refresh_token_flow(self):
        """Test OAuth refresh token flow"""
        oauth_service = OAuthService()
        
        # Initial token
        initial = await oauth_service.generate_token_pair(
            user_id="123",
            client_id="test_client"
        )
        
        # Wait a bit
        await asyncio.sleep(0.1)
        
        # Refresh token
        refreshed = await oauth_service.refresh_access_token(
            refresh_token=initial["refresh_token"],
            client_id="test_client",
            client_secret="test_secret"
        )
        
        assert refreshed["access_token"] != initial["access_token"]
        assert "refresh_token" in refreshed
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_oauth_pkce_flow(self):
        """Test OAuth with PKCE for public clients"""
        oauth_service = OAuthService()
        
        # Generate PKCE challenge
        code_verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        code_challenge = await oauth_service.generate_pkce_challenge(code_verifier)
        
        # Authorization with PKCE
        auth_code = await oauth_service.generate_authorization_code(
            client_id="public_client",
            user_id="123",
            redirect_uri="http://localhost/callback",
            code_challenge=code_challenge,
            code_challenge_method="S256"
        )
        
        # Exchange with verifier
        token_response = await oauth_service.exchange_code_for_token(
            code=auth_code,
            client_id="public_client",
            redirect_uri="http://localhost/callback",
            code_verifier=code_verifier
        )
        
        assert "access_token" in token_response