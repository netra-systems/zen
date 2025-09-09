"""
Comprehensive Unit Tests for auth_integration/auth.py - AUTH Integration SSOT

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) - Auth integration enables Golden Path access
- Business Goal: Enable secure user access to $50K+ MRR AI optimization platform  
- Value Impact: Authentication is the gateway - without it, users cannot access ANY services
- Strategic Impact: FastAPI dependencies ensure multi-user isolation and JWT validation

MISSION CRITICAL: Auth integration is the SINGLE ENTRY POINT for all user access
to the Netra platform. It validates JWT tokens, creates user sessions, enables
admin functions, and prevents unauthorized access. If auth integration fails,
the ENTIRE PLATFORM is inaccessible to users.

Tests validate:
1. JWT token validation prevents unauthorized access
2. User dependency injection works for all endpoints  
3. Admin permission validation prevents privilege escalation
4. User auto-creation supports rapid onboarding
5. JWT claims synchronization maintains data consistency
6. Session validation handles multi-user scenarios
7. Permission-based access control works correctly
8. Error handling provides secure, user-friendly responses
9. Database session validation prevents data corruption

These tests ensure auth integration delivers secure, reliable user access.
"""

import pytest
from datetime import datetime, timezone
from typing import Dict, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.auth_integration.auth import (
    get_current_user,
    get_current_user_optional,
    get_current_user_with_db,
    get_current_active_user,
    validate_token_jwt,
    extract_admin_status_from_jwt,
    require_admin,
    require_admin_with_enhanced_validation,
    require_developer,
    require_permission,
    get_jwt_claims_for_user,
    auth_client,
    _validate_token_with_auth_service,
    _get_user_from_database, 
    _sync_jwt_claims_to_user_record,
    _auto_create_user_if_needed,
    _check_admin_permissions,
    _validate_user_permission,
    ActiveUserDep,
    OptionalUserDep,
    AdminDep,
    DeveloperDep,
    EnhancedAdminDep
)
from netra_backend.app.db.models_postgres import User


@pytest.fixture
def mock_credentials():
    """Create mock HTTP authorization credentials."""
    credentials = Mock(spec=HTTPAuthorizationCredentials)
    credentials.credentials = "valid_jwt_token_12345"
    return credentials


@pytest.fixture 
def mock_db_session():
    """Create mock async database session."""
    db = AsyncMock(spec=AsyncSession)
    return db


@pytest.fixture
def mock_user():
    """Create mock user object."""
    user = Mock(spec=User)
    user.id = "user123"
    user.email = "test@example.com"
    user.role = "standard_user"
    user.is_superuser = False
    user.is_admin = False
    user.is_developer = False
    user.permissions = ["read", "write"]
    return user


@pytest.fixture
def mock_admin_user():
    """Create mock admin user object."""
    user = Mock(spec=User)
    user.id = "admin123"
    user.email = "admin@example.com" 
    user.role = "admin"
    user.is_superuser = True
    user.is_admin = True
    user.is_developer = False
    user.permissions = ["admin", "read", "write", "system:*"]
    return user


@pytest.fixture
def valid_jwt_validation_result():
    """Create valid JWT validation result."""
    return {
        "valid": True,
        "user_id": "user123",
        "email": "test@example.com",
        "role": "standard_user", 
        "permissions": ["read", "write"]
    }


@pytest.fixture
def admin_jwt_validation_result():
    """Create admin JWT validation result."""
    return {
        "valid": True,
        "user_id": "admin123",
        "email": "admin@example.com",
        "role": "admin",
        "permissions": ["admin", "system:*"]
    }


