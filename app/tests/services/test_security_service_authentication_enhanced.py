"""
Enhanced comprehensive tests for Security Service authentication, token validation, and permission checks
Tests authentication flow, token management, permission validation, and security edge cases
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch, call
from cryptography.fernet import Fernet
from jose import jwt, JWTError

from app.services.security_service import SecurityService
from app.services.key_manager import KeyManager
from app.db import models_postgres
from app import schemas
from app.core.exceptions_base import NetraException
from app.config import settings


class MockUser:
    """Mock user model for testing"""
    
    def __init__(self, id: str, email: str, full_name: str = None, hashed_password: str = None):
        self.id = id
        self.email = email
        self.full_name = full_name
        self.hashed_password = hashed_password
        self.picture = None
        self.is_active = True
        self.is_verified = True
        self.created_at = datetime.now(UTC)
        self.last_login = None
        self.failed_login_attempts = 0
        self.account_locked_until = None
        
        # Permission-related fields
        self.roles = ['user']  # Default role
        self.permissions = []
        self.groups = []
        self.tool_permissions = {}
        self.feature_flags = {}


class EnhancedSecurityService(SecurityService):
    """Enhanced security service with additional features"""
    
    def __init__(self, key_manager: KeyManager):
        super().__init__(key_manager)
        self.max_login_attempts = 5
        self.lockout_duration = timedelta(minutes=30)
        self.token_blacklist = set()
        self.session_store = {}  # session_id -> session_data
        
    def check_account_lockout(self, user: MockUser) -> bool:
        """Check if account is locked due to failed attempts"""
        if user.account_locked_until and datetime.now(UTC) < user.account_locked_until:
            return True
        return False
    
    def increment_failed_attempts(self, user: MockUser):
        """Increment failed login attempts and lock if necessary"""
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= self.max_login_attempts:
            user.account_locked_until = datetime.now(UTC) + self.lockout_duration
    
    def reset_failed_attempts(self, user: MockUser):
        """Reset failed login attempts on successful login"""
        user.failed_login_attempts = 0
        user.account_locked_until = None
        user.last_login = datetime.now(UTC)
    
    def blacklist_token(self, token: str):
        """Add token to blacklist"""
        self.token_blacklist.add(token)
    
    def is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted"""
        return token in self.token_blacklist
    
    def create_session(self, user_id: str, session_data: Dict[str, Any]) -> str:
        """Create user session"""
        session_id = f"session_{user_id}_{datetime.now(UTC).timestamp()}"
        self.session_store[session_id] = {
            'user_id': user_id,
            'created_at': datetime.now(UTC),
            'last_accessed': datetime.now(UTC),
            **session_data
        }
        return session_id
    
    def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Validate and update session"""
        if session_id not in self.session_store:
            return None
        
        session = self.session_store[session_id]
        
        # Check session expiry (e.g., 24 hours)
        if datetime.now(UTC) - session['created_at'] > timedelta(hours=24):
            del self.session_store[session_id]
            return None
        
        # Update last accessed
        session['last_accessed'] = datetime.now(UTC)
        return session
    
    def check_permission(self, user: MockUser, permission: str) -> bool:
        """Check if user has specific permission"""
        if permission in user.permissions:
            return True
        
        # Check role-based permissions
        role_permissions = {
            'admin': ['create', 'read', 'update', 'delete', 'manage_users', 'access_all_tools'],
            'moderator': ['create', 'read', 'update', 'manage_content'],
            'user': ['read', 'create_own', 'update_own'],
            'viewer': ['read']
        }
        
        for role in user.roles:
            if role in role_permissions and permission in role_permissions[role]:
                return True
        
        return False
    
    def check_tool_permission(self, user: MockUser, tool_name: str) -> bool:
        """Check if user has permission to use specific tool"""
        tool_perms = user.tool_permissions.get(tool_name, {})
        return tool_perms.get('allowed', False)
    
    def check_feature_flag(self, user: MockUser, feature: str) -> bool:
        """Check if feature is enabled for user"""
        return user.feature_flags.get(feature, False)


class TestSecurityServiceAuthenticationEnhanced:
    """Enhanced tests for security service authentication"""
    
    @pytest.fixture
    def key_manager(self):
        """Create key manager for testing"""
        mock_settings = MagicMock()
        mock_settings.jwt_secret_key = "test_jwt_secret_key_that_is_long_enough_for_testing_purposes_and_security"
        mock_settings.fernet_key = Fernet.generate_key()
        return KeyManager.load_from_settings(mock_settings)
    
    @pytest.fixture
    def enhanced_security_service(self, key_manager):
        """Create enhanced security service"""
        return EnhancedSecurityService(key_manager)
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session"""
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        return session
    
    @pytest.fixture
    def sample_users(self, enhanced_security_service):
        """Create sample users for testing"""
        users = []
        
        # Admin user
        admin = MockUser("admin_123", "admin@test.com", "Test Admin")
        admin.hashed_password = enhanced_security_service.get_password_hash("admin_password")
        admin.roles = ['admin']
        admin.permissions = ['access_all_tools', 'manage_users']
        users.append(admin)
        
        # Regular user
        user = MockUser("user_456", "user@test.com", "Test User")
        user.hashed_password = enhanced_security_service.get_password_hash("user_password")
        user.roles = ['user']
        user.tool_permissions = {
            'data_analyzer': {'allowed': True, 'rate_limit': 100},
            'premium_optimizer': {'allowed': False}
        }
        users.append(user)
        
        # Locked user
        locked = MockUser("locked_789", "locked@test.com", "Locked User")
        locked.hashed_password = enhanced_security_service.get_password_hash("locked_password")
        locked.failed_login_attempts = 5
        locked.account_locked_until = datetime.now(UTC) + timedelta(minutes=15)
        users.append(locked)
        
        return users
    
    def test_password_hashing_and_verification(self, enhanced_security_service):
        """Test password hashing and verification"""
        password = "test_secure_password_123"
        
        # Hash password
        hashed = enhanced_security_service.get_password_hash(password)
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are long
        
        # Verify correct password
        assert enhanced_security_service.verify_password(password, hashed) == True
        
        # Verify incorrect password
        assert enhanced_security_service.verify_password("wrong_password", hashed) == False
    
    def test_access_token_creation_and_validation(self, enhanced_security_service):
        """Test access token creation and validation"""
        token_payload = schemas.TokenPayload(sub="test@example.com")
        
        # Create token
        token = enhanced_security_service.create_access_token(token_payload)
        assert token != None
        assert isinstance(token, str)
        
        # Validate token
        email = enhanced_security_service.get_user_email_from_token(token)
        assert email == "test@example.com"
        
        # Decode full token payload
        payload = enhanced_security_service.decode_access_token(token)
        assert payload != None
        assert payload["sub"] == "test@example.com"
        assert "exp" in payload
    
    def test_access_token_expiration(self, enhanced_security_service):
        """Test access token expiration handling"""
        token_payload = schemas.TokenPayload(sub="test@example.com")
        
        # Create token with short expiry
        short_expiry = timedelta(seconds=1)
        token = enhanced_security_service.create_access_token(token_payload, short_expiry)
        
        # Token should be valid initially
        email = enhanced_security_service.get_user_email_from_token(token)
        assert email == "test@example.com"
        
        # Wait for expiry - need to wait more than 5 seconds due to tolerance
        import time
        time.sleep(6.1)  # Wait 6.1 seconds to exceed the 5-second tolerance
        
        # Token should be expired
        expired_email = enhanced_security_service.get_user_email_from_token(token)
        assert expired_email == None
        
        expired_payload = enhanced_security_service.decode_access_token(token)
        assert expired_payload == None
    
    def test_invalid_token_handling(self, enhanced_security_service):
        """Test handling of various invalid tokens"""
        # Completely invalid token
        assert enhanced_security_service.get_user_email_from_token("invalid_token") == None
        assert enhanced_security_service.decode_access_token("invalid_token") == None
        
        # Empty token
        assert enhanced_security_service.get_user_email_from_token("") == None
        
        # Malformed JWT
        malformed_jwt = "header.payload"  # Missing signature
        assert enhanced_security_service.get_user_email_from_token(malformed_jwt) == None
        
        # JWT with wrong signature
        valid_payload = {"sub": "test@example.com", "exp": datetime.now(UTC).timestamp() + 3600}
        wrong_signature_token = jwt.encode(valid_payload, "wrong_secret", algorithm="HS256")
        assert enhanced_security_service.get_user_email_from_token(wrong_signature_token) == None
    
    @pytest.mark.asyncio
    async def test_user_authentication_success(self, enhanced_security_service, mock_db_session, sample_users):
        """Test successful user authentication"""
        user = sample_users[1]  # Regular user
        
        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = user
        mock_db_session.execute.return_value = mock_result
        
        # Authenticate user
        authenticated_user = await enhanced_security_service.authenticate_user(
            mock_db_session, "user@test.com", "user_password"
        )
        
        assert authenticated_user != None
        assert authenticated_user.email == "user@test.com"
        assert authenticated_user.failed_login_attempts == 0
    
    @pytest.mark.asyncio
    async def test_user_authentication_wrong_password(self, enhanced_security_service, mock_db_session, sample_users):
        """Test authentication with wrong password"""
        user = sample_users[1]  # Regular user
        
        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = user
        mock_db_session.execute.return_value = mock_result
        
        # Authenticate with wrong password
        authenticated_user = await enhanced_security_service.authenticate_user(
            mock_db_session, "user@test.com", "wrong_password"
        )
        
        assert authenticated_user == None
    
    @pytest.mark.asyncio
    async def test_user_authentication_nonexistent_user(self, enhanced_security_service, mock_db_session):
        """Test authentication with nonexistent user"""
        # Mock empty query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        # Authenticate nonexistent user
        authenticated_user = await enhanced_security_service.authenticate_user(
            mock_db_session, "nonexistent@test.com", "any_password"
        )
        
        assert authenticated_user == None
    
    def test_account_lockout_detection(self, enhanced_security_service, sample_users):
        """Test account lockout detection"""
        locked_user = sample_users[2]  # Locked user
        
        # Should detect lockout
        assert enhanced_security_service.check_account_lockout(locked_user) == True
        
        # Regular user should not be locked
        regular_user = sample_users[1]
        assert enhanced_security_service.check_account_lockout(regular_user) == False
    
    def test_failed_login_attempt_tracking(self, enhanced_security_service, sample_users):
        """Test failed login attempt tracking and lockout"""
        user = sample_users[1]  # Regular user
        
        # Initial state
        assert user.failed_login_attempts == 0
        assert user.account_locked_until == None
        
        # Increment failed attempts
        for i in range(4):
            enhanced_security_service.increment_failed_attempts(user)
            assert user.failed_login_attempts == i + 1
            assert user.account_locked_until == None  # Not locked yet
        
        # Fifth attempt should lock account
        enhanced_security_service.increment_failed_attempts(user)
        assert user.failed_login_attempts == 5
        assert user.account_locked_until != None
        assert user.account_locked_until > datetime.now(UTC)
    
    def test_successful_login_resets_attempts(self, enhanced_security_service, sample_users):
        """Test that successful login resets failed attempts"""
        user = sample_users[1]  # Regular user
        
        # Set failed attempts
        user.failed_login_attempts = 3
        
        # Reset on successful login
        enhanced_security_service.reset_failed_attempts(user)
        
        assert user.failed_login_attempts == 0
        assert user.account_locked_until == None
        assert user.last_login != None
    
    def test_token_blacklisting(self, enhanced_security_service):
        """Test token blacklisting functionality"""
        token_payload = schemas.TokenPayload(sub="test@example.com")
        token = enhanced_security_service.create_access_token(token_payload)
        
        # Initially not blacklisted
        assert enhanced_security_service.is_token_blacklisted(token) == False
        
        # Blacklist token
        enhanced_security_service.blacklist_token(token)
        
        # Should now be blacklisted
        assert enhanced_security_service.is_token_blacklisted(token) == True
    
    def test_session_management(self, enhanced_security_service):
        """Test session creation and validation"""
        user_id = "user_123"
        session_data = {"ip_address": "192.168.1.1", "user_agent": "Test Browser"}
        
        # Create session
        session_id = enhanced_security_service.create_session(user_id, session_data)
        assert session_id.startswith("session_user_123_")
        
        # Validate session
        session = enhanced_security_service.validate_session(session_id)
        assert session != None
        assert session['user_id'] == user_id
        assert session['ip_address'] == "192.168.1.1"
        
        # Invalid session ID
        invalid_session = enhanced_security_service.validate_session("invalid_session_id")
        assert invalid_session == None
    
    def test_session_expiry(self, enhanced_security_service):
        """Test session expiry handling"""
        user_id = "user_456"
        session_data = {"test": "data"}
        
        # Create session
        session_id = enhanced_security_service.create_session(user_id, session_data)
        
        # Mock old creation time
        enhanced_security_service.session_store[session_id]['created_at'] = (
            datetime.now(UTC) - timedelta(hours=25)  # Expired
        )
        
        # Should return None for expired session
        expired_session = enhanced_security_service.validate_session(session_id)
        assert expired_session == None
        
        # Session should be removed from store
        assert session_id not in enhanced_security_service.session_store


