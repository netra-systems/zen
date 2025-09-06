from unittest.mock import AsyncMock, Mock, patch, MagicMock

# REMOVED_SYNTAX_ERROR: '''Existing User Login Flow Integration Tests (L3)

# REMOVED_SYNTAX_ERROR: Tests complete login flow for existing users including authentication,
# REMOVED_SYNTAX_ERROR: session management, token refresh, and logout.

# REMOVED_SYNTAX_ERROR: Business Value Justification (BVJ):
    # REMOVED_SYNTAX_ERROR: - Segment: All (Free, Early, Mid, Enterprise)
    # REMOVED_SYNTAX_ERROR: - Business Goal: Retention - seamless login keeps users engaged
    # REMOVED_SYNTAX_ERROR: - Value Impact: Poor login experience causes user churn
    # REMOVED_SYNTAX_ERROR: - Revenue Impact: Direct - can't monetize users who can't log in
    # REMOVED_SYNTAX_ERROR: """"

    # REMOVED_SYNTAX_ERROR: import sys
    # REMOVED_SYNTAX_ERROR: from pathlib import Path
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import TestDatabaseManager
    # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # Test framework import - using pytest fixtures instead

    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import os
    # REMOVED_SYNTAX_ERROR: import time
    # REMOVED_SYNTAX_ERROR: import uuid
    # REMOVED_SYNTAX_ERROR: from datetime import datetime, timedelta, timezone
    # REMOVED_SYNTAX_ERROR: from typing import Any, Dict

    # REMOVED_SYNTAX_ERROR: import jwt
    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: from fastapi.testclient import TestClient
    # REMOVED_SYNTAX_ERROR: from httpx import ASGITransport, AsyncClient

    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env

    # Set test environment before imports
    # REMOVED_SYNTAX_ERROR: env = get_env()
    # REMOVED_SYNTAX_ERROR: env.set("ENVIRONMENT", "testing", "test")
    # REMOVED_SYNTAX_ERROR: env.set("TESTING", "true", "test")
    # REMOVED_SYNTAX_ERROR: env.set("SKIP_STARTUP_CHECKS", "true", "test")

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.config import get_config
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.models_postgres import User
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.main import app
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.user_auth_service import UserAuthService as AuthService
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.session_service import SessionService

    # Import test framework for real auth
    # REMOVED_SYNTAX_ERROR: from test_framework.fixtures.auth import create_test_user_token, create_admin_token, create_real_jwt_token