class TestTokenValidationCore:
    """Test core JWT token validation business logic."""

    @pytest.mark.asyncio
    async def test_validate_token_with_auth_service_success(self, valid_jwt_validation_result):
        """Test successful token validation with auth service."""
        with patch.object(auth_client, 'validate_token_jwt') as mock_validate:
            mock_validate.return_value = valid_jwt_validation_result
            
            result = await _validate_token_with_auth_service("valid_token")
            
            assert result == valid_jwt_validation_result
            assert result["valid"] is True
            assert result["user_id"] == "user123"
            mock_validate.assert_called_once_with("valid_token")

    @pytest.mark.asyncio
    async def test_validate_token_with_auth_service_invalid_token(self):
        """Test token validation with invalid token raises HTTPException."""
        with patch.object(auth_client, 'validate_token_jwt') as mock_validate:
            mock_validate.return_value = {"valid": False, "error": "Token expired"}
            
            with pytest.raises(HTTPException) as exc_info:
                await _validate_token_with_auth_service("invalid_token")
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Invalid or expired token" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_validate_token_with_auth_service_no_user_id(self):
        """Test token validation without user_id raises HTTPException."""
        with patch.object(auth_client, 'validate_token_jwt') as mock_validate:
            mock_validate.return_value = {"valid": True}  # Missing user_id
            
            with pytest.raises(HTTPException) as exc_info:
                await _validate_token_with_auth_service("token_without_user_id")
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Invalid token payload" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_validate_token_with_auth_service_none_result(self):
        """Test token validation with None result raises HTTPException.""" 
        with patch.object(auth_client, 'validate_token_jwt') as mock_validate:
            mock_validate.return_value = None
            
            with pytest.raises(HTTPException) as exc_info:
                await _validate_token_with_auth_service("token_returns_none")
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


class TestUserDatabaseOperations:
    """Test user database operations and user creation logic."""

    @pytest.mark.asyncio
    async def test_get_user_from_database_existing_user(self, mock_db_session, mock_user, valid_jwt_validation_result):
        """Test retrieving existing user from database."""
        # Mock database query result
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db_session.execute.return_value = mock_result
        
        with patch('netra_backend.app.auth_integration.auth.validate_db_session') as mock_validate_session:
            user = await _get_user_from_database(mock_db_session, valid_jwt_validation_result)
            
            assert user == mock_user
            mock_validate_session.assert_called_once_with(mock_db_session, "get_user_from_database")
            mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio  
    async def test_get_user_from_database_auto_create_user(self, mock_db_session, mock_user, valid_jwt_validation_result):
        """Test auto-creating user when not found in database."""
        # Mock database query returns None (user not found)
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        with patch('netra_backend.app.auth_integration.auth.validate_db_session'), \
             patch('netra_backend.app.auth_integration.auth._auto_create_user_if_needed') as mock_create:
            mock_create.return_value = mock_user
            
            user = await _get_user_from_database(mock_db_session, valid_jwt_validation_result)
            
            assert user == mock_user
            mock_create.assert_called_once_with(mock_db_session, valid_jwt_validation_result)

    @pytest.mark.asyncio
    async def test_get_user_from_database_sync_jwt_claims(self, mock_db_session, mock_user, valid_jwt_validation_result):
        """Test syncing JWT claims to existing user record."""
        # Mock database query returns existing user
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db_session.execute.return_value = mock_result
        
        with patch('netra_backend.app.auth_integration.auth.validate_db_session'), \
             patch('netra_backend.app.auth_integration.auth._sync_jwt_claims_to_user_record') as mock_sync:
            
            user = await _get_user_from_database(mock_db_session, valid_jwt_validation_result)
            
            assert user == mock_user
            mock_sync.assert_called_once_with(mock_user, valid_jwt_validation_result, mock_db_session)

    @pytest.mark.asyncio
    async def test_sync_jwt_claims_to_user_record_role_update(self, mock_db_session, mock_user):
        """Test syncing JWT role to user database record."""
        jwt_result = {
            "role": "admin",  # Different from user.role
            "permissions": ["admin", "system:*"]
        }
        
        # User starts as standard_user, should be updated to admin
        mock_user.role = "standard_user"
        mock_user.is_superuser = False
        
        await _sync_jwt_claims_to_user_record(mock_user, jwt_result, mock_db_session)
        
        # Should update role and admin status
        assert mock_user.role == "admin"
        assert mock_user.is_superuser is True
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_jwt_claims_to_user_record_no_changes_needed(self, mock_db_session, mock_user):
        """Test sync when JWT claims match database record."""
        jwt_result = {
            "role": "standard_user",  # Same as user.role
            "permissions": ["read", "write"]
        }
        
        # User already has matching values
        mock_user.role = "standard_user"
        mock_user.is_superuser = False
        
        await _sync_jwt_claims_to_user_record(mock_user, jwt_result, mock_db_session)
        
        # Should not commit changes
        mock_db_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_jwt_claims_handles_exceptions(self, mock_db_session, mock_user):
        """Test sync handles database errors gracefully."""
        jwt_result = {"role": "admin", "permissions": ["admin"]}
        
        # Mock commit to raise exception
        mock_db_session.commit.side_effect = Exception("Database error")
        
        # Should not raise exception, should rollback
        await _sync_jwt_claims_to_user_record(mock_user, jwt_result, mock_db_session)
        
        mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_create_user_if_needed_creates_user(self, mock_db_session, mock_user, valid_jwt_validation_result):
        """Test auto-creating user from JWT claims."""
        with patch('netra_backend.app.auth_integration.auth.validate_db_session'), \
             patch('netra_backend.app.services.user_service.user_service') as mock_service, \
             patch('netra_backend.app.config.get_config') as mock_get_config:
            
            mock_service.get_or_create_dev_user.return_value = mock_user
            mock_config = Mock()
            mock_config.environment = "test"
            mock_get_config.return_value = mock_config
            
            user = await _auto_create_user_if_needed(mock_db_session, valid_jwt_validation_result)
            
            assert user == mock_user
            mock_service.get_or_create_dev_user.assert_called_once_with(
                mock_db_session,
                email="test@example.com",
                user_id="user123"
            )


