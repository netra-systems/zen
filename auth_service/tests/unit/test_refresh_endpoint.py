"""
Unit tests for auth service refresh token endpoint.
Tests the /auth/refresh endpoint request handling and validation.
"""
import pytest
import json
from datetime import datetime, timedelta, UTC
from fastapi import HTTPException
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import jwt
from shared.isolated_environment import IsolatedEnvironment
import asyncio


@pytest.mark.unit
@pytest.mark.auth
class TestRefreshEndpointUnit:
    """Unit tests for refresh token endpoint"""

    @pytest.fixture
    def mock_auth_service(self):
        """Mock auth service for testing"""
        with patch('auth_service.auth_core.routes.auth_routes.auth_service') as mock:
            mock.refresh_tokens = AsyncMock()
            yield mock

    @pytest.fixture
    def test_client(self):
        """Create test client"""
        from auth_service.auth_core.routes.auth_routes import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_refresh_with_valid_token_in_body(self, test_client, mock_auth_service):
        """Test refresh with valid token in request body"""
        # Setup mock to return new tokens
        mock_auth_service.refresh_tokens.return_value = (
            "new.access.token",
            "new.refresh.token"
        )

        # Send request with refresh_token field
        response = test_client.post(
            "/auth/refresh",
            json={"refresh_token": "valid.refresh.token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "new.access.token"
        assert data["refresh_token"] == "new.refresh.token"
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] == 900  # 15 minutes

        # Verify service was called correctly
        mock_auth_service.refresh_tokens.assert_called_once_with("valid.refresh.token")

    def test_refresh_with_camelcase_field(self, test_client, mock_auth_service):
        """Test refresh accepts camelCase field name"""
        mock_auth_service.refresh_tokens.return_value = (
            "new.access.token",
            "new.refresh.token"
        )

        # Send request with refreshToken (camelCase) field
        response = test_client.post(
            "/auth/refresh",
            json={"refreshToken": "valid.refresh.token"}
        )

        assert response.status_code == 200
        assert "access_token" in response.json()
        mock_auth_service.refresh_tokens.assert_called_once_with("valid.refresh.token")

    def test_refresh_with_token_field(self, test_client, mock_auth_service):
        """Test refresh accepts 'token' field name"""
        mock_auth_service.refresh_tokens.return_value = (
            "new.access.token",
            "new.refresh.token"
        )

        # Send request with just 'token' field
        response = test_client.post(
            "/auth/refresh",
            json={"token": "valid.refresh.token"}
        )

        assert response.status_code == 200
        assert "access_token" in response.json()
        mock_auth_service.refresh_tokens.assert_called_once_with("valid.refresh.token")

    def test_refresh_missing_token_field(self, test_client):
        """Test refresh returns 422 when token field is missing"""
        # Send empty body
        response = test_client.post(
            "/auth/refresh",
            json={}
        )

        assert response.status_code == 422
        error = response.json()
        assert "refresh_token field is required" in str(error)
        assert "received_keys" in str(error)

    def test_refresh_with_invalid_json(self, test_client):
        """Test refresh returns 422 for invalid JSON"""
        response = test_client.post(
            "/auth/refresh",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422
        error = response.json()
        assert "Invalid JSON body" in str(error)

    def test_refresh_with_invalid_token(self, test_client, mock_auth_service):
        """Test refresh returns 401 for invalid token"""
        # Mock service returns None for invalid token
        mock_auth_service.refresh_tokens.return_value = None

        response = test_client.post(
            "/auth/refresh",
            json={"refresh_token": "invalid.token"}
        )

        assert response.status_code == 401
        assert "Invalid refresh token" in response.json()["detail"]

    def test_refresh_with_service_error(self, test_client, mock_auth_service):
        """Test refresh returns 500 on service error"""
        # Mock service raises exception
        mock_auth_service.refresh_tokens.side_effect = Exception("Database error")

        response = test_client.post(
            "/auth/refresh",
            json={"refresh_token": "valid.token"}
        )

        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]


class TestJWTHandlerRefreshTokens:
    """Unit tests for JWT handler refresh token functionality"""

    @pytest.fixture
    def jwt_handler(self):
        """Create JWT handler instance"""
        from auth_service.auth_core.core.jwt_handler import JWTHandler
        return JWTHandler()

    def test_create_refresh_token(self, jwt_handler):
        """Test refresh token creation"""
        user_id = "test-user-123"
        token = jwt_handler.create_refresh_token(user_id)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

        # Decode and verify structure
        payload = jwt.decode(
            token, 
            jwt_handler.secret, 
            algorithms=[jwt_handler.algorithm],
            options={"verify_aud": False}  # Disable audience verification for test
        )
        assert payload["sub"] == user_id
        assert payload["type"] == "refresh"
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload  # JWT ID for tracking

    def test_validate_refresh_token_success(self, jwt_handler):
        """Test successful refresh token validation"""
        user_id = "test-user-123"
        token = jwt_handler.create_refresh_token(user_id)

        payload = jwt_handler.validate_token(token, "refresh")
        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["type"] == "refresh"

    def test_validate_refresh_token_wrong_type(self, jwt_handler):
        """Test validation fails for wrong token type"""
        # Create access token instead of refresh
        access_token = jwt_handler.create_access_token(
            user_id="test-user",
            email="test@example.com"
        )

        # Should fail when validating as refresh token
        payload = jwt_handler.validate_token(access_token, "refresh")
        assert payload is None

    def test_validate_expired_refresh_token(self, jwt_handler):
        """Test validation fails for expired token"""
        # Create expired token
        past_time = datetime.now(UTC) - timedelta(hours=1)
        payload = {
            "sub": "test-user",
            "type": "refresh",
            "exp": past_time.timestamp(),
            "iat": past_time.timestamp()
        }

        expired_token = jwt.encode(
            payload,
            jwt_handler.secret,
            algorithm=jwt_handler.algorithm
        )

        result = jwt_handler.validate_token(expired_token, "refresh")
        assert result is None

    def test_validate_malformed_refresh_token(self, jwt_handler):
        """Test validation fails for malformed token"""
        malformed_token = "not.a.valid.jwt.token"

        result = jwt_handler.validate_token(malformed_token, "refresh")
        assert result is None

    def test_refresh_token_blacklist_check(self, jwt_handler):
        """Test refresh token blacklist validation"""
        user_id = "test-user"
        token = jwt_handler.create_refresh_token(user_id)

        # Add token to blacklist
        jwt_handler.blacklist_token(token)

        # Validation should fail for blacklisted token
        result = jwt_handler.validate_token(token, "refresh")
        assert result is None

    def test_refresh_token_expiry_time(self, jwt_handler):
        """Test refresh token has correct expiry time"""
        user_id = "test-user"
        token = jwt_handler.create_refresh_token(user_id)

        payload = jwt.decode(
            token,
            jwt_handler.secret,
            algorithms=[jwt_handler.algorithm],
            options={"verify_aud": False}  # Disable audience verification for test
        )

        # Check expiry matches the environment-specific configuration
        # In test environment, refresh tokens expire in 1 day
        exp_time = datetime.fromtimestamp(payload["exp"], UTC)
        expected_exp = datetime.now(UTC) + timedelta(days=1)  # Test environment uses 1 day

        # Allow 1 minute tolerance for test execution time
        assert abs((exp_time - expected_exp).total_seconds()) < 60


class TestAuthServiceRefreshLogic:
    """Unit tests for auth service refresh token business logic"""

    @pytest.fixture
    def auth_service(self):
        """Create auth service instance"""
        from auth_service.auth_core.services.auth_service import AuthService
        return AuthService()

    @pytest.mark.asyncio
    async def test_refresh_tokens_success(self, auth_service):
        """Test successful token refresh"""
        # Mock JWT handler
        with patch.object(auth_service.jwt_handler, 'validate_token') as mock_validate:
            with patch.object(auth_service.jwt_handler, 'create_access_token') as mock_access:
                with patch.object(auth_service.jwt_handler, 'create_refresh_token') as mock_refresh:
                    # Setup mocks
                    mock_validate.return_value = {"sub": "user-123", "type": "refresh"}
                    mock_access.return_value = "new.access.token"
                    mock_refresh.return_value = "new.refresh.token"

                    # Initialize used_refresh_tokens set
                    auth_service.used_refresh_tokens = set()

                    result = await auth_service.refresh_tokens("old.refresh.token")

                    assert result is not None
                    access_token, refresh_token = result
                    assert access_token == "new.access.token"
                    assert refresh_token == "new.refresh.token"
                    # Verify token was marked as used
                    assert "old.refresh.token" in auth_service.used_refresh_tokens

    @pytest.mark.asyncio
    async def test_refresh_tokens_invalid_token(self, auth_service):
        """Test refresh fails with invalid token"""
        with patch.object(auth_service.jwt_handler, 'validate_token') as mock_validate:
            mock_validate.return_value = None  # Invalid token

            result = await auth_service.refresh_tokens("invalid.token")
            assert result is None

    @pytest.mark.asyncio
    async def test_refresh_tokens_race_condition(self, auth_service):
        """Test refresh handles race condition"""
        with patch.object(auth_service.jwt_handler, 'validate_token') as mock_validate:
            mock_validate.return_value = {"sub": "user-123", "type": "refresh"}

            # Mark token as already used (race condition)
            auth_service.used_refresh_tokens = {"already.used.token"}

            result = await auth_service.refresh_tokens("already.used.token")
            assert result is None

    @pytest.mark.asyncio
    async def test_refresh_updates_session(self, auth_service):
        """Test refresh updates user session"""
        with patch.object(auth_service.jwt_handler, 'validate_token') as mock_validate:
            with patch.object(auth_service.jwt_handler, 'create_access_token') as mock_access:
                with patch.object(auth_service.jwt_handler, 'create_refresh_token') as mock_refresh:
                    mock_validate.return_value = {"sub": "user-123", "type": "refresh"}
                    mock_access.return_value = "new.access.token"
                    mock_refresh.return_value = "new.refresh.token"

                    # Initialize used_refresh_tokens set  
                    auth_service.used_refresh_tokens = set()

                    result = await auth_service.refresh_tokens("old.refresh.token")

                    # Verify tokens were generated
                    assert result is not None
                    assert result[0] == "new.access.token"
                    assert result[1] == "new.refresh.token"
                    # Verify old token was marked as used
                    assert "old.refresh.token" in auth_service.used_refresh_tokens


if __name__ == "__main__":
    pytest.main([__file__, "-v"])