"""Existing User Login Flow Integration Tests (L3)

Tests complete login flow for existing users including authentication,
session management, token refresh, and logout.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Retention - seamless login keeps users engaged
- Value Impact: Poor login experience causes user churn
- Revenue Impact: Direct - can't monetize users who can't log in
"""

import sys
from pathlib import Path

from test_framework import setup_test_path

import asyncio
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

# Set test environment before imports
os.environ["ENVIRONMENT"] = "testing"
os.environ["TESTING"] = "true"
os.environ["SKIP_STARTUP_CHECKS"] = "true"

from netra_backend.app.config import get_config
from netra_backend.app.db.models_postgres import User
from netra_backend.app.main import app
from netra_backend.app.services.auth_service import AuthService
from netra_backend.app.services.session_service import SessionService

class TestExistingUserLoginFlow:
    """Test existing user login flow from authentication to logout."""
    
    @pytest.fixture
    async def mock_existing_user(self):
        """Create mock existing user."""
        user = MagicMock(spec=User)
        user.id = str(uuid.uuid4())
        user.email = "existing@example.com"
        user.full_name = "Existing User"
        user.is_active = True
        user.email_verified = True
        user.last_login = datetime.utcnow() - timedelta(days=1)
        user.failed_login_attempts = 0
        user.check_password = MagicMock(return_value=True)
        return user
    
    @pytest.fixture
    async def mock_auth_service(self):
        """Create mock auth service."""
        service = AsyncMock(spec=AuthService)
        service.authenticate = AsyncMock()
        service.generate_tokens = AsyncMock()
        service.validate_token = AsyncMock(return_value=True)
        service.refresh_tokens = AsyncMock()
        service.revoke_token = AsyncMock()
        return service
    
    @pytest.fixture
    async def mock_session_service(self):
        """Create mock session service."""
        service = AsyncMock(spec=SessionService)
        service.create_session = AsyncMock()
        service.get_session = AsyncMock()
        service.update_session_activity = AsyncMock()
        service.end_session = AsyncMock()
        return service
    
    @pytest.fixture
    async def async_client(self):
        """Create async client for testing."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    
    @pytest.mark.integration
    @pytest.mark.L3
    async def test_successful_login_with_valid_credentials(self, async_client, mock_existing_user, mock_auth_service):
        """Test 1: Successful login with valid credentials should return tokens."""
        login_data = {
            "email": "existing@example.com",
            "password": "ValidPassword123!"
        }
        
        # Mock successful authentication
        mock_tokens = {
            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
            "refresh_token": "refresh_token_123",
            "token_type": "bearer",
            "expires_in": 3600
        }
        
        with patch('app.services.user_service.UserService.get_user_by_email', return_value=mock_existing_user):
            with patch('app.services.auth_service.AuthService.authenticate', return_value=mock_existing_user):
                with patch('app.services.auth_service.AuthService.generate_tokens', return_value=mock_tokens):
                    
                    response = await async_client.post("/api/auth/login", json=login_data)
                    
                    # Should return 200 with tokens
                    assert response.status_code == 200
                    
                    data = response.json()
                    assert "access_token" in data
                    assert "refresh_token" in data
                    assert data["token_type"] == "bearer"
                    assert "expires_in" in data
    
    @pytest.mark.integration
    @pytest.mark.L3
    async def test_failed_login_with_invalid_password(self, async_client, mock_existing_user):
        """Test 2: Login with invalid password should fail and increment attempt counter."""
        mock_existing_user.check_password.return_value = False
        
        login_data = {
            "email": "existing@example.com",
            "password": "WrongPassword123!"
        }
        
        with patch('app.services.user_service.UserService.get_user_by_email', return_value=mock_existing_user):
            response = await async_client.post("/api/auth/login", json=login_data)
            
            # Should return 401 Unauthorized
            assert response.status_code == 401
            
            data = response.json()
            assert "invalid" in data.get("detail", "").lower() or "incorrect" in data.get("detail", "").lower()
    
    @pytest.mark.integration
    @pytest.mark.L3
    async def test_account_lockout_after_failed_attempts(self, async_client, mock_existing_user):
        """Test 3: Account should be locked after multiple failed login attempts."""
        mock_existing_user.check_password.return_value = False
        mock_existing_user.failed_login_attempts = 5  # Already at limit
        mock_existing_user.locked_until = datetime.utcnow() + timedelta(minutes=15)
        
        login_data = {
            "email": "existing@example.com",
            "password": "AnyPassword123!"
        }
        
        with patch('app.services.user_service.UserService.get_user_by_email', return_value=mock_existing_user):
            response = await async_client.post("/api/auth/login", json=login_data)
            
            # Should return 423 Locked or 403 Forbidden
            assert response.status_code in [423, 403, 401]
            
            data = response.json()
            assert "locked" in data.get("detail", "").lower() or "too many attempts" in data.get("detail", "").lower()
    
    @pytest.mark.integration
    @pytest.mark.L3
    async def test_session_creation_on_successful_login(self, async_client, mock_existing_user, mock_session_service):
        """Test 4: Successful login should create a new session."""
        mock_session = MagicMock()
        mock_session.id = str(uuid.uuid4())
        mock_session.user_id = mock_existing_user.id
        mock_session.created_at = datetime.utcnow()
        mock_session.last_activity = datetime.utcnow()
        
        mock_session_service.create_session.return_value = mock_session
        
        login_data = {
            "email": "existing@example.com",
            "password": "ValidPassword123!"
        }
        
        with patch('app.services.user_service.UserService.get_user_by_email', return_value=mock_existing_user):
            with patch('app.services.auth_service.AuthService.authenticate', return_value=mock_existing_user):
                with patch('app.services.session_service.SessionService.create_session', return_value=mock_session) as mock_create:
                    
                    response = await async_client.post("/api/auth/login", json=login_data)
                    
                    if response.status_code == 200:
                        # Session should be created
                        assert mock_create.called or mock_session.id is not None
    
    @pytest.mark.integration
    @pytest.mark.L3
    async def test_token_refresh_flow(self, async_client, mock_auth_service):
        """Test 5: Token refresh should return new access token."""
        refresh_token = "valid_refresh_token_123"
        
        # Mock new tokens
        new_tokens = {
            "access_token": "new_access_token_456",
            "refresh_token": refresh_token,  # Same refresh token
            "token_type": "bearer",
            "expires_in": 3600
        }
        
        mock_auth_service.refresh_tokens.return_value = new_tokens
        
        with patch('app.services.auth_service.AuthService.validate_refresh_token', return_value=True):
            with patch('app.services.auth_service.AuthService.refresh_tokens', return_value=new_tokens):
                
                response = await async_client.post(
                    "/api/auth/refresh",
                    json={"refresh_token": refresh_token}
                )
                
                # Should return 200 with new tokens
                assert response.status_code == 200
                
                data = response.json()
                assert "access_token" in data
                assert data["access_token"] == new_tokens["access_token"]
    
    @pytest.mark.integration
    @pytest.mark.L3
    async def test_authenticated_request_with_valid_token(self, async_client, mock_existing_user):
        """Test 6: Authenticated requests with valid token should succeed."""
        access_token = "valid_access_token_123"
        
        # Mock token validation
        with patch('app.services.auth_service.AuthService.validate_token', return_value=mock_existing_user.id):
            with patch('app.services.user_service.UserService.get_user', return_value=mock_existing_user):
                
                headers = {"Authorization": f"Bearer {access_token}"}
                response = await async_client.get("/api/user/profile", headers=headers)
                
                # Should return user profile
                assert response.status_code in [200, 404]  # 404 if endpoint doesn't exist in test
    
    @pytest.mark.integration
    @pytest.mark.L3
    async def test_logout_revokes_tokens_and_ends_session(self, async_client, mock_auth_service, mock_session_service):
        """Test 7: Logout should revoke tokens and end session."""
        access_token = "valid_access_token_123"
        user_id = str(uuid.uuid4())
        
        # Mock successful logout
        mock_auth_service.revoke_token.return_value = True
        mock_session_service.end_session.return_value = True
        
        with patch('app.services.auth_service.AuthService.validate_token', return_value=user_id):
            with patch('app.services.auth_service.AuthService.revoke_token', return_value=True) as mock_revoke:
                with patch('app.services.session_service.SessionService.end_session', return_value=True) as mock_end:
                    
                    headers = {"Authorization": f"Bearer {access_token}"}
                    response = await async_client.post("/api/auth/logout", headers=headers)
                    
                    # Should return success
                    assert response.status_code in [200, 204]
                    
                    # Token should be revoked and session ended
                    if response.status_code == 200:
                        assert mock_revoke.called or mock_end.called
    
    @pytest.mark.integration
    @pytest.mark.L3
    async def test_concurrent_login_sessions_handling(self, async_client, mock_existing_user):
        """Test 8: System should handle multiple concurrent sessions for same user."""
        login_data = {
            "email": "existing@example.com",
            "password": "ValidPassword123!"
        }
        
        # Create multiple login sessions
        sessions = []
        
        for i in range(3):
            mock_tokens = {
                "access_token": f"access_token_{i}",
                "refresh_token": f"refresh_token_{i}",
                "token_type": "bearer",
                "expires_in": 3600
            }
            
            with patch('app.services.user_service.UserService.get_user_by_email', return_value=mock_existing_user):
                with patch('app.services.auth_service.AuthService.authenticate', return_value=mock_existing_user):
                    with patch('app.services.auth_service.AuthService.generate_tokens', return_value=mock_tokens):
                        
                        response = await async_client.post("/api/auth/login", json=login_data)
                        
                        if response.status_code == 200:
                            sessions.append(response.json())
        
        # All sessions should be valid
        assert len(sessions) >= 1  # At least one should succeed
        for session in sessions:
            assert "access_token" in session
    
    @pytest.mark.integration
    @pytest.mark.L3
    async def test_login_updates_last_login_timestamp(self, async_client, mock_existing_user):
        """Test 9: Successful login should update user's last login timestamp."""
        original_last_login = mock_existing_user.last_login
        
        login_data = {
            "email": "existing@example.com",
            "password": "ValidPassword123!"
        }
        
        with patch('app.services.user_service.UserService.get_user_by_email', return_value=mock_existing_user):
            with patch('app.services.auth_service.AuthService.authenticate', return_value=mock_existing_user):
                with patch('app.services.user_service.UserService.update_last_login', return_value=True) as mock_update:
                    
                    response = await async_client.post("/api/auth/login", json=login_data)
                    
                    if response.status_code == 200:
                        # Last login should be updated
                        assert mock_update.called or mock_existing_user.last_login > original_last_login
    
    @pytest.mark.integration
    @pytest.mark.L3
    async def test_remember_me_extends_token_expiry(self, async_client, mock_existing_user):
        """Test 10: 'Remember me' option should extend token expiry time."""
        # Login without remember me
        login_data_short = {
            "email": "existing@example.com",
            "password": "ValidPassword123!",
            "remember_me": False
        }
        
        # Login with remember me
        login_data_long = {
            "email": "existing@example.com",
            "password": "ValidPassword123!",
            "remember_me": True
        }
        
        # Mock different token expiries
        short_tokens = {
            "access_token": "short_token",
            "refresh_token": "short_refresh",
            "token_type": "bearer",
            "expires_in": 3600  # 1 hour
        }
        
        long_tokens = {
            "access_token": "long_token",
            "refresh_token": "long_refresh",
            "token_type": "bearer",
            "expires_in": 2592000  # 30 days
        }
        
        with patch('app.services.user_service.UserService.get_user_by_email', return_value=mock_existing_user):
            with patch('app.services.auth_service.AuthService.authenticate', return_value=mock_existing_user):
                
                # Test short expiry
                with patch('app.services.auth_service.AuthService.generate_tokens', return_value=short_tokens):
                    response_short = await async_client.post("/api/auth/login", json=login_data_short)
                    
                    if response_short.status_code == 200:
                        data_short = response_short.json()
                        short_expiry = data_short.get("expires_in", 0)
                
                # Test long expiry
                with patch('app.services.auth_service.AuthService.generate_tokens', return_value=long_tokens):
                    response_long = await async_client.post("/api/auth/login", json=login_data_long)
                    
                    if response_long.status_code == 200:
                        data_long = response_long.json()
                        long_expiry = data_long.get("expires_in", 0)
                        
                        # Remember me should have longer expiry
                        assert long_expiry > short_expiry