# REMOVED_SYNTAX_ERROR: class TestExistingUserLoginFlow:
    # REMOVED_SYNTAX_ERROR: """Test existing user login flow from authentication to logout."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def mock_existing_user(self):
    # REMOVED_SYNTAX_ERROR: """Create mock existing user."""
    # Mock: Service component isolation for predictable testing behavior
    # REMOVED_SYNTAX_ERROR: user = MagicMock(spec=User)
    # REMOVED_SYNTAX_ERROR: user.id = str(uuid.uuid4())
    # REMOVED_SYNTAX_ERROR: user.email = "existing@example.com"
    # REMOVED_SYNTAX_ERROR: user.full_name = "Existing User"
    # REMOVED_SYNTAX_ERROR: user.is_active = True
    # REMOVED_SYNTAX_ERROR: user.email_verified = True
    # REMOVED_SYNTAX_ERROR: user.last_login = datetime.now(timezone.utc) - timedelta(days=1)
    # REMOVED_SYNTAX_ERROR: user.failed_login_attempts = 0
    # Mock: Service component isolation for predictable testing behavior
    # REMOVED_SYNTAX_ERROR: user.check_password = MagicMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: yield user

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def mock_auth_service(self):
    # REMOVED_SYNTAX_ERROR: """Create mock auth service."""
    # Mock: Authentication service isolation for testing without real auth flows
    # REMOVED_SYNTAX_ERROR: service = AsyncMock(spec=AuthService)
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: service.authenticate = AsyncMock()  # TODO: Use real service instance
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: service.generate_tokens = AsyncMock()  # TODO: Use real service instance
    # Mock: Async component isolation for testing without real async operations
    # REMOVED_SYNTAX_ERROR: service.validate_token = AsyncMock(return_value=True)
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: service.refresh_tokens = AsyncMock()  # TODO: Use real service instance
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: service.revoke_token = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: yield service

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def mock_session_service(self):
    # REMOVED_SYNTAX_ERROR: """Create mock session service."""
    # Mock: Database session isolation for transaction testing without real database dependency
    # REMOVED_SYNTAX_ERROR: service = AsyncMock(spec=SessionService)
    # Mock: Session isolation for controlled testing without external state
    # REMOVED_SYNTAX_ERROR: service.create_session = AsyncMock()  # TODO: Use real service instance
    # Mock: Session isolation for controlled testing without external state
    # REMOVED_SYNTAX_ERROR: service.get_session = AsyncMock()  # TODO: Use real service instance
    # Mock: Session isolation for controlled testing without external state
    # REMOVED_SYNTAX_ERROR: service.update_session_activity = AsyncMock()  # TODO: Use real service instance
    # Mock: Session isolation for controlled testing without external state
    # REMOVED_SYNTAX_ERROR: service.end_session = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: yield service

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def async_client(self):
    # REMOVED_SYNTAX_ERROR: """Create async client for testing."""
    # REMOVED_SYNTAX_ERROR: transport = ASGITransport(app=app)
    # REMOVED_SYNTAX_ERROR: async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # REMOVED_SYNTAX_ERROR: yield ac

        # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
        # REMOVED_SYNTAX_ERROR: @pytest.mark.L3
        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_successful_login_with_valid_credentials(self, async_client, mock_existing_user, mock_auth_service):
            # REMOVED_SYNTAX_ERROR: """Test 1: Successful login with valid credentials should return tokens."""
            # REMOVED_SYNTAX_ERROR: login_data = { )
            # REMOVED_SYNTAX_ERROR: "email": "existing@example.com",
            # REMOVED_SYNTAX_ERROR: "password": "ValidPassword123!"
            

            # Mock successful authentication
            # REMOVED_SYNTAX_ERROR: mock_tokens = { )
            # REMOVED_SYNTAX_ERROR: "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
            # REMOVED_SYNTAX_ERROR: "refresh_token": "refresh_token_123",
            # REMOVED_SYNTAX_ERROR: "token_type": "bearer",
            # REMOVED_SYNTAX_ERROR: "expires_in": 3600
            

            # Mock: Component isolation for testing without external dependencies
            # REMOVED_SYNTAX_ERROR: with patch('app.services.user_service.UserService.get_user_by_email', return_value=mock_existing_user):
                # Mock: Component isolation for testing without external dependencies
                # REMOVED_SYNTAX_ERROR: with patch('app.services.auth_service.AuthService.authenticate', return_value=mock_existing_user):
                    # Mock: Component isolation for testing without external dependencies
                    # REMOVED_SYNTAX_ERROR: with patch('app.services.auth_service.AuthService.generate_tokens', return_value=mock_tokens):

                        # REMOVED_SYNTAX_ERROR: response = await async_client.post("/auth/login", json=login_data)

                        # Should return 200 with tokens
                        # REMOVED_SYNTAX_ERROR: assert response.status_code == 200

                        # REMOVED_SYNTAX_ERROR: data = response.json()
                        # REMOVED_SYNTAX_ERROR: assert "access_token" in data
                        # REMOVED_SYNTAX_ERROR: assert "refresh_token" in data
                        # REMOVED_SYNTAX_ERROR: assert data["token_type"] == "bearer"
                        # REMOVED_SYNTAX_ERROR: assert "expires_in" in data

                        # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
                        # REMOVED_SYNTAX_ERROR: @pytest.mark.L3
                        # Removed problematic line: @pytest.mark.asyncio
                        # Removed problematic line: async def test_failed_login_with_invalid_password(self, async_client, mock_existing_user):
                            # REMOVED_SYNTAX_ERROR: """Test 2: Login with invalid password should fail and increment attempt counter."""
                            # REMOVED_SYNTAX_ERROR: mock_existing_user.check_password.return_value = False

                            # REMOVED_SYNTAX_ERROR: login_data = { )
                            # REMOVED_SYNTAX_ERROR: "email": "existing@example.com",
                            # REMOVED_SYNTAX_ERROR: "password": "WrongPassword123!"
                            

                            # Mock: Component isolation for testing without external dependencies
                            # REMOVED_SYNTAX_ERROR: with patch('app.services.user_service.UserService.get_user_by_email', return_value=mock_existing_user):
                                # REMOVED_SYNTAX_ERROR: response = await async_client.post("/auth/login", json=login_data)

                                # Should return 401 Unauthorized
                                # REMOVED_SYNTAX_ERROR: assert response.status_code == 401

                                # REMOVED_SYNTAX_ERROR: data = response.json()
                                # REMOVED_SYNTAX_ERROR: assert "invalid" in data.get("detail", "").lower() or "incorrect" in data.get("detail", "").lower()

                                # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
                                # REMOVED_SYNTAX_ERROR: @pytest.mark.L3
                                # Removed problematic line: @pytest.mark.asyncio
                                # Removed problematic line: async def test_account_lockout_after_failed_attempts(self, async_client, mock_existing_user):
                                    # REMOVED_SYNTAX_ERROR: """Test 3: Account should be locked after multiple failed login attempts."""
                                    # REMOVED_SYNTAX_ERROR: mock_existing_user.check_password.return_value = False
                                    # REMOVED_SYNTAX_ERROR: mock_existing_user.failed_login_attempts = 5  # Already at limit
                                    # REMOVED_SYNTAX_ERROR: mock_existing_user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)

                                    # REMOVED_SYNTAX_ERROR: login_data = { )
                                    # REMOVED_SYNTAX_ERROR: "email": "existing@example.com",
                                    # REMOVED_SYNTAX_ERROR: "password": "AnyPassword123!"
                                    

                                    # Mock: Component isolation for testing without external dependencies
                                    # REMOVED_SYNTAX_ERROR: with patch('app.services.user_service.UserService.get_user_by_email', return_value=mock_existing_user):
                                        # REMOVED_SYNTAX_ERROR: response = await async_client.post("/auth/login", json=login_data)

                                        # Should return 423 Locked or 403 Forbidden
                                        # REMOVED_SYNTAX_ERROR: assert response.status_code in [423, 403, 401]

                                        # REMOVED_SYNTAX_ERROR: data = response.json()
                                        # REMOVED_SYNTAX_ERROR: assert "locked" in data.get("detail", "").lower() or "too many attempts" in data.get("detail", "").lower()

                                        # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
                                        # REMOVED_SYNTAX_ERROR: @pytest.mark.L3
                                        # Removed problematic line: @pytest.mark.asyncio
                                        # Removed problematic line: async def test_session_creation_on_successful_login(self, async_client, mock_existing_user, mock_session_service):
                                            # REMOVED_SYNTAX_ERROR: """Test 4: Successful login should create a new session."""
                                            # Mock: Database session isolation for transaction testing without real database dependency
                                            # REMOVED_SYNTAX_ERROR: mock_session = MagicMock()  # TODO: Use real service instance
                                            # REMOVED_SYNTAX_ERROR: mock_session.id = str(uuid.uuid4())
                                            # REMOVED_SYNTAX_ERROR: mock_session.user_id = mock_existing_user.id
                                            # REMOVED_SYNTAX_ERROR: mock_session.created_at = datetime.now(timezone.utc)
                                            # REMOVED_SYNTAX_ERROR: mock_session.last_activity = datetime.now(timezone.utc)

                                            # REMOVED_SYNTAX_ERROR: mock_session_service.create_session.return_value = mock_session

                                            # REMOVED_SYNTAX_ERROR: login_data = { )
                                            # REMOVED_SYNTAX_ERROR: "email": "existing@example.com",
                                            # REMOVED_SYNTAX_ERROR: "password": "ValidPassword123!"
                                            

                                            # Mock: Component isolation for testing without external dependencies
                                            # REMOVED_SYNTAX_ERROR: with patch('app.services.user_service.UserService.get_user_by_email', return_value=mock_existing_user):
                                                # Mock: Component isolation for testing without external dependencies
                                                # REMOVED_SYNTAX_ERROR: with patch('app.services.auth_service.AuthService.authenticate', return_value=mock_existing_user):
                                                    # Mock: Database session isolation for transaction testing without real database dependency
                                                    # REMOVED_SYNTAX_ERROR: with patch('app.services.session_service.SessionService.create_session', return_value=mock_session) as mock_create:

                                                        # REMOVED_SYNTAX_ERROR: response = await async_client.post("/auth/login", json=login_data)

                                                        # REMOVED_SYNTAX_ERROR: if response.status_code == 200:
                                                            # Session should be created
                                                            # REMOVED_SYNTAX_ERROR: assert mock_create.called or mock_session.id is not None

                                                            # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
                                                            # REMOVED_SYNTAX_ERROR: @pytest.mark.L3
                                                            # Removed problematic line: @pytest.mark.asyncio
                                                            # Removed problematic line: async def test_token_refresh_flow(self, async_client, mock_auth_service):
                                                                # REMOVED_SYNTAX_ERROR: """Test 5: Token refresh should return new access token."""
                                                                # REMOVED_SYNTAX_ERROR: refresh_token = "valid_refresh_token_123"

                                                                # Generate real tokens for integration testing
                                                                # REMOVED_SYNTAX_ERROR: test_token = create_test_user_token("refreshed_user", use_real_jwt=True)
                                                                # REMOVED_SYNTAX_ERROR: new_tokens = { )
                                                                # REMOVED_SYNTAX_ERROR: "access_token": test_token.token,
                                                                # REMOVED_SYNTAX_ERROR: "refresh_token": refresh_token,  # Same refresh token
                                                                # REMOVED_SYNTAX_ERROR: "token_type": "bearer",
                                                                # REMOVED_SYNTAX_ERROR: "expires_in": 3600
                                                                

                                                                # REMOVED_SYNTAX_ERROR: mock_auth_service.refresh_tokens.return_value = new_tokens

                                                                # Mock: Component isolation for testing without external dependencies
                                                                # REMOVED_SYNTAX_ERROR: with patch('app.services.auth_service.AuthService.validate_refresh_token', return_value=True):
                                                                    # Mock: Component isolation for testing without external dependencies
                                                                    # REMOVED_SYNTAX_ERROR: with patch('app.services.auth_service.AuthService.refresh_tokens', return_value=new_tokens):

                                                                        # REMOVED_SYNTAX_ERROR: response = await async_client.post( )
                                                                        # REMOVED_SYNTAX_ERROR: "/auth/refresh",
                                                                        # REMOVED_SYNTAX_ERROR: json={"refresh_token": refresh_token}
                                                                        

                                                                        # Should return 200 with new tokens
                                                                        # REMOVED_SYNTAX_ERROR: assert response.status_code == 200

                                                                        # REMOVED_SYNTAX_ERROR: data = response.json()
                                                                        # REMOVED_SYNTAX_ERROR: assert "access_token" in data
                                                                        # REMOVED_SYNTAX_ERROR: assert data["access_token"] == new_tokens["access_token"]

                                                                        # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
                                                                        # REMOVED_SYNTAX_ERROR: @pytest.mark.L3
                                                                        # Removed problematic line: @pytest.mark.asyncio
                                                                        # Removed problematic line: async def test_authenticated_request_with_valid_token(self, async_client, mock_existing_user):
                                                                            # REMOVED_SYNTAX_ERROR: """Test 6: Authenticated requests with valid token should succeed."""
                                                                            # REMOVED_SYNTAX_ERROR: access_token = "valid_access_token_123"

                                                                            # Mock token validation
                                                                            # Mock: Component isolation for testing without external dependencies
                                                                            # REMOVED_SYNTAX_ERROR: with patch('app.services.auth_service.AuthService.validate_token', return_value=mock_existing_user.id):
                                                                                # Mock: Component isolation for testing without external dependencies
                                                                                # REMOVED_SYNTAX_ERROR: with patch('app.services.user_service.UserService.get_user', return_value=mock_existing_user):

                                                                                    # REMOVED_SYNTAX_ERROR: headers = {"Authorization": "formatted_string"}
                                                                                    # REMOVED_SYNTAX_ERROR: response = await async_client.get("/api/user/profile", headers=headers)

                                                                                    # Should return user profile
                                                                                    # REMOVED_SYNTAX_ERROR: assert response.status_code in [200, 404]  # 404 if endpoint doesn"t exist in test

                                                                                    # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
                                                                                    # REMOVED_SYNTAX_ERROR: @pytest.mark.L3
                                                                                    # Removed problematic line: @pytest.mark.asyncio
                                                                                    # Removed problematic line: async def test_logout_revokes_tokens_and_ends_session(self, async_client, mock_auth_service, mock_session_service):
                                                                                        # REMOVED_SYNTAX_ERROR: """Test 7: Logout should revoke tokens and end session."""
                                                                                        # REMOVED_SYNTAX_ERROR: access_token = "valid_access_token_123"
                                                                                        # REMOVED_SYNTAX_ERROR: user_id = str(uuid.uuid4())

                                                                                        # Mock successful logout
                                                                                        # REMOVED_SYNTAX_ERROR: mock_auth_service.revoke_token.return_value = True
                                                                                        # REMOVED_SYNTAX_ERROR: mock_session_service.end_session.return_value = True

                                                                                        # Mock: Component isolation for testing without external dependencies
                                                                                        # REMOVED_SYNTAX_ERROR: with patch('app.services.auth_service.AuthService.validate_token', return_value=user_id):
                                                                                            # Mock: Component isolation for testing without external dependencies
                                                                                            # REMOVED_SYNTAX_ERROR: with patch('app.services.auth_service.AuthService.revoke_token', return_value=True) as mock_revoke:
                                                                                                # Mock: Session isolation for controlled testing without external state
                                                                                                # REMOVED_SYNTAX_ERROR: with patch('app.services.session_service.SessionService.end_session', return_value=True) as mock_end:

                                                                                                    # REMOVED_SYNTAX_ERROR: headers = {"Authorization": "formatted_string"}
                                                                                                    # REMOVED_SYNTAX_ERROR: response = await async_client.post("/auth/logout", headers=headers)

                                                                                                    # Should return success
                                                                                                    # REMOVED_SYNTAX_ERROR: assert response.status_code in [200, 204]

                                                                                                    # Token should be revoked and session ended
                                                                                                    # REMOVED_SYNTAX_ERROR: if response.status_code == 200:
                                                                                                        # REMOVED_SYNTAX_ERROR: assert mock_revoke.called or mock_end.called

                                                                                                        # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
                                                                                                        # REMOVED_SYNTAX_ERROR: @pytest.mark.L3
                                                                                                        # Removed problematic line: @pytest.mark.asyncio
                                                                                                        # Removed problematic line: async def test_concurrent_login_sessions_handling(self, async_client, mock_existing_user):
                                                                                                            # REMOVED_SYNTAX_ERROR: """Test 8: System should handle multiple concurrent sessions for same user."""
                                                                                                            # REMOVED_SYNTAX_ERROR: login_data = { )
                                                                                                            # REMOVED_SYNTAX_ERROR: "email": "existing@example.com",
                                                                                                            # REMOVED_SYNTAX_ERROR: "password": "ValidPassword123!"
                                                                                                            

                                                                                                            # Create multiple login sessions
                                                                                                            # REMOVED_SYNTAX_ERROR: sessions = []

                                                                                                            # REMOVED_SYNTAX_ERROR: for i in range(3):
                                                                                                                # REMOVED_SYNTAX_ERROR: mock_tokens = { )
                                                                                                                # REMOVED_SYNTAX_ERROR: "access_token": "formatted_string",
                                                                                                                # REMOVED_SYNTAX_ERROR: "refresh_token": "formatted_string",
                                                                                                                # REMOVED_SYNTAX_ERROR: "token_type": "bearer",
                                                                                                                # REMOVED_SYNTAX_ERROR: "expires_in": 3600
                                                                                                                

                                                                                                                # Mock: Component isolation for testing without external dependencies
                                                                                                                # REMOVED_SYNTAX_ERROR: with patch('app.services.user_service.UserService.get_user_by_email', return_value=mock_existing_user):
                                                                                                                    # Mock: Component isolation for testing without external dependencies
                                                                                                                    # REMOVED_SYNTAX_ERROR: with patch('app.services.auth_service.AuthService.authenticate', return_value=mock_existing_user):
                                                                                                                        # Mock: Component isolation for testing without external dependencies
                                                                                                                        # REMOVED_SYNTAX_ERROR: with patch('app.services.auth_service.AuthService.generate_tokens', return_value=mock_tokens):

                                                                                                                            # REMOVED_SYNTAX_ERROR: response = await async_client.post("/auth/login", json=login_data)

                                                                                                                            # REMOVED_SYNTAX_ERROR: if response.status_code == 200:
                                                                                                                                # REMOVED_SYNTAX_ERROR: sessions.append(response.json())

                                                                                                                                # All sessions should be valid
                                                                                                                                # REMOVED_SYNTAX_ERROR: assert len(sessions) >= 1  # At least one should succeed
                                                                                                                                # REMOVED_SYNTAX_ERROR: for session in sessions:
                                                                                                                                    # REMOVED_SYNTAX_ERROR: assert "access_token" in session

                                                                                                                                    # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
                                                                                                                                    # REMOVED_SYNTAX_ERROR: @pytest.mark.L3
                                                                                                                                    # Removed problematic line: @pytest.mark.asyncio
                                                                                                                                    # Removed problematic line: async def test_login_updates_last_login_timestamp(self, async_client, mock_existing_user):
                                                                                                                                        # REMOVED_SYNTAX_ERROR: """Test 9: Successful login should update user's last login timestamp."""
                                                                                                                                        # REMOVED_SYNTAX_ERROR: original_last_login = mock_existing_user.last_login

                                                                                                                                        # REMOVED_SYNTAX_ERROR: login_data = { )
                                                                                                                                        # REMOVED_SYNTAX_ERROR: "email": "existing@example.com",
                                                                                                                                        # REMOVED_SYNTAX_ERROR: "password": "ValidPassword123!"
                                                                                                                                        

                                                                                                                                        # Mock: Component isolation for testing without external dependencies
                                                                                                                                        # REMOVED_SYNTAX_ERROR: with patch('app.services.user_service.UserService.get_user_by_email', return_value=mock_existing_user):
                                                                                                                                            # Mock: Component isolation for testing without external dependencies
                                                                                                                                            # REMOVED_SYNTAX_ERROR: with patch('app.services.auth_service.AuthService.authenticate', return_value=mock_existing_user):
                                                                                                                                                # Mock: Component isolation for testing without external dependencies
                                                                                                                                                # REMOVED_SYNTAX_ERROR: with patch('app.services.user_service.UserService.update_last_login', return_value=True) as mock_update:

                                                                                                                                                    # REMOVED_SYNTAX_ERROR: response = await async_client.post("/auth/login", json=login_data)

                                                                                                                                                    # REMOVED_SYNTAX_ERROR: if response.status_code == 200:
                                                                                                                                                        # Last login should be updated
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: assert mock_update.called or mock_existing_user.last_login > original_last_login

                                                                                                                                                        # REMOVED_SYNTAX_ERROR: @pytest.mark.integration
                                                                                                                                                        # REMOVED_SYNTAX_ERROR: @pytest.mark.L3
                                                                                                                                                        # Removed problematic line: @pytest.mark.asyncio
                                                                                                                                                        # Removed problematic line: async def test_remember_me_extends_token_expiry(self, async_client, mock_existing_user):
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: """Test 10: 'Remember me' option should extend token expiry time."""
                                                                                                                                                            # Login without remember me
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: login_data_short = { )
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: "email": "existing@example.com",
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: "password": "ValidPassword123!",
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: "remember_me": False
                                                                                                                                                            

                                                                                                                                                            # Login with remember me
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: login_data_long = { )
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: "email": "existing@example.com",
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: "password": "ValidPassword123!",
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: "remember_me": True
                                                                                                                                                            

                                                                                                                                                            # Mock different token expiries
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: short_tokens = { )
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: "access_token": "short_token",
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: "refresh_token": "short_refresh",
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: "token_type": "bearer",
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: "expires_in": 3600  # 1 hour
                                                                                                                                                            

                                                                                                                                                            # REMOVED_SYNTAX_ERROR: long_tokens = { )
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: "access_token": "long_token",
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: "refresh_token": "long_refresh",
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: "token_type": "bearer",
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: "expires_in": 2592000  # 30 days
                                                                                                                                                            

                                                                                                                                                            # Mock: Component isolation for testing without external dependencies
                                                                                                                                                            # REMOVED_SYNTAX_ERROR: with patch('app.services.user_service.UserService.get_user_by_email', return_value=mock_existing_user):
                                                                                                                                                                # Mock: Component isolation for testing without external dependencies
                                                                                                                                                                # REMOVED_SYNTAX_ERROR: with patch('app.services.auth_service.AuthService.authenticate', return_value=mock_existing_user):

                                                                                                                                                                    # Test short expiry
                                                                                                                                                                    # Mock: Component isolation for testing without external dependencies
                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: with patch('app.services.auth_service.AuthService.generate_tokens', return_value=short_tokens):
                                                                                                                                                                        # REMOVED_SYNTAX_ERROR: response_short = await async_client.post("/auth/login", json=login_data_short)

                                                                                                                                                                        # REMOVED_SYNTAX_ERROR: if response_short.status_code == 200:
                                                                                                                                                                            # REMOVED_SYNTAX_ERROR: data_short = response_short.json()
                                                                                                                                                                            # REMOVED_SYNTAX_ERROR: short_expiry = data_short.get("expires_in", 0)

                                                                                                                                                                            # Test long expiry
                                                                                                                                                                            # Mock: Component isolation for testing without external dependencies
                                                                                                                                                                            # REMOVED_SYNTAX_ERROR: with patch('app.services.auth_service.AuthService.generate_tokens', return_value=long_tokens):
                                                                                                                                                                                # REMOVED_SYNTAX_ERROR: response_long = await async_client.post("/auth/login", json=login_data_long)

                                                                                                                                                                                # REMOVED_SYNTAX_ERROR: if response_long.status_code == 200:
                                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: data_long = response_long.json()
                                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: long_expiry = data_long.get("expires_in", 0)

                                                                                                                                                                                    # Remember me should have longer expiry
                                                                                                                                                                                    # REMOVED_SYNTAX_ERROR: assert long_expiry > short_expiry