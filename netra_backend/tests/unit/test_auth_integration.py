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
from unittest.mock import AsyncMock, MagicMock, Mock, patch

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
from netra_backend.app.clients.auth_client_core import auth_client
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
        with patch('netra_backend.app.auth_integration.auth.auth_client.validate_token_jwt', new_callable=AsyncMock) as mock:
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
        
        # Mock config to be production so it doesn't create dev users
        with patch('netra_backend.app.config.get_config') as mock_config:
            mock_config.return_value.environment = "production"
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials, mock_db_session)
            
            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert "User not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_optional_valid_credentials_returns_user(self, mock_credentials, mock_auth_client, mock_db_session, sample_user):
        """Test optional auth returns user with valid credentials."""
        # Mock: Async component isolation for testing without real async operations
        with patch('netra_backend.app.auth_integration.auth.get_current_user', new_callable=AsyncMock) as mock_get_user:
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
        with patch('netra_backend.app.auth_integration.auth.get_current_user', new_callable=AsyncMock) as mock_get_user:
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

    @pytest.mark.asyncio
    async def test_get_current_user_auth_service_failure(self, mock_credentials, mock_auth_client, mock_db_session):
        """Test handling of auth service failure during token validation."""
        # Mock auth service exception
        mock_auth_client.side_effect = Exception("Auth service unavailable")
        
        with pytest.raises(Exception, match="Auth service unavailable"):
            await get_current_user(mock_credentials, mock_db_session)
            
    @pytest.mark.asyncio
    async def test_get_current_user_database_failure(self, mock_credentials, mock_auth_client, mock_db_session):
        """Test handling of database failure during user lookup."""
        self._setup_auth_client_valid_response(mock_auth_client)
        # Mock database exception
        mock_db_session.execute.side_effect = Exception("Database connection failed")
        
        with pytest.raises(Exception, match="Database connection failed"):
            await get_current_user(mock_credentials, mock_db_session)
            
    @pytest.mark.asyncio
    async def test_get_current_user_dev_mode_creates_user(self, mock_credentials, mock_auth_client, mock_db_session):
        """Test that development mode creates user when not found."""
        self._setup_auth_client_valid_response(mock_auth_client)
        self._setup_db_session_no_user(mock_db_session)
        
        # Mock config to be development
        with patch('netra_backend.app.config.get_config') as mock_config, \
             patch('netra_backend.app.services.user_service.user_service.get_or_create_dev_user', new_callable=AsyncMock) as mock_create_user:
            
            mock_config.return_value.environment = "development"
            
            dev_user = User()
            dev_user.id = "test-user-123"
            dev_user.email = "dev@example.com"
            mock_create_user.return_value = dev_user
            
            result = await get_current_user(mock_credentials, mock_db_session)
            
            assert result == dev_user
            mock_create_user.assert_called_once()
            
    def test_permission_validation_helper_with_valid_permission(self, sample_user):
        """Test internal permission validation helper function."""
        # Should not raise exception for valid permission
        try:
            from netra_backend.app.auth_integration.auth import _validate_user_permission
            _validate_user_permission(sample_user, "read")
            assert True  # No exception raised
        except ImportError:
            pytest.skip("Permission validation helper not available")
            
    def test_permission_validation_helper_with_invalid_permission(self, sample_user):
        """Test internal permission validation helper function with invalid permission."""
        try:
            from netra_backend.app.auth_integration.auth import _validate_user_permission
            with pytest.raises(HTTPException) as exc_info:
                _validate_user_permission(sample_user, "invalid_permission")
            self._assert_403_forbidden(exc_info, "Permission 'invalid_permission' required")
        except ImportError:
            pytest.skip("Permission validation helper not available")
            
    def test_permission_validation_helper_user_without_permissions(self):
        """Test permission validation with user that has no permissions attribute."""
        try:
            from netra_backend.app.auth_integration.auth import _validate_user_permission
            user_no_permissions = User()
            user_no_permissions.id = "no-perms-user"
            # No permissions attribute
            
            # Should not raise exception if user doesn't have permissions attribute
            _validate_user_permission(user_no_permissions, "any_permission")
            assert True  # Should complete without error
        except ImportError:
            pytest.skip("Permission validation helper not available")
            
    @pytest.mark.asyncio
    async def test_require_admin_with_superuser(self):
        """Test admin requirement with superuser flag."""
        user = User()
        user.id = "superuser-123"
        user.is_superuser = True
        user.is_admin = False  # Legacy flag is false
        
        result = await require_admin(user)
        assert result == user
        
    @pytest.mark.asyncio
    async def test_require_admin_with_role_based_admin(self):
        """Test admin requirement with admin role."""
        user = User()
        user.id = "role-admin-123"
        user.role = "admin"
        user.is_admin = False
        user.is_superuser = False
        
        result = await require_admin(user)
        assert result == user
        
    @pytest.mark.asyncio
    async def test_require_admin_with_super_admin_role(self):
        """Test admin requirement with super_admin role."""
        user = User()
        user.id = "super-admin-123"
        user.role = "super_admin"
        user.is_admin = False
        
        result = await require_admin(user)
        assert result == user
        
    @pytest.mark.asyncio
    async def test_require_developer_user_without_developer_attribute(self):
        """Test developer requirement with user that has no is_developer attribute."""
        user = User()
        user.id = "no-dev-attr-123"
        # No is_developer attribute
        
        with pytest.raises(HTTPException) as exc_info:
            await require_developer(user)
            
        self._assert_403_forbidden(exc_info, "Developer access required")
        
    def test_auth_client_instance_exists(self):
        """Test that auth client instance is properly initialized."""
        from netra_backend.app.auth_integration.auth import auth_client
        assert auth_client is not None
        assert hasattr(auth_client, 'validate_token_jwt')
        
    def test_security_bearer_instance(self):
        """Test that HTTPBearer security instance is properly configured."""
        from netra_backend.app.auth_integration.auth import security
        assert security is not None
        assert isinstance(security, HTTPBearer)
        
    def test_dependency_annotations_exist(self):
        """Test that FastAPI dependency annotations are properly defined."""
        from netra_backend.app.auth_integration.auth import ActiveUserDep, OptionalUserDep, AdminDep, DeveloperDep
        
        # These should be properly typed annotations
        assert ActiveUserDep is not None
        assert OptionalUserDep is not None
        assert AdminDep is not None
        assert DeveloperDep is not None

    # Helper methods (each ≤8 lines)
    def _setup_successful_auth_flow(self, mock_auth_client, mock_db_session, user):
        """Setup successful authentication flow."""
        self._setup_auth_client_valid_response(mock_auth_client)
        self._setup_db_session_with_user(mock_db_session, user)

    def _setup_auth_client_valid_response(self, mock_auth_client):
        """Setup auth client to return valid response."""
        mock_auth_client.return_value = {
            "valid": True,
            "user_id": "test-user-123",
            "email": "test@example.com"  # Include email for dev user creation
        }

    def _setup_db_session_with_user(self, mock_db_session, user):
        """Setup database session to return user."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db_session.execute.return_value = mock_result

    def _setup_db_session_no_user(self, mock_db_session):
        """Setup database session to return no user."""
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
        
    def _create_admin_user_with_role(self, role: str) -> User:
        """Create admin user with specific role."""
        user = User()
        user.id = f"admin-{role}-123"
        user.role = role
        user.is_admin = False  # Test role-based auth over legacy flag
        return user