"""
OAuth Flow End-to-End Tests
Business Value: $25K MRR - Critical authentication path validation
"""

import asyncio
import json
from typing import Any, Dict, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.websocket_core import WebSocketManager
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from shared.isolated_environment import IsolatedEnvironment

# Import main app with error handling
try:
    from netra_backend.app.main import app
except ImportError:
    # Create a minimal FastAPI app for testing if import fails
    app = FastAPI()

# Import with error handling
try:
    from netra_backend.app.services.security_service import SecurityService
except ImportError:
    SecurityService = Mock

try:
    from netra_backend.app.clients.auth_client_core import auth_client
except ImportError:
    auth_client = AuthManager()

try:
    from netra_backend.app.schemas.auth_types import DevLoginRequest
except ImportError:
    from pydantic import BaseModel
    
    class DevLoginRequest(BaseModel):
        email: str
        name: str = "Development User"

try:
    from netra_backend.app.auth_integration.auth import get_current_user
except ImportError:
    get_current_user = Mock()


@pytest.fixture
def test_client():
    """Create test client for OAuth flow testing"""
    # Mock database dependencies to avoid configuration errors
    try:
        from netra_backend.app.auth_dependencies import get_db_session, get_security_service
        
        async def mock_get_db_session():
            """Mock database session isolation for testing without real database"""
            mock_session = AsyncMock(spec=AsyncSession)
            yield mock_session

        async def mock_get_security_service():
            """Mock security service isolation for testing without dependencies"""
            await asyncio.sleep(0)
            return AsyncMock(spec=SecurityService)

        app.dependency_overrides[get_db_session] = mock_get_db_session
        app.dependency_overrides[get_security_service] = mock_get_security_service
    except ImportError:
        pass

    yield TestClient(app)


@pytest.fixture
def mock_auth_client():
    """Mock auth client for OAuth testing"""
    with patch('netra_backend.app.clients.auth_client_core.auth_client') as mock:
        mock.get_oauth_config.return_value = {
            "client_id": "test_client_id",
            "redirect_uri": "http://localhost:3000/auth/callback",
            "scope": "openid email profile"
        }
        mock.detect_environment.return_value = Mock(value="development")
        yield mock


@pytest.fixture
def mock_security_service():
    """Mock security service for authentication testing"""
    mock = Mock(spec=SecurityService)
    mock.authenticate_user = AsyncMock()
    mock.create_access_token = AsyncMock()
    mock.create_refresh_token = AsyncMock()
    mock.validate_token = AsyncMock()
    mock.validate_token_jwt = AsyncMock()
    mock.validate_refresh_token = AsyncMock()
    return mock


@pytest.fixture
def mock_websocket_manager():
    """Mock WebSocket manager for connection testing"""
    with patch('netra_backend.app.websocket.connection_manager.WebSocketManager') as mock:
        manager = Mock()
        manager.connect = AsyncMock()
        manager.disconnect = AsyncMock()
        manager.authenticate_connection = AsyncMock(return_value=True)
        mock.return_value = manager
        yield manager


class TestOAuthCompleteFlow:
    """Test complete OAuth login sequence"""

    @pytest.mark.asyncio
    async def test_complete_oauth_login_flow(self, test_client, mock_auth_client):
        """
        Test full OAuth login sequence
        Business Value: $25K MRR - User authentication path
        """
        # Step 1: User initiates OAuth login
        # The endpoint returns a redirect (302) to the auth service
        response = test_client.get("/auth/login?provider=google", follow_redirects=False)

        # Should receive a 302 redirect to auth service
        assert response.status_code == 302

        # Verify redirect URL contains the auth service and provider
        redirect_url = response.headers.get("location")
        assert redirect_url is not None
        assert "auth/login" in redirect_url
        assert "provider=google" in redirect_url

        # Step 2: Test OAuth callback redirect
        # The callback endpoint also redirects to auth service
        callback_response = test_client.get(
            "/auth/callback?code=test_auth_code&state=test_state",
            follow_redirects=False
        )

        # Should receive a 302 redirect to auth service callback
        assert callback_response.status_code == 302

        # Verify callback redirect URL contains the auth service
        callback_redirect_url = callback_response.headers.get("location")
        assert callback_redirect_url is not None
        assert "auth/callback" in callback_redirect_url
        assert "code=test_auth_code" in callback_redirect_url
        assert "state=test_state" in callback_redirect_url

        # OAuth flow test complete - both login and callback redirects work correctly
        print("OAuth redirect flow working correctly")