class TestSecurityServicePermissions:
    """Test permission checking functionality"""
    
    @pytest.fixture
    def security_service_with_permissions(self):
        """Create security service with permission features"""
        key_manager = MagicMock()
        key_manager.jwt_secret_key = "test_key_for_permissions"
        key_manager.fernet_key = Fernet.generate_key()
        return EnhancedSecurityService(key_manager)
    
    @pytest.fixture
    def permission_test_users(self, security_service_with_permissions):
        """Create users with different permissions for testing"""
        # Admin user with all permissions
        admin = MockUser("admin_001", "admin@company.com", "Admin User")
        admin.roles = ['admin']
        admin.permissions = ['manage_users', 'access_all_tools']
        admin.tool_permissions = {
            'data_analyzer': {'allowed': True},
            'premium_optimizer': {'allowed': True},
            'restricted_tool': {'allowed': True}
        }
        admin.feature_flags = {'beta_features': True, 'advanced_analytics': True}
        
        # Moderator user with limited permissions
        moderator = MockUser("mod_002", "mod@company.com", "Moderator User")
        moderator.roles = ['moderator']
        moderator.permissions = ['manage_content']
        moderator.tool_permissions = {
            'data_analyzer': {'allowed': True},
            'premium_optimizer': {'allowed': True},
            'restricted_tool': {'allowed': False}
        }
        moderator.feature_flags = {'beta_features': True}
        
        # Regular user with basic permissions
        user = MockUser("user_003", "user@company.com", "Regular User")
        user.roles = ['user']
        user.tool_permissions = {
            'data_analyzer': {'allowed': True, 'rate_limit': 50},
            'premium_optimizer': {'allowed': False},
            'restricted_tool': {'allowed': False}
        }
        user.feature_flags = {}
        
        # Viewer with read-only permissions
        viewer = MockUser("viewer_004", "viewer@company.com", "Viewer User")
        viewer.roles = ['viewer']
        viewer.tool_permissions = {}
        viewer.feature_flags = {}
        
        return {
            'admin': admin,
            'moderator': moderator,
            'user': user,
            'viewer': viewer
        }
    
    def test_role_based_permissions(self, security_service_with_permissions, permission_test_users):
        """Test role-based permission checking"""
        service = security_service_with_permissions
        users = permission_test_users
        
        # Admin permissions
        assert service.check_permission(users['admin'], 'create') == True
        assert service.check_permission(users['admin'], 'read') == True
        assert service.check_permission(users['admin'], 'update') == True
        assert service.check_permission(users['admin'], 'delete') == True
        assert service.check_permission(users['admin'], 'manage_users') == True
        
        # Moderator permissions
        assert service.check_permission(users['moderator'], 'create') == True
        assert service.check_permission(users['moderator'], 'read') == True
        assert service.check_permission(users['moderator'], 'update') == True
        assert service.check_permission(users['moderator'], 'delete') == False
        assert service.check_permission(users['moderator'], 'manage_users') == False
        
        # User permissions
        assert service.check_permission(users['user'], 'read') == True
        assert service.check_permission(users['user'], 'create_own') == True
        assert service.check_permission(users['user'], 'update_own') == True
        assert service.check_permission(users['user'], 'delete') == False
        assert service.check_permission(users['user'], 'manage_users') == False
        
        # Viewer permissions
        assert service.check_permission(users['viewer'], 'read') == True
        assert service.check_permission(users['viewer'], 'create') == False
        assert service.check_permission(users['viewer'], 'update') == False
        assert service.check_permission(users['viewer'], 'delete') == False
    
    def test_tool_specific_permissions(self, security_service_with_permissions, permission_test_users):
        """Test tool-specific permission checking"""
        service = security_service_with_permissions
        users = permission_test_users
        
        # Admin - should have access to all tools
        assert service.check_tool_permission(users['admin'], 'data_analyzer') == True
        assert service.check_tool_permission(users['admin'], 'premium_optimizer') == True
        assert service.check_tool_permission(users['admin'], 'restricted_tool') == True
        
        # Moderator - mixed access
        assert service.check_tool_permission(users['moderator'], 'data_analyzer') == True
        assert service.check_tool_permission(users['moderator'], 'premium_optimizer') == True
        assert service.check_tool_permission(users['moderator'], 'restricted_tool') == False
        
        # User - limited access
        assert service.check_tool_permission(users['user'], 'data_analyzer') == True
        assert service.check_tool_permission(users['user'], 'premium_optimizer') == False
        assert service.check_tool_permission(users['user'], 'restricted_tool') == False
        
        # Viewer - no tool access
        assert service.check_tool_permission(users['viewer'], 'data_analyzer') == False
        assert service.check_tool_permission(users['viewer'], 'premium_optimizer') == False
        assert service.check_tool_permission(users['viewer'], 'restricted_tool') == False
    
    def test_feature_flag_checking(self, security_service_with_permissions, permission_test_users):
        """Test feature flag checking"""
        service = security_service_with_permissions
        users = permission_test_users
        
        # Admin - has beta features and advanced analytics
        assert service.check_feature_flag(users['admin'], 'beta_features') == True
        assert service.check_feature_flag(users['admin'], 'advanced_analytics') == True
        assert service.check_feature_flag(users['admin'], 'non_existent_feature') == False
        
        # Moderator - has beta features only
        assert service.check_feature_flag(users['moderator'], 'beta_features') == True
        assert service.check_feature_flag(users['moderator'], 'advanced_analytics') == False
        
        # User and Viewer - no feature flags
        assert service.check_feature_flag(users['user'], 'beta_features') == False
        assert service.check_feature_flag(users['viewer'], 'beta_features') == False
    
    def test_explicit_permissions_override_roles(self, security_service_with_permissions, permission_test_users):
        """Test that explicit permissions override role-based permissions"""
        service = security_service_with_permissions
        user = permission_test_users['user']
        
        # User normally doesn't have manage_users permission through role
        assert service.check_permission(user, 'manage_users') == False
        
        # Add explicit permission
        user.permissions.append('manage_users')
        
        # Should now have permission
        assert service.check_permission(user, 'manage_users') == True


