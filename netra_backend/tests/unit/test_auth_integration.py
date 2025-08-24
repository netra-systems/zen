"""Unit tests for Auth Integration module.

Tests authentication integration with external auth service.
HIGHEST PRIORITY - Auth failures = 100% revenue loss.

Business Value: Ensures proper token validation, user retrieval, and error handling
for all authenticated endpoints. Protects against unauthorized access.

Target Coverage:
- get_current_user: token validation and database lookup
- get_current_user_optional: optional authentication flow  
- Permission-based dependencies: admin, developer, custom permissions
- Error scenarios: 401 Unauthorized, 404 User Not Found, service failures
"""

import sys
from pathlib import Path

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.auth_integration.auth import (
    create_access_token,
    get_current_user,
    get_current_user_optional,
    get_password_hash,
    require_admin,
    require_developer,
    require_permission,
    validate_token_jwt,
    verify_password,
)
from netra_backend.app.clients.auth_client import auth_client
from netra_backend.app.db.models_postgres import User

class TestAuthIntegration:
    """Test suite for Auth Integration functionality."""
    
    @pytest.fixture
    def mock_credentials(self):
        """Create mock HTTP authorization credentials."""
        # Mock: Authentication service isolation for testing without real auth flows
        credentials = Mock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = "valid-jwt-token-123"
        return credentials
    
    @pytest.fixture
    def mock_auth_client(self):
        """Create mock auth client with common responses."""
        with patch.object(auth_client, 'validate_token', new_callable=AsyncMock) as mock:
            yield mock
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock async database session."""
        # Mock: Database session isolation for transaction testing without real database dependency
        session = AsyncMock(spec=AsyncSession)
        # Mock: Database session isolation for transaction testing without real database dependency
        session.__aenter__ = AsyncMock(return_value=session)
        # Mock: Session isolation for controlled testing without external state
        session.__aexit__ = AsyncMock(return_value=None)
        return session
    
    @pytest.fixture
    def sample_user(self):
        """Create sample user for testing."""
        user = User()
        user.id = "test-user-123"
        user.email = "test@example.com"
        user.is_admin = False
        user.is_developer = False
        user.permissions = ["read", "write"]
        return user

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token_success(self, mock_credentials, mock_auth_client, mock_db_session, sample_user):
        """Test successful user retrieval with valid token."""
        self._setup_successful_auth_flow(mock_auth_client, mock_db_session, sample_user)
        
        result = await get_current_user(mock_credentials, mock_db_session)
        
        assert result == sample_user
        mock_auth_client.assert_called_once_with("valid-jwt-token-123")
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token_raises_401(self, mock_credentials, mock_auth_client, mock_db_session):
        """Test 401 error with invalid token."""
        mock_auth_client.return_value = {"valid": False}
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_credentials, mock_db_session)
        
        self._assert_401_unauthorized(exc_info)

    @pytest.mark.asyncio
    async def test_get_current_user_no_token_validation_raises_401(self, mock_credentials, mock_auth_client, mock_db_session):
        """Test 401 error when auth service returns None."""
        mock_auth_client.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_credentials, mock_db_session)
        
        self._assert_401_unauthorized(exc_info)

    @pytest.mark.asyncio
    async def test_get_current_user_missing_user_id_raises_401(self, mock_credentials, mock_auth_client, mock_db_session):
        """Test 401 error when token payload lacks user_id."""
        mock_auth_client.return_value = {"valid": True}  # No user_id
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_credentials, mock_db_session)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token payload" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_user_not_found_raises_404(self, mock_credentials, mock_auth_client, mock_db_session):
        """Test 404 error when user not found in database."""
        self._setup_auth_client_valid_response(mock_auth_client)
        self._setup_db_session_no_user(mock_db_session)
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_credentials, mock_db_session)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "User not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_optional_valid_credentials_returns_user(self, mock_credentials, mock_auth_client, mock_db_session, sample_user):
        """Test optional auth returns user with valid credentials."""
        # Mock: Async component isolation for testing without real async operations
        with patch('app.auth_integration.auth.get_current_user', new_callable=AsyncMock) as mock_get_user:
            mock_get_user.return_value = sample_user
            
            result = await get_current_user_optional(mock_credentials, mock_db_session)
            
            assert result == sample_user

    @pytest.mark.asyncio
    async def test_get_current_user_optional_no_credentials_returns_none(self, mock_db_session):
        """Test optional auth returns None with no credentials."""
        result = await get_current_user_optional(None, mock_db_session)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_current_user_optional_invalid_credentials_returns_none(self, mock_credentials, mock_db_session):
        """Test optional auth returns None when authentication fails."""
        # Mock: Async component isolation for testing without real async operations
        with patch('app.auth_integration.auth.get_current_user', new_callable=AsyncMock) as mock_get_user:
            mock_get_user.side_effect = HTTPException(status_code=401, detail="Invalid token")
            
            result = await get_current_user_optional(mock_credentials, mock_db_session)
            
            assert result is None

    @pytest.mark.asyncio
    async def test_require_admin_with_admin_user_success(self, sample_user):
        """Test admin requirement with admin user."""
        sample_user.is_admin = True
        
        result = await require_admin(sample_user)
        
        assert result == sample_user

    @pytest.mark.asyncio
    async def test_require_admin_with_non_admin_user_raises_403(self, sample_user):
        """Test admin requirement with non-admin user."""
        sample_user.is_admin = False
        
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(sample_user)
        
        self._assert_403_forbidden(exc_info, "Admin access required")

    @pytest.mark.asyncio
    async def test_require_developer_with_developer_user_success(self, sample_user):
        """Test developer requirement with developer user."""
        sample_user.is_developer = True
        
        result = await require_developer(sample_user)
        
        assert result == sample_user

    @pytest.mark.asyncio
    async def test_require_developer_with_non_developer_user_raises_403(self, sample_user):
        """Test developer requirement with non-developer user."""
        sample_user.is_developer = False
        
        with pytest.raises(HTTPException) as exc_info:
            await require_developer(sample_user)
        
        self._assert_403_forbidden(exc_info, "Developer access required")

    @pytest.mark.asyncio
    async def test_require_permission_with_valid_permission_success(self, sample_user):
        """Test permission requirement with valid permission."""
        check_permission = require_permission("read")
        
        result = await check_permission(sample_user)
        
        assert result == sample_user

    @pytest.mark.asyncio
    async def test_require_permission_with_invalid_permission_raises_403(self, sample_user):
        """Test permission requirement with missing permission."""
        check_permission = require_permission("admin")
        
        with pytest.raises(HTTPException) as exc_info:
            await check_permission(sample_user)
        
        self._assert_403_forbidden(exc_info, "Permission 'admin' required")

    def test_password_hashing_and_verification_success(self):
        """Test password hashing and successful verification."""
        password = "test-password-123"
        
        hashed = get_password_hash(password)
        is_valid = verify_password(password, hashed)
        
        assert isinstance(hashed, str)
        assert is_valid is True

    def test_password_verification_wrong_password_fails(self):
        """Test password verification with wrong password."""
        password = "correct-password"
        wrong_password = "wrong-password"
        hashed = get_password_hash(password)
        
        is_valid = verify_password(wrong_password, hashed)
        
        assert is_valid is False

    def test_create_access_token_default_expiry(self):
        """Test JWT token creation with default expiry."""
        data = {"user_id": "test-123", "email": "test@example.com"}
        
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 20  # JWT tokens are longer

    def test_create_access_token_custom_expiry(self):
        """Test JWT token creation with custom expiry."""
        data = {"user_id": "test-123"}
        expires_delta = timedelta(hours=1)
        
        token = create_access_token(data, expires_delta)
        
        assert isinstance(token, str)

    def test_validate_token_jwt_valid_token_success(self):
        """Test JWT token validation with valid token."""
        data = {"user_id": "test-123", "email": "test@example.com"}
        token = create_access_token(data, timedelta(minutes=5))
        
        payload = validate_token_jwt(token)
        
        assert payload is not None
        assert payload["user_id"] == "test-123"
        assert payload["email"] == "test@example.com"

    def test_validate_token_jwt_invalid_token_returns_none(self):
        """Test JWT token validation with invalid token."""
        invalid_token = "invalid.jwt.token"
        
        payload = validate_token_jwt(invalid_token)
        
        assert payload is None

    def test_validate_token_jwt_expired_token_returns_none(self):
        """Test JWT token validation with expired token."""
        data = {"user_id": "test-123"}
        
        # Mock: Component isolation for testing without external dependencies
        with patch('app.auth_integration.auth.datetime') as mock_datetime:
            past_time = datetime.utcnow() - timedelta(hours=1)
            mock_datetime.utcnow.return_value = past_time
            token = create_access_token(data, timedelta(minutes=5))
        
        payload = validate_token_jwt(token)
        
        assert payload is None

    # Helper methods (each ≤8 lines)
    def _setup_successful_auth_flow(self, mock_auth_client, mock_db_session, user):
        """Setup successful authentication flow."""
        self._setup_auth_client_valid_response(mock_auth_client)
        self._setup_db_session_with_user(mock_db_session, user)

    def _setup_auth_client_valid_response(self, mock_auth_client):
        """Setup auth client to return valid response."""
        mock_auth_client.return_value = {
            "valid": True,
            "user_id": "test-user-123"
        }

    def _setup_db_session_with_user(self, mock_db_session, user):
        """Setup database session to return user."""
        # Mock: Generic component isolation for controlled unit testing
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db_session.execute.return_value = mock_result

    def _setup_db_session_no_user(self, mock_db_session):
        """Setup database session to return no user."""
        # Mock: Generic component isolation for controlled unit testing
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

    def _assert_401_unauthorized(self, exc_info):
        """Assert 401 Unauthorized exception details."""
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid or expired token" in exc_info.value.detail
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}

    def _assert_403_forbidden(self, exc_info, expected_detail):
        """Assert 403 Forbidden exception details."""
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert expected_detail in exc_info.value.detail