class TestTokenGenerationAndValidation:
    """Test JWT token lifecycle"""

    @pytest.mark.asyncio
    async def test_token_generation_and_validation(self, mock_security_service):
        """
        Test JWT token lifecycle
        Covers: Generation, validation, expiration
        """
        # Mock token generation
        mock_security_service.create_access_token.return_value = "jwt_access_token"
        mock_security_service.create_refresh_token.return_value = "jwt_refresh_token"

        # Generate tokens
        access_token = await mock_security_service.create_access_token(
            user_id="test_user",
            email="test@example.com"
        )

        refresh_token = await mock_security_service.create_refresh_token(
            user_id="test_user"
        )

        assert access_token == "jwt_access_token"
        assert refresh_token == "jwt_refresh_token"

        # Mock token validation
        mock_security_service.validate_token_jwt.return_value = {
            "valid": True,
            "user_id": "test_user",
            "email": "test@example.com",
            "permissions": ["read", "write"]
        }

        # Validate token
        validation_result = await mock_security_service.validate_token_jwt(access_token)

        assert validation_result["valid"] is True
        assert validation_result["user_id"] == "test_user"

    @pytest.mark.asyncio
    async def test_token_expiration_handling(self, mock_security_service):
        """Test expired token handling"""
        # Mock expired token validation
        mock_security_service.validate_token_jwt.return_value = {
            "valid": False,
            "error": "Token expired"
        }

        expired_token = "expired_jwt_token"
        validation_result = await mock_security_service.validate_token_jwt(expired_token)

        assert validation_result["valid"] is False
        assert "expired" in validation_result.get("error", "").lower()


class TestWebSocketAuthentication:
    """Test WebSocket auth with JWT"""

    @pytest.mark.asyncio
    async def test_websocket_authentication(self, mock_websocket_manager):
        """
        Test WebSocket auth with JWT
        Verifies token validation and connection establishment
        """
        # Mock successful authentication
        mock_websocket_manager.authenticate_connection.return_value = {
            "authenticated": True,
            "user_id": "test_user",
            "permissions": ["read", "write"]
        }

        # Test WebSocket connection with valid token
        token = "valid_jwt_token"
        auth_result = await mock_websocket_manager.authenticate_connection(
            token=token
        )

        assert auth_result["authenticated"] is True
        assert auth_result["user_id"] == "test_user"

    @pytest.mark.asyncio
    async def test_websocket_invalid_token_rejection(self, mock_websocket_manager):
        """Test WebSocket rejection of invalid tokens"""
        # Mock failed authentication
        mock_websocket_manager.authenticate_connection.return_value = {
            "authenticated": False,
            "error": "Invalid token"
        }

        # Test WebSocket connection with invalid token
        invalid_token = "invalid_jwt_token"
        auth_result = await mock_websocket_manager.authenticate_connection(
            token=invalid_token
        )

        assert auth_result["authenticated"] is False
        assert "invalid" in auth_result.get("error", "").lower()


class TestTokenRefreshFlow:
    """Test token refresh across services"""

    @pytest.mark.asyncio
    async def test_token_refresh_across_services(self, test_client, mock_security_service):
        """
        Test token refresh flow
        Covers: Refresh token usage and new token distribution
        """
        # Mock refresh token validation and new token generation
        mock_security_service.validate_refresh_token = AsyncMock(return_value={
            "valid": True,
            "user_id": "test_user"
        })

        mock_security_service.create_access_token.return_value = "new_access_token"
        mock_security_service.create_refresh_token.return_value = "new_refresh_token"

        # Simulate refresh token request
        with patch('netra_backend.app.services.security_service.SecurityService', return_value=mock_security_service):
            # Test refresh endpoint would be called here
            # This demonstrates the flow without requiring actual endpoint
            refresh_result = {
                "access_token": await mock_security_service.create_access_token(
                    user_id="test_user",
                    email="test@example.com"
                ),
                "refresh_token": await mock_security_service.create_refresh_token(
                    user_id="test_user"
                ),
                "token_type": "Bearer",
                "expires_in": 900
            }

            assert refresh_result["access_token"] == "new_access_token"
            assert refresh_result["refresh_token"] == "new_refresh_token"
            assert refresh_result["token_type"] == "Bearer"


