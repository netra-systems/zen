"""
Integration test for OAuth token flow from Google to frontend storage.
Tests the complete flow: OAuth callback -> token exchange -> frontend redirect -> token storage
"""
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import json
import base64


@pytest.mark.asyncio
async def test_oauth_callback_token_exchange():
    """Test that auth service correctly exchanges OAuth code for tokens"""
    from auth_service.auth_core.routes.auth_routes import router
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(router)
    
    with patch('auth_service.auth_core.config.AuthConfig.get_google_client_id', return_value='test-client-id'), \
         patch('auth_service.auth_core.config.AuthConfig.get_google_client_secret', return_value='test-secret'), \
         patch('auth_service.auth_core.routes.auth_routes._determine_urls', return_value=('http://auth.test', 'http://app.test')):
        
        # Mock Google token exchange
        mock_token_response = {
            'access_token': 'google-access-token',
            'id_token': 'google-id-token',
            'refresh_token': 'google-refresh-token'
        }
        
        # Mock Google user info
        mock_user_info = {
            'id': 'google-user-123',
            'email': 'test@example.com',
            'name': 'Test User'
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            # Mock token exchange response
            token_response = AsyncMock()
            token_response.status_code = 200
            token_response.json.return_value = mock_token_response
            
            # Mock user info response
            user_response = AsyncMock()
            user_response.status_code = 200
            user_response.json.return_value = mock_user_info
            
            mock_instance.post.return_value = token_response
            mock_instance.get.return_value = user_response
            
            # Mock database operations
            with patch('auth_service.auth_core.routes.auth_routes.auth_db') as mock_db, \
                 patch('auth_service.auth_core.routes.auth_routes.AuthUserRepository') as mock_repo, \
                 patch('auth_service.auth_core.routes.auth_routes.auth_service') as mock_auth_service:
                
                # Setup mocks
                mock_session = AsyncMock()
                mock_db.get_session.return_value.__aenter__.return_value = mock_session
                
                mock_auth_user = MagicMock()
                mock_auth_user.id = 'user-123'
                mock_repo_instance = AsyncMock()
                mock_repo_instance.create_oauth_user.return_value = mock_auth_user
                mock_repo.return_value = mock_repo_instance
                
                # Mock JWT creation
                mock_auth_service.jwt_handler.create_access_token.return_value = 'jwt-access-token'
                mock_auth_service.jwt_handler.create_refresh_token.return_value = 'jwt-refresh-token'
                mock_auth_service.session_manager.create_session.return_value = 'session-123'
                
                # Test the callback
                client = TestClient(app)
                response = client.get(
                    '/auth/callback',
                    params={
                        'code': 'test-oauth-code',
                        'state': 'test-state'
                    },
                    follow_redirects=False
                )
                
                # Verify redirect response
                assert response.status_code == 302
                location = response.headers.get('location')
                assert location is not None
                assert 'token=jwt-access-token' in location
                assert 'refresh=jwt-refresh-token' in location
                assert location.startswith('http://app.test/chat')


@pytest.mark.asyncio  
async def test_frontend_token_storage():
    """Test that frontend correctly stores tokens from URL parameters"""
    # This would be better as a frontend test, but we can test the logic
    from urllib.parse import urlparse, parse_qs
    
    # Simulate the redirect URL from auth service
    redirect_url = "http://app.test/chat?token=jwt-access-token&refresh=jwt-refresh-token"
    
    parsed = urlparse(redirect_url)
    params = parse_qs(parsed.query)
    
    # Verify tokens are present in URL
    assert 'token' in params
    assert params['token'][0] == 'jwt-access-token'
    assert 'refresh' in params
    assert params['refresh'][0] == 'jwt-refresh-token'


@pytest.mark.asyncio
async def test_token_validation_after_storage():
    """Test that stored tokens can be validated by auth service"""
    from auth_service.auth_core.routes.auth_routes import router
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(router)
    
    test_token = 'jwt-access-token'
    
    with patch('auth_service.auth_core.routes.auth_routes.auth_service') as mock_auth_service:
        # Mock successful token validation
        mock_response = MagicMock()
        mock_response.valid = True
        mock_response.user_id = 'user-123'
        mock_response.email = 'test@example.com'
        mock_auth_service.validate_token.return_value = mock_response
        
        client = TestClient(app)
        response = client.post(
            '/auth/validate',
            json={'token': test_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['valid'] is True
        assert data['user_id'] == 'user-123'


@pytest.mark.asyncio
async def test_oauth_error_handling():
    """Test error handling when OAuth token exchange fails"""
    from auth_service.auth_core.routes.auth_routes import router
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(router)
    
    with patch('auth_service.auth_core.config.AuthConfig.get_google_client_id', return_value='test-client-id'), \
         patch('auth_service.auth_core.config.AuthConfig.get_google_client_secret', return_value='test-secret'), \
         patch('auth_service.auth_core.routes.auth_routes._determine_urls', return_value=('http://auth.test', 'http://app.test')):
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            # Mock failed token exchange
            token_response = AsyncMock()
            token_response.status_code = 400
            token_response.text = 'Invalid authorization code'
            mock_instance.post.return_value = token_response
            
            client = TestClient(app)
            response = client.get(
                '/auth/callback',
                params={
                    'code': 'invalid-code',
                    'state': 'test-state'
                }
            )
            
            # Should return error
            assert response.status_code == 401
            assert 'Failed to exchange code' in response.json()['detail']


@pytest.mark.asyncio
async def test_staging_environment_urls():
    """Test that staging environment uses correct URLs"""
    from auth_service.auth_core.config import AuthConfig
    import os
    
    # Set staging environment
    with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):
        # Test auth service URL
        auth_url = AuthConfig.get_auth_service_url()
        assert auth_url == 'https://auth.staging.netrasystems.ai'
        
        # Test frontend URL
        frontend_url = AuthConfig.get_frontend_url()
        assert frontend_url == 'https://app.staging.netrasystems.ai'
        
        # Test callback URL construction
        callback_url = f"{frontend_url}/auth/callback"
        assert callback_url == 'https://app.staging.netrasystems.ai/auth/callback'


def test_jwt_token_decoding():
    """Test that frontend can decode JWT tokens"""
    import jwt
    import time
    
    # Create a test JWT token
    payload = {
        'user_id': 'user-123',
        'email': 'test@example.com',
        'exp': int(time.time()) + 3600,
        'iat': int(time.time())
    }
    
    secret = 'test-secret'
    token = jwt.encode(payload, secret, algorithm='HS256')
    
    # Decode without verification (as frontend would)
    decoded = jwt.decode(token, options={"verify_signature": False})
    
    assert decoded['user_id'] == 'user-123'
    assert decoded['email'] == 'test@example.com'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])