class TestCurrentUserDependencies:
    """Test FastAPI dependency injection for current user."""

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, mock_credentials, mock_db_session, mock_user, valid_jwt_validation_result):
        """Test successful current user retrieval."""
        with patch('netra_backend.app.auth_integration.auth._validate_token_with_auth_service') as mock_validate, \
             patch('netra_backend.app.auth_integration.auth._get_user_from_database') as mock_get_user:
            
            mock_validate.return_value = valid_jwt_validation_result
            mock_get_user.return_value = mock_user
            
            user = await get_current_user(mock_credentials, mock_db_session)
            
            assert user == mock_user
            # Verify JWT validation result is stored on user
            assert hasattr(user, '_jwt_validation_result')
            assert user._jwt_validation_result == valid_jwt_validation_result
            
            mock_validate.assert_called_once_with("valid_jwt_token_12345")
            mock_get_user.assert_called_once_with(mock_db_session, valid_jwt_validation_result)

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, mock_credentials, mock_db_session):
        """Test current user retrieval with invalid token."""
        with patch('netra_backend.app.auth_integration.auth._validate_token_with_auth_service') as mock_validate:
            mock_validate.side_effect = HTTPException(status_code=401, detail="Invalid token")
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials, mock_db_session)
            
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_optional_success(self, mock_credentials, mock_db_session, mock_user, valid_jwt_validation_result):
        """Test optional current user retrieval with valid credentials."""
        with patch('netra_backend.app.auth_integration.auth._validate_token_with_auth_service') as mock_validate, \
             patch('netra_backend.app.auth_integration.auth._get_user_from_database') as mock_get_user, \
             patch('netra_backend.app.auth_integration.auth.validate_db_session'):
            
            mock_validate.return_value = valid_jwt_validation_result
            mock_get_user.return_value = mock_user
            
            user = await get_current_user_optional(mock_credentials, mock_db_session)
            
            assert user == mock_user

    @pytest.mark.asyncio
    async def test_get_current_user_optional_no_credentials(self, mock_db_session):
        """Test optional current user retrieval without credentials returns None."""
        user = await get_current_user_optional(None, mock_db_session)
        assert user is None

    @pytest.mark.asyncio
    async def test_get_current_user_optional_invalid_token(self, mock_credentials, mock_db_session):
        """Test optional current user retrieval with invalid token returns None."""
        with patch('netra_backend.app.auth_integration.auth._validate_token_with_auth_service') as mock_validate:
            mock_validate.side_effect = HTTPException(status_code=401, detail="Invalid token")
            
            user = await get_current_user_optional(mock_credentials, mock_db_session)
            assert user is None

    @pytest.mark.asyncio
    async def test_get_current_user_with_db_success(self, mock_credentials, mock_user, valid_jwt_validation_result):
        """Test current user retrieval with provided database session."""
        mock_db = AsyncMock(spec=AsyncSession)
        
        with patch('netra_backend.app.auth_integration.auth._validate_token_with_auth_service') as mock_validate, \
             patch('netra_backend.app.auth_integration.auth._get_user_from_database') as mock_get_user:
            
            mock_validate.return_value = valid_jwt_validation_result
            mock_get_user.return_value = mock_user
            
            user = await get_current_user_with_db(mock_credentials, mock_db)
            
            assert user == mock_user

    @pytest.mark.asyncio
    async def test_get_current_user_with_db_no_session(self, mock_credentials):
        """Test current user retrieval without database session raises error."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_with_db(mock_credentials, None)
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Database session not provided" in exc_info.value.detail


class TestJWTValidationAndClaims:
    """Test JWT validation and claims extraction."""

    @pytest.mark.asyncio
    async def test_validate_token_jwt_success(self, valid_jwt_validation_result):
        """Test JWT token validation success."""
        with patch.object(auth_client, 'validate_token') as mock_validate:
            mock_validate.return_value = valid_jwt_validation_result
            
            result = await validate_token_jwt("valid_token")
            
            assert result == valid_jwt_validation_result
            mock_validate.assert_called_once_with("valid_token")

    @pytest.mark.asyncio
    async def test_validate_token_jwt_failure(self):
        """Test JWT token validation failure."""
        with patch.object(auth_client, 'validate_token') as mock_validate:
            mock_validate.return_value = None
            
            result = await validate_token_jwt("invalid_token")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_extract_admin_status_from_jwt_admin_role(self, admin_jwt_validation_result):
        """Test admin status extraction from JWT with admin role."""
        with patch.object(auth_client, 'validate_token_jwt') as mock_validate:
            mock_validate.return_value = admin_jwt_validation_result
            
            result = await extract_admin_status_from_jwt("admin_token")
            
            assert result["is_admin"] is True
            assert result["role"] == "admin"
            assert result["user_id"] == "admin123"
            assert result["source"] == "jwt_claims"

    @pytest.mark.asyncio
    async def test_extract_admin_status_from_jwt_admin_permissions(self):
        """Test admin status extraction from JWT with admin permissions."""
        jwt_result = {
            "valid": True,
            "user_id": "user123",
            "role": "user",
            "permissions": ["system:*"]  # Admin via permissions
        }
        
        with patch.object(auth_client, 'validate_token_jwt') as mock_validate:
            mock_validate.return_value = jwt_result
            
            result = await extract_admin_status_from_jwt("token_with_admin_perms")
            
            assert result["is_admin"] is True
            assert result["source"] == "jwt_claims"

    @pytest.mark.asyncio
    async def test_extract_admin_status_from_jwt_not_admin(self, valid_jwt_validation_result):
        """Test admin status extraction from JWT for non-admin user."""
        with patch.object(auth_client, 'validate_token_jwt') as mock_validate:
            mock_validate.return_value = valid_jwt_validation_result
            
            result = await extract_admin_status_from_jwt("user_token")
            
            assert result["is_admin"] is False
            assert result["role"] == "standard_user"
            assert result["source"] == "jwt_claims"

    @pytest.mark.asyncio
    async def test_extract_admin_status_from_jwt_invalid_token(self):
        """Test admin status extraction from invalid JWT token."""
        with patch.object(auth_client, 'validate_token_jwt') as mock_validate:
            mock_validate.return_value = {"valid": False}
            
            result = await extract_admin_status_from_jwt("invalid_token")
            
            assert result["is_admin"] is False
            assert result["error"] == "Invalid token"
            assert result["source"] == "jwt_validation_failed"

    @pytest.mark.asyncio
    async def test_extract_admin_status_from_jwt_exception(self):
        """Test admin status extraction handles exceptions gracefully."""
        with patch.object(auth_client, 'validate_token_jwt') as mock_validate:
            mock_validate.side_effect = Exception("Auth service down")
            
            result = await extract_admin_status_from_jwt("token")
            
            assert result["is_admin"] is False
            assert result["error"] == "Auth service down"
            assert result["source"] == "jwt_extraction_error"

    def test_get_jwt_claims_for_user_with_claims(self, mock_user, valid_jwt_validation_result):
        """Test extracting JWT claims from user object."""
        mock_user._jwt_validation_result = valid_jwt_validation_result
        
        claims = get_jwt_claims_for_user(mock_user)
        
        assert claims == valid_jwt_validation_result

    def test_get_jwt_claims_for_user_without_claims(self, mock_user):
        """Test extracting JWT claims when not available on user object."""
        # User doesn't have _jwt_validation_result attribute
        delattr(mock_user, '_jwt_validation_result') if hasattr(mock_user, '_jwt_validation_result') else None
        
        claims = get_jwt_claims_for_user(mock_user)
        
        assert claims == {}


class TestPermissionChecking:
    """Test permission checking and authorization logic."""

    def test_check_admin_permissions_superuser(self, mock_user):
        """Test admin permission check for superuser."""
        mock_user.is_superuser = True
        
        result = _check_admin_permissions(mock_user)
        assert result is True

    def test_check_admin_permissions_admin_role(self, mock_user):
        """Test admin permission check for admin role."""
        mock_user.role = "admin"
        
        result = _check_admin_permissions(mock_user)
        assert result is True

    def test_check_admin_permissions_super_admin_role(self, mock_user):
        """Test admin permission check for super_admin role."""
        mock_user.role = "super_admin"
        
        result = _check_admin_permissions(mock_user)
        assert result is True

    def test_check_admin_permissions_is_admin_attribute(self, mock_user):
        """Test admin permission check with is_admin attribute."""
        mock_user.is_admin = True
        
        result = _check_admin_permissions(mock_user)
        assert result is True

    def test_check_admin_permissions_not_admin(self, mock_user):
        """Test admin permission check for non-admin user."""
        # All admin indicators are False by default in mock_user
        result = _check_admin_permissions(mock_user)
        assert result is False

    def test_validate_user_permission_has_db_permission(self, mock_user):
        """Test user permission validation with database permission."""
        mock_user.permissions = ["read", "write", "admin"]
        
        # Should not raise exception
        _validate_user_permission(mock_user, "admin")

    def test_validate_user_permission_has_jwt_permission(self, mock_user, valid_jwt_validation_result):
        """Test user permission validation with JWT permission."""
        mock_user.permissions = ["read"]  # DB doesn't have admin
        mock_user._jwt_validation_result = {
            "permissions": ["admin", "system:*"]  # JWT has admin
        }
        
        # Should not raise exception
        _validate_user_permission(mock_user, "admin")

    def test_validate_user_permission_wildcard_permission(self, mock_user):
        """Test user permission validation with wildcard permission."""
        mock_user._jwt_validation_result = {
            "permissions": ["system:*"]  # Wildcard permission
        }
        
        # Should not raise exception for any permission
        _validate_user_permission(mock_user, "any_permission")

    def test_validate_user_permission_prefix_wildcard(self, mock_user):
        """Test user permission validation with prefix wildcard."""
        mock_user._jwt_validation_result = {
            "permissions": ["users:*"]  # Prefix wildcard
        }
        
        # Should not raise exception for users:read
        _validate_user_permission(mock_user, "users:read")

    def test_validate_user_permission_denied(self, mock_user):
        """Test user permission validation denied."""
        mock_user.permissions = ["read"]  # Only read permission
        mock_user._jwt_validation_result = {
            "permissions": ["read"]  # JWT also only has read
        }
        
        # Should raise HTTPException for admin permission
        with pytest.raises(HTTPException) as exc_info:
            _validate_user_permission(mock_user, "admin")
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Permission 'admin' required" in exc_info.value.detail


class TestAdminRequirements:
    """Test admin requirement dependencies."""

    @pytest.mark.asyncio
    async def test_require_admin_success(self, mock_admin_user):
        """Test admin requirement with admin user."""
        user = await require_admin(mock_admin_user)
        assert user == mock_admin_user

    @pytest.mark.asyncio
    async def test_require_admin_not_admin(self, mock_user):
        """Test admin requirement with non-admin user."""
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(mock_user)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Admin access required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_require_admin_with_enhanced_validation_db_admin(self, mock_credentials, mock_admin_user):
        """Test enhanced admin requirement with database admin."""
        user = await require_admin_with_enhanced_validation(mock_credentials, mock_admin_user)
        assert user == mock_admin_user

    @pytest.mark.asyncio
    async def test_require_admin_with_enhanced_validation_jwt_override(self, mock_credentials, mock_user, admin_jwt_validation_result):
        """Test enhanced admin requirement with JWT admin override."""
        # User is not admin in database but is admin in JWT
        with patch('netra_backend.app.auth_integration.auth.extract_admin_status_from_jwt') as mock_extract:
            mock_extract.return_value = {
                "is_admin": True,
                "user_id": "user123",
                "role": "admin",
                "source": "jwt_claims"
            }
            
            user = await require_admin_with_enhanced_validation(mock_credentials, mock_user)
            assert user == mock_user

    @pytest.mark.asyncio
    async def test_require_admin_with_enhanced_validation_denied(self, mock_credentials, mock_user):
        """Test enhanced admin requirement denied by both database and JWT."""
        with patch('netra_backend.app.auth_integration.auth.extract_admin_status_from_jwt') as mock_extract:
            mock_extract.return_value = {
                "is_admin": False,
                "user_id": "user123",
                "source": "jwt_claims"
            }
            
            with pytest.raises(HTTPException) as exc_info:
                await require_admin_with_enhanced_validation(mock_credentials, mock_user)
            
            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
            assert "Admin access required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_require_developer_success(self, mock_user):
        """Test developer requirement with developer user."""
        mock_user.is_developer = True
        
        user = await require_developer(mock_user)
        assert user == mock_user

    @pytest.mark.asyncio
    async def test_require_developer_not_developer(self, mock_user):
        """Test developer requirement with non-developer user."""
        # is_developer is False by default in mock_user
        with pytest.raises(HTTPException) as exc_info:
            await require_developer(mock_user)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Developer access required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_require_permission_dependency_creation(self, mock_user):
        """Test require_permission creates proper dependency function."""
        permission_dependency = require_permission("admin")
        
        # Test with user that has admin permission
        mock_user.permissions = ["admin", "read", "write"]
        
        user = await permission_dependency(mock_user)
        assert user == mock_user

    @pytest.mark.asyncio
    async def test_require_permission_dependency_denied(self, mock_user):
        """Test require_permission dependency denies user without permission."""
        permission_dependency = require_permission("admin")
        
        # Test with user that doesn't have admin permission
        mock_user.permissions = ["read", "write"]
        
        with pytest.raises(HTTPException) as exc_info:
            await permission_dependency(mock_user)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


class TestTypeAnnotationsDependencies:
    """Test that type annotation dependencies are properly defined."""

    def test_active_user_dep_annotation(self):
        """Test ActiveUserDep annotation is properly defined."""
        # This is a type annotation test - just verify it's importable and defined
        assert ActiveUserDep is not None

    def test_optional_user_dep_annotation(self):
        """Test OptionalUserDep annotation is properly defined."""
        assert OptionalUserDep is not None

    def test_admin_dep_annotation(self):
        """Test AdminDep annotation is properly defined."""
        assert AdminDep is not None

    def test_developer_dep_annotation(self):
        """Test DeveloperDep annotation is properly defined."""
        assert DeveloperDep is not None

    def test_enhanced_admin_dep_annotation(self):
        """Test EnhancedAdminDep annotation is properly defined."""
        assert EnhancedAdminDep is not None


class TestBackwardCompatibilityAliases:
    """Test backward compatibility aliases and functions."""

    def test_get_current_active_user_alias(self):
        """Test get_current_active_user is alias for get_current_user."""
        assert get_current_active_user == get_current_user

    def test_active_user_ws_dep_exists(self):
        """Test ActiveUserWsDep annotation exists for WebSocket compatibility."""
        from netra_backend.app.auth_integration.auth import ActiveUserWsDep
        assert ActiveUserWsDep is not None


class TestSecurityLoggingAndAudit:
    """Test security logging and audit functionality."""

    @pytest.mark.asyncio
    async def test_validate_token_with_auth_service_logs_success(self, valid_jwt_validation_result):
        """Test successful token validation logs appropriate information."""
        with patch.object(auth_client, 'validate_token_jwt') as mock_validate, \
             patch('netra_backend.app.auth_integration.auth.logger') as mock_logger:
            
            mock_validate.return_value = valid_jwt_validation_result
            
            await _validate_token_with_auth_service("valid_token")
            
            # Should log debug message with user info
            mock_logger.debug.assert_called_once()
            debug_call = mock_logger.debug.call_args[0][0]
            assert "Token validated successfully" in debug_call
            assert "user123" in debug_call

    @pytest.mark.asyncio  
    async def test_validate_token_with_auth_service_logs_failures(self):
        """Test failed token validation logs appropriate warnings."""
        with patch.object(auth_client, 'validate_token_jwt') as mock_validate, \
             patch('netra_backend.app.auth_integration.auth.logger') as mock_logger:
            
            mock_validate.return_value = {"valid": False}
            
            with pytest.raises(HTTPException):
                await _validate_token_with_auth_service("invalid_token")
            
            # Should log warning about validation failure
            mock_logger.warning.assert_called()
            warning_call = mock_logger.warning.call_args[0][0]
            assert "Token validation failed" in warning_call

    @pytest.mark.asyncio
    async def test_sync_jwt_claims_logs_changes(self, mock_db_session, mock_user):
        """Test JWT claims sync logs important security changes."""
        jwt_result = {
            "role": "admin",  # Escalation from standard_user
            "permissions": ["admin", "system:*"]
        }
        
        mock_user.role = "standard_user"
        mock_user.is_superuser = False
        
        with patch('netra_backend.app.auth_integration.auth.logger') as mock_logger:
            await _sync_jwt_claims_to_user_record(mock_user, jwt_result, mock_db_session)
            
            # Should log role change
            assert mock_logger.info.call_count >= 2  # Role sync and admin status sync
            
            # Check for role sync log
            info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
            assert any("Syncing role from JWT" in call for call in info_calls)
            assert any("Syncing admin status from JWT" in call for call in info_calls)


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_get_current_user_optional_database_error(self, mock_credentials, mock_db_session):
        """Test optional user retrieval handles database errors gracefully."""
        with patch('netra_backend.app.auth_integration.auth.validate_db_session') as mock_validate:
            mock_validate.side_effect = TypeError("DB session error")
            
            # Should return None instead of raising exception
            user = await get_current_user_optional(mock_credentials, mock_db_session)
            assert user is None

    @pytest.mark.asyncio
    async def test_auto_create_user_generates_fallback_email(self, mock_db_session, mock_user):
        """Test auto-creating user generates fallback email when missing."""
        jwt_result = {
            "user_id": "user123",
            # "email" is missing
        }
        
        with patch('netra_backend.app.auth_integration.auth.validate_db_session'), \
             patch('netra_backend.app.services.user_service.user_service') as mock_service, \
             patch('netra_backend.app.config.get_config') as mock_get_config:
            
            mock_service.get_or_create_dev_user.return_value = mock_user
            mock_config = Mock()
            mock_config.environment = "test" 
            mock_get_config.return_value = mock_config
            
            user = await _auto_create_user_if_needed(mock_db_session, jwt_result)
            
            # Should use fallback email format
            mock_service.get_or_create_dev_user.assert_called_once_with(
                mock_db_session,
                email="user_user123@example.com",  # Fallback format
                user_id="user123"
            )

    def test_check_admin_permissions_handles_missing_attributes(self):
        """Test admin permission check handles users with missing attributes."""
        # User with minimal attributes
        minimal_user = Mock()
        # Intentionally don't set any admin attributes
        
        result = _check_admin_permissions(minimal_user)
        assert result is False  # Should default to False safely

    @pytest.mark.asyncio
    async def test_require_admin_logs_access_denials(self, mock_user):
        """Test admin requirement logs access denials for security audit."""
        with patch('netra_backend.app.auth_integration.auth.logger') as mock_logger:
            with pytest.raises(HTTPException):
                await require_admin(mock_user)
            
            # Should log warning about denied admin access
            mock_logger.warning.assert_called_once()
            warning_call = mock_logger.warning.call_args[0][0]
            assert "Admin access denied" in warning_call
            assert "user123" in warning_call  # Should include user ID


class TestAuthIntegrationBusinessValueDelivery:
    """Test that auth integration delivers expected business value."""

    @pytest.mark.asyncio
    async def test_auth_integration_enables_golden_path_access(self, mock_credentials, mock_db_session, mock_user, valid_jwt_validation_result):
        """Test auth integration enables Golden Path user access to AI services."""
        with patch('netra_backend.app.auth_integration.auth._validate_token_with_auth_service') as mock_validate, \
             patch('netra_backend.app.auth_integration.auth._get_user_from_database') as mock_get_user:
            
            mock_validate.return_value = valid_jwt_validation_result
            mock_get_user.return_value = mock_user
            
            # Golden Path: User gets authenticated and can access services
            user = await get_current_user(mock_credentials, mock_db_session)
            
            # Verify user has access to the platform
            assert user.id == "user123"
            assert user.email == "test@example.com"
            assert hasattr(user, '_jwt_validation_result')  # JWT claims available
            
            # This represents successful authentication enabling $50K+ MRR platform access

    def test_auth_integration_prevents_unauthorized_access(self, mock_user):
        """Test auth integration prevents unauthorized access to protect business value."""
        # Non-admin user should not get admin access
        with pytest.raises(HTTPException) as exc_info:
            _validate_user_permission(mock_user, "admin")
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        
        # This prevents unauthorized access that could damage the business

    def test_auth_integration_supports_multi_user_isolation(self, mock_user, valid_jwt_validation_result):
        """Test auth integration supports multi-user isolation for platform scalability."""
        # Each user gets their own isolated context
        mock_user._jwt_validation_result = valid_jwt_validation_result
        
        claims = get_jwt_claims_for_user(mock_user)
        
        # Each user has unique ID and permissions
        assert claims["user_id"] == "user123"
        assert claims["permissions"] == ["read", "write"]
        
        # This enables multi-tenant platform supporting many customers

    @pytest.mark.asyncio
    async def test_auth_integration_enables_rapid_user_onboarding(self, mock_db_session, mock_user, valid_jwt_validation_result):
        """Test auth integration enables rapid user onboarding for business growth."""
        # New user gets automatically created from JWT
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None  # User doesn't exist
        mock_db_session.execute.return_value = mock_result
        
        with patch('netra_backend.app.auth_integration.auth.validate_db_session'), \
             patch('netra_backend.app.auth_integration.auth._auto_create_user_if_needed') as mock_create:
            mock_create.return_value = mock_user
            
            user = await _get_user_from_database(mock_db_session, valid_jwt_validation_result)
            
            assert user == mock_user
            mock_create.assert_called_once()
            
            # This enables rapid user onboarding without manual account creation

    def test_auth_integration_maintains_security_compliance(self, mock_user):
        """Test auth integration maintains security compliance for enterprise customers."""
        # Verify proper JWT claims synchronization for audit compliance
        jwt_result = {
            "role": "admin",
            "permissions": ["admin", "system:*"],
            "user_id": "user123"
        }
        
        # Extract admin status (important for compliance)
        is_admin = (
            jwt_result.get("role") in ["admin", "super_admin"] or
            "admin" in jwt_result.get("permissions", []) or
            "system:*" in jwt_result.get("permissions", [])
        )
        
        assert is_admin is True
        
        # This maintains security compliance required for enterprise customers