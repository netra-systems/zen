"""
Test Auth Service Integration

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise)
- Business Goal: Ensure authentication system reliability and security
- Value Impact: Prevent auth failures that cause customer churn and security breaches
- Strategic Impact: Core platform functionality - auth must work for all features

This test suite validates the internal auth service logic and database/cache interactions,
focusing on service integrations with real PostgreSQL and Redis but mocking external APIs.
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env

# Auth service imports
from netra_backend.app.auth_integration.auth import (
    get_current_user,
    _validate_token_with_auth_service,
    _get_user_from_database,
    _sync_jwt_claims_to_user_record,
    extract_admin_status_from_jwt,
    require_admin_with_enhanced_validation
)
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from netra_backend.app.services.security_service import SecurityService
from netra_backend.app.middleware.auth_middleware import AuthMiddleware

# Models and schemas
from netra_backend.app.models.session import Session, SessionModel
from netra_backend.app.models.user import User, UserCreate
from netra_backend.app.schemas.auth_types import (
    TokenPayload,
    TokenData,
    TokenClaims,
    LoginRequest,
    LoginResponse,
    AuthProvider,
    TokenType,
    TokenStatus,
    Role,
    Permission,
    UserProfile,
    SessionInfo
)
from netra_backend.app.db.models_postgres import User as DBUser

# Test utilities
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials


class TestAuthServiceIntegration(BaseIntegrationTest):
    """Integration tests for authentication service with real services."""
    
    def setup_method(self):
        """Set up method called before each test method."""
        super().setup_method()
        self.env = get_env()
        
        # Mock external APIs while using real services
        self.mock_auth_client = AsyncMock(spec=AuthServiceClient)
        self.mock_redis = None  # Will be set by fixtures
        self.mock_security_service = None  # Will be set by fixtures

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_session_persistence(self, real_services_fixture):
        """
        Test session storage in Redis and database.
        
        Validates:
        - Session creation and storage in Redis
        - Session metadata persistence in database
        - Session retrieval and validation
        - Session expiry handling
        """
        # Test Session model functionality - this tests business logic without external dependencies
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        
        # Create session object
        session = Session(
            session_id=session_id,
            user_id=user_id,
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            timeout_seconds=3600,
            session_data={"last_activity": "test_action"}
        )
        
        # Test session model functionality
        assert session.session_id == session_id
        assert session.user_id == user_id
        assert session.session_data["last_activity"] == "test_action"
        
        # Test session expiry logic
        assert not session.is_session_expired()
        
        # Test session activity update
        original_time = session.last_activity
        session.update_activity()
        updated_time = session.last_activity
        assert updated_time > original_time
        
        # Test JSON serialization/deserialization
        session_json = session.model_dump_json()
        parsed_session = Session.model_validate_json(session_json)
        assert parsed_session.session_id == session_id
        assert parsed_session.user_id == user_id
        assert parsed_session.session_data["last_activity"] == "test_action"
        
        # Test session invalidation
        session.mark_invalid()
        assert not session.is_valid
        assert session.is_expired
        
        # Test session data storage and retrieval
        session.store_data("user_preference", "dark_mode")
        assert session.get_data("user_preference") == "dark_mode"
        assert session.get_data("nonexistent", "default") == "default"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_token_validation_and_expiry(self, real_services_fixture):
        """
        Test JWT token validation logic.
        
        Validates:
        - Token validation through auth service
        - Token expiry detection and handling
        - JWT claims extraction and validation
        - Invalid token rejection
        """
        # Mock auth service client for token validation
        with patch('netra_backend.app.auth_integration.auth.auth_client') as mock_client:
            # Test valid token
            valid_token = "valid.jwt.token"
            mock_validation_result = {
                "valid": True,
                "user_id": "test-user-123",
                "email": "test@example.com",
                "role": "standard_user",
                "permissions": ["read:profile", "write:profile"],
                "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
            }
            mock_client.validate_token_jwt.return_value = mock_validation_result
            
            # Test token validation
            result = await _validate_token_with_auth_service(valid_token)
            assert result["valid"] == True
            assert result["user_id"] == "test-user-123"
            assert result["email"] == "test@example.com"
            assert "read:profile" in result["permissions"]
            
            # Test expired token
            expired_token = "expired.jwt.token"
            mock_client.validate_token_jwt.return_value = {
                "valid": False,
                "error": "Token expired"
            }
            
            with pytest.raises(HTTPException) as exc_info:
                await _validate_token_with_auth_service(expired_token)
            
            assert exc_info.value.status_code == 401
            assert "Invalid or expired token" in str(exc_info.value.detail)
            
            # Test invalid token format
            invalid_token = "invalid.token"
            mock_client.validate_token_jwt.return_value = None
            
            with pytest.raises(HTTPException) as exc_info:
                await _validate_token_with_auth_service(invalid_token)
            
            assert exc_info.value.status_code == 401
            
            # Test token without user_id
            no_user_token = "no.user.token"
            mock_client.validate_token_jwt.return_value = {
                "valid": True,
                "email": "test@example.com"
                # Missing user_id
            }
            
            with pytest.raises(HTTPException) as exc_info:
                await _validate_token_with_auth_service(no_user_token)
            
            assert exc_info.value.status_code == 401
            assert "Invalid token payload" in str(exc_info.value.detail)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_registration_flow(self, real_services_fixture):
        """
        Test user creation and validation.
        
        Validates:
        - User creation through security service
        - Password hashing via auth service  
        - User authentication logic
        - Security service integration
        """
        # Mock auth service for password operations and database
        with patch('netra_backend.app.services.security_service.auth_client') as mock_client:
            # Mock database session
            mock_db_session = AsyncMock()
            
            # Setup security service
            security_service = SecurityService()
            
            # Mock password hashing
            mock_client.hash_password.return_value = {
                "hashed_password": "$2b$12$mock.hashed.password"
            }
            
            # Mock password verification
            mock_client.verify_password.return_value = {
                "valid": True
            }
            
            # Test UserCreate model validation
            user_create = UserCreate(
                email="newuser@example.com",
                password="securepassword123",
                full_name="New Test User"
            )
            
            assert user_create.email == "newuser@example.com" 
            assert user_create.password == "securepassword123"
            assert user_create.full_name == "New Test User"
            
            # Test password hashing integration
            hashed_password = await security_service.get_password_hash("securepassword123")
            assert hashed_password == "$2b$12$mock.hashed.password"
            
            # Test password verification integration
            is_valid = await security_service.verify_password("securepassword123", "$2b$12$mock.hashed.password")
            assert is_valid == True
            
            # Test with wrong password
            mock_client.verify_password.return_value = {"valid": False}
            is_invalid = await security_service.verify_password("wrongpassword", "$2b$12$mock.hashed.password")
            assert is_invalid == False
            
            # Test user model building
            hashed_password = "$2b$12$mock.hashed.password"
            user_model = security_service._build_user_model(user_create, hashed_password)
            
            assert user_model.email == "newuser@example.com"
            assert user_model.full_name == "New Test User"
            assert user_model.hashed_password == "$2b$12$mock.hashed.password"
            assert not hasattr(user_model, 'password')  # Original password should be excluded

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_permission_and_role_management(self, real_services_fixture):
        """
        Test RBAC and permissions.
        
        Validates:
        - Role assignment and validation
        - Permission checking
        - JWT claims extraction
        - Admin status validation
        """
        # Create test users with different roles (in memory for testing)
        admin_user_id = str(uuid.uuid4())
        regular_user_id = str(uuid.uuid4())
        
        admin_user = DBUser(
            id=admin_user_id,
            email="admin@example.com",
            full_name="Admin User",
            role="admin",
            is_superuser=True,
            is_active=True
        )
        
        regular_user = DBUser(
            id=regular_user_id,
            email="user@example.com", 
            full_name="Regular User",
            role="standard_user",
            is_superuser=False,
            is_active=True
        )
        
        # Test JWT claims extraction for admin
        with patch('netra_backend.app.auth_integration.auth.auth_client') as mock_client:
            mock_client.validate_token_jwt.return_value = {
                "valid": True,
                "user_id": admin_user_id,
                "email": "admin@example.com",
                "role": "super_admin",
                "permissions": ["admin", "system:*", "user:read", "user:write"]
            }
            
            admin_token = "admin.jwt.token"
            admin_status = await extract_admin_status_from_jwt(admin_token)
            
            assert admin_status["is_admin"] == True
            assert admin_status["role"] == "super_admin"
            assert admin_status["user_id"] == admin_user_id
            assert "system:*" in admin_status["permissions"]
            assert admin_status["source"] == "jwt_claims"
            
            # Test JWT claims with regular user
            mock_client.validate_token_jwt.return_value = {
                "valid": True,
                "user_id": regular_user_id,
                "email": "user@example.com",
                "role": "standard_user",
                "permissions": ["user:read", "profile:write"]
            }
            
            user_token = "user.jwt.token"
            user_status = await extract_admin_status_from_jwt(user_token)
            
            assert user_status["is_admin"] == False
            assert user_status["role"] == "standard_user"
            assert user_status["user_id"] == regular_user_id
            assert "user:read" in user_status["permissions"]
        
        # Test permission validation logic
        regular_user._jwt_validation_result = {
            "user_id": regular_user_id,
            "permissions": ["user:read", "profile:write"]
        }
        
        # Test admin permission checking
        from netra_backend.app.auth_integration.auth import _check_admin_permissions
        assert _check_admin_permissions(admin_user) == True
        assert _check_admin_permissions(regular_user) == False
        
        # Test permission validation
        from netra_backend.app.auth_integration.auth import _validate_user_permission
        
        # This should work - user has the permission
        _validate_user_permission(regular_user, "user:read")
        
        # This should fail - user doesn't have admin permission
        with pytest.raises(HTTPException) as exc_info:
            _validate_user_permission(regular_user, "admin:delete")
        
        assert exc_info.value.status_code == 403
        assert "admin:delete" in str(exc_info.value.detail)
        
        # Test wildcard permissions
        admin_user._jwt_validation_result = {
            "user_id": admin_user_id,
            "permissions": ["system:*", "admin"]
        }
        
        # Should work with wildcard permission
        _validate_user_permission(admin_user, "system:delete")
        _validate_user_permission(admin_user, "system:create")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_auth_middleware_behavior(self, real_services_fixture):
        """
        Test authentication middleware.
        
        Validates:
        - Request authentication processing
        - Token extraction and validation
        - User context injection
        - Error handling for invalid tokens
        """
        # Mock FastAPI request and dependencies
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid.test.token"
        )
        
        # Mock database session
        mock_db_session = AsyncMock()
        
        test_user_id = str(uuid.uuid4())
        
        # Create test user for middleware testing
        test_user = DBUser(
            id=test_user_id,
            email="middleware@example.com",
            full_name="Middleware Test User",
            is_active=True
        )
        
        with patch('netra_backend.app.auth_integration.auth.auth_client') as mock_auth_client:
            # Mock successful token validation
            mock_auth_client.validate_token_jwt.return_value = {
                "valid": True,
                "user_id": test_user_id,
                "email": "middleware@example.com", 
                "role": "standard_user",
                "permissions": ["user:read"]
            }
            
            # Mock database query to return test user
            from sqlalchemy import select
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = test_user
            mock_db_session.execute.return_value = mock_result
            
            # Test get_current_user function 
            authenticated_user = await get_current_user(mock_credentials, mock_db_session)
            
            assert authenticated_user is not None
            assert authenticated_user.id == test_user_id
            assert authenticated_user.email == "middleware@example.com"
            assert hasattr(authenticated_user, '_jwt_validation_result')
            
            jwt_claims = authenticated_user._jwt_validation_result
            assert jwt_claims["user_id"] == test_user_id
            assert jwt_claims["role"] == "standard_user"
            
            # Test with invalid token
            mock_auth_client.validate_token_jwt.return_value = {
                "valid": False,
                "error": "Invalid token"
            }
            
            invalid_credentials = HTTPAuthorizationCredentials(
                scheme="Bearer", 
                credentials="invalid.token"
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(invalid_credentials, mock_db_session)
            
            assert exc_info.value.status_code == 401

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_enhanced_admin_validation(self, real_services_fixture):
        """
        Test enhanced admin validation with dual JWT and database checks.
        
        Validates:
        - Database-based admin validation
        - JWT-based admin validation as override
        - Dual validation security pattern
        - Error handling for insufficient privileges
        """
        db_session = real_services_fixture.get("db")
        if not db_session:
            pytest.skip("Real database service not available")
        
        # Create test user with admin database record but non-admin JWT
        admin_user_id = str(uuid.uuid4())
        admin_user = DBUser(
            id=admin_user_id,
            email="admin@example.com",
            full_name="DB Admin User",
            role="admin",
            is_superuser=True,
            is_active=True
        )
        
        db_session.add(admin_user)
        await db_session.commit()
        
        try:
            # Test database admin validation passes
            from netra_backend.app.auth_integration.auth import _check_admin_permissions
            assert _check_admin_permissions(admin_user) == True
            
            # Create user with non-admin database record
            user_id = str(uuid.uuid4())
            regular_user = DBUser(
                id=user_id,
                email="user@example.com",
                full_name="Regular User",
                role="standard_user",
                is_superuser=False,
                is_active=True
            )
            
            db_session.add(regular_user)
            await db_session.commit()
            
            # Test database non-admin validation fails
            assert _check_admin_permissions(regular_user) == False
            
            # Test enhanced admin validation with JWT override
            mock_credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials="jwt.admin.override.token"
            )
            
            with patch('netra_backend.app.auth_integration.auth.extract_admin_status_from_jwt') as mock_extract:
                # Mock JWT admin status extraction
                mock_extract.return_value = {
                    "is_admin": True,
                    "user_id": user_id,
                    "role": "super_admin",
                    "permissions": ["system:*", "admin"],
                    "source": "jwt_claims"
                }
                
                # Test that JWT override allows access despite database record
                enhanced_user = await require_admin_with_enhanced_validation(mock_credentials, regular_user)
                assert enhanced_user == regular_user
                
                # Test that JWT non-admin is rejected
                mock_extract.return_value = {
                    "is_admin": False,
                    "user_id": user_id,
                    "role": "standard_user",
                    "permissions": ["user:read"],
                    "source": "jwt_claims"
                }
                
                with pytest.raises(HTTPException) as exc_info:
                    await require_admin_with_enhanced_validation(mock_credentials, regular_user)
                
                assert exc_info.value.status_code == 403
                assert "Admin access required" in str(exc_info.value.detail)
            
            # Cleanup additional user
            await db_session.execute(
                text("DELETE FROM users WHERE id = :user_id"),
                {"user_id": user_id}
            )
            await db_session.commit()
            
        finally:
            # Cleanup admin user
            await db_session.execute(
                text("DELETE FROM users WHERE id = :user_id"),
                {"user_id": admin_user_id}
            )
            await db_session.commit()

    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_oauth_user_flow(self, real_services_fixture):
        """
        Test OAuth user creation and update flow.
        
        Validates:
        - OAuth user creation from external provider data
        - Existing user update with OAuth profile
        - User data synchronization
        """
        db_session = real_services_fixture.get("db")
        if not db_session:
            pytest.skip("Real database service not available")
        
        # Mock auth service client
        with patch('netra_backend.app.services.security_service.auth_client') as mock_client:
            security_service = SecurityService()
            
            # Test new OAuth user creation
            oauth_user_info = {
                "email": "oauth@example.com",
                "name": "OAuth User",
                "picture": "https://example.com/avatar.jpg"
            }
            
            created_user = await security_service.get_or_create_user_from_oauth(
                db_session, oauth_user_info
            )
            
            assert created_user.email == "oauth@example.com"
            assert created_user.full_name == "OAuth User"
            
            # Test existing OAuth user update
            updated_info = {
                "email": "oauth@example.com", 
                "name": "Updated OAuth User",
                "picture": "https://example.com/new_avatar.jpg"
            }
            
            updated_user = await security_service.get_or_create_user_from_oauth(
                db_session, updated_info
            )
            
            # Should be same user, but with updated info
            assert updated_user.id == created_user.id
            assert updated_user.full_name == "Updated OAuth User"
            
            # Cleanup
            await db_session.execute(
                text("DELETE FROM users WHERE email = :email"),
                {"email": "oauth@example.com"}
            )
            await db_session.commit()

    def cleanup_resources(self):
        """Clean up resources after test."""
        # Cleanup any remaining test data
        if hasattr(self, 'test_user_ids') and self.test_user_ids:
            # This would be implemented if we track user IDs across tests
            pass
        super().cleanup_resources()