class TestSecurityServiceOAuth:
    """Test OAuth integration functionality"""
    
    @pytest.fixture
    def oauth_security_service(self):
        """Create security service for OAuth testing"""
        key_manager = MagicMock()
        key_manager.jwt_secret_key = "oauth_test_key"
        key_manager.fernet_key = Fernet.generate_key()
        return EnhancedSecurityService(key_manager)
    
    @pytest.mark.asyncio
    async def test_create_user_from_oauth_new_user(self, oauth_security_service):
        """Test creating new user from OAuth data"""
        mock_db_session = AsyncMock()
        
        oauth_user_info = {
            "email": "oauth@example.com",
            "name": "OAuth User",
            "picture": "https://example.com/avatar.jpg"
        }
        
        # Mock user creation
        created_user = MockUser("oauth_123", "oauth@example.com", "OAuth User")
        created_user.picture = "https://example.com/avatar.jpg"
        
        # Mock the database session operations
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None
        
        # Mock get_user to return None (no existing user) and User constructor
        with patch.object(oauth_security_service, 'get_user', return_value=None), \
             patch('app.db.models_postgres.User', return_value=created_user):
            user = await oauth_security_service.get_or_create_user_from_oauth(
                mock_db_session, oauth_user_info
            )
        
        # Verify user creation was attempted
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_existing_user_from_oauth(self, oauth_security_service):
        """Test getting existing user from OAuth data"""
        mock_db_session = AsyncMock()
        
        # Mock existing user
        existing_user = MockUser("existing_456", "existing@example.com", "Existing User")
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = existing_user
        mock_db_session.execute.return_value = mock_result
        
        oauth_user_info = {
            "email": "existing@example.com",
            "name": "OAuth User",
            "picture": "https://example.com/avatar.jpg"
        }
        
        user = await oauth_security_service.get_or_create_user_from_oauth(
            mock_db_session, oauth_user_info
        )
        
        # Should return existing user without creating new one
        assert user == existing_user
        mock_db_session.add.assert_not_called()
        mock_db_session.commit.assert_not_called()