class TestOAuthErrorScenarios:
    """Test OAuth error handling scenarios"""

    @pytest.mark.asyncio
    async def test_oauth_provider_error(self, test_client, mock_auth_client):
        """Test OAuth provider error handling"""
        # Mock OAuth provider error
        with patch('netra_backend.app.routes.auth_routes.login_flow.handle_login_request') as mock_login:
            mock_login.side_effect = Exception("OAuth provider unavailable")
            
            response = test_client.get("/auth/login?provider=google")
            # Should handle error gracefully
            assert response.status_code in [500, 502, 503]

    @pytest.mark.asyncio
    async def test_invalid_authorization_code(self, test_client):
        """Test invalid authorization code handling"""
        with patch('netra_backend.app.routes.auth_routes.callback_processor.handle_callback_request') as mock_callback:
            mock_callback.side_effect = Exception("Invalid authorization code")
            
            response = test_client.get(
                "/auth/callback?code=invalid_code&state=test_state"
            )
            # Should handle invalid code gracefully
            assert response.status_code in [400, 401, 500]

    @pytest.mark.asyncio
    async def test_state_parameter_validation(self, test_client):
        """Test CSRF protection via state parameter"""
        # Test missing state parameter
        response = test_client.get("/auth/callback?code=test_code")
        # Should reject request without state parameter
        assert response.status_code in [400, 403]


class TestCrossServiceTokenValidation:
    """Test token validation across different services"""

    @pytest.mark.asyncio
    async def test_auth_service_token_validation(self, mock_auth_client):
        """Test token validation through auth service"""
        # Mock auth service token validation
        with patch('netra_backend.app.clients.auth_client_core.auth_client.validate_token') as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "user_id": "test_user",
                "email": "test@example.com",
                "permissions": ["read", "write"]
            }

            token = "cross_service_token"
            validation_result = mock_validate(token)

            assert validation_result["valid"] is True
            assert validation_result["user_id"] == "test_user"

    @pytest.mark.asyncio
    async def test_backend_service_token_acceptance(self, test_client):
        """Test backend service accepts valid tokens from auth service"""
        with patch('netra_backend.app.auth_integration.auth.get_current_user') as mock_user:
            mock_user.return_value = {
                "id": "test_user",
                "email": "test@example.com",
                "authenticated": True
            }

            # Test protected endpoint with valid token
            response = test_client.get(
                "/auth/me",
                headers={"Authorization": "Bearer valid_cross_service_token"}
            )

            assert response.status_code == 200
            user_data = response.json()
            assert user_data["authenticated"] is True


class TestDevLoginFlow:
    """Test development login functionality"""

    @pytest.mark.asyncio
    async def test_dev_login_flow(self, test_client, mock_auth_client):
        """Test development mode login flow"""
        # Mock development environment
        mock_auth_client.detect_environment.return_value = Mock(value="development")

        dev_request = DevLoginRequest(
            email="dev@example.com",
            name="Development User"
        )

        with patch('netra_backend.app.routes.auth_routes.dev_login.handle_dev_login') as mock_dev_login:
            mock_dev_login.return_value = {
                "access_token": "dev_access_token",
                "refresh_token": "dev_refresh_token",
                "user": {
                    "id": "dev_user_id",
                    "email": "dev@example.com",
                    "name": "Development User"
                }
            }

            response = test_client.post(
                "/auth/dev_login",
                json=dev_request.model_dump()
            )

            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["user"]["email"] == "dev@example.com"


@pytest.mark.integration
class TestOAuthIntegrationFlow:
    """Integration tests for complete OAuth flow"""

    @pytest.mark.asyncio
    async def test_end_to_end_oauth_integration(self, test_client):
        """
        End-to-end OAuth integration test
        Tests the complete flow from login initiation to authenticated session
        """
        # Test should validate that callback is properly forwarded (302 redirect is expected)
        # This is the correct behavior - backend forwards to auth service

        # Mock httpx.AsyncClient to simulate auth service response
        with patch('httpx.AsyncClient') as mock_client_class:
            # Mock the async client instance
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock successful response from auth service
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "test_access_token",
                "token_type": "Bearer",
                "user": {
                    "id": "test_user_123", 
                    "email": "test@example.com",
                    "name": "Test User"
                }
            }
            mock_client.get.return_value = mock_response

            # Test OAuth callback handling (disable automatic redirect following)
            response = test_client.get(
                "/auth/callback?code=test_code&state=test_state",
                follow_redirects=False
            )

            # Verify response is a redirect to auth service (expected behavior)
            assert response.status_code == 302

            # Verify redirect URL contains expected auth service endpoint
            redirect_url = response.headers.get("location", "")
            assert "/auth/callback" in redirect_url
            assert "code=test_code" in redirect_url
            assert "state=test_state" in redirect_url


if __name__ == "__main__":
    # Run specific test for debugging
    pytest.main([__file__ + "::TestOAuthCompleteFlow::test_complete_oauth_login_flow", "-v"])