class TestSecurityServiceConcurrency:
    """Test security service under concurrent conditions"""
    
    @pytest.fixture
    def concurrent_security_service(self):
        """Create security service for concurrency testing"""
        key_manager = MagicMock()
        key_manager.jwt_secret_key = "concurrent_test_key_that_is_sufficiently_long_for_security"
        key_manager.fernet_key = Fernet.generate_key()
        return EnhancedSecurityService(key_manager)
    
    @pytest.mark.asyncio
    async def test_concurrent_token_validation(self, concurrent_security_service):
        """Test concurrent token validation"""
        # Create multiple tokens
        tokens = []
        for i in range(10):
            payload = schemas.TokenPayload(sub=f"user_{i}@example.com")
            token = concurrent_security_service.create_access_token(payload)
            tokens.append(token)
        
        # Validate tokens concurrently
        async def validate_token(token):
            return concurrent_security_service.get_user_email_from_token(token)
        
        tasks = [validate_token(token) for token in tokens]
        results = await asyncio.gather(*tasks)
        
        # All validations should succeed
        assert len(results) == 10
        assert all(result != None for result in results)
        assert all(f"user_{i}@example.com" in results for i in range(10))
    
    @pytest.mark.asyncio
    async def test_concurrent_session_management(self, concurrent_security_service):
        """Test concurrent session creation and validation"""
        # Create sessions concurrently
        async def create_and_validate_session(user_id):
            session_data = {"test": f"data_{user_id}"}
            session_id = concurrent_security_service.create_session(user_id, session_data)
            
            # Immediately validate
            session = concurrent_security_service.validate_session(session_id)
            return session != None
        
        tasks = [create_and_validate_session(f"user_{i}") for i in range(20)]
        results = await asyncio.gather(*tasks)
        
        # All sessions should be created and validated successfully
        assert all(result == True for result in results)
        assert len(concurrent_security_service.session_store) == 20
    
    def test_concurrent_failed_login_tracking(self, concurrent_security_service):
        """Test concurrent failed login attempt tracking"""
        user = MockUser("concurrent_user", "test@concurrent.com", "Test User")
        
        # Simulate concurrent failed login attempts
        import threading
        
        def increment_attempts():
            for _ in range(2):
                concurrent_security_service.increment_failed_attempts(user)
        
        # Start multiple threads
        threads = []
        for _ in range(3):  # 3 threads * 2 attempts = 6 total attempts
            thread = threading.Thread(target=increment_attempts)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Should have recorded all attempts and locked account
        assert user.failed_login_attempts == 6
        assert user.account_locked_until != None