"""
Enhanced tests for security service authentication.
All functions ≤8 lines per requirements.
"""

import pytest
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Any
from unittest.mock import AsyncMock, MagicMock, patch
from cryptography.fernet import Fernet

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.services.key_manager import KeyManager
from netra_backend.tests.security_service_test_mocks import (

# Add project root to path
    MockUser, EnhancedSecurityService, create_test_user, create_admin_user,
    create_locked_user, assert_authentication_success, assert_authentication_failure
)


@pytest.fixture
def key_manager():
    """Create key manager for testing"""
    mock_settings = MagicMock()
    mock_settings.jwt_secret_key = "test_jwt_secret_key_that_is_long_enough_for_testing_purposes_and_security"
    mock_settings.fernet_key = Fernet.generate_key()
    return KeyManager.load_from_settings(mock_settings)


@pytest.fixture
def enhanced_security_service(key_manager):
    """Create enhanced security service"""
    return EnhancedSecurityService(key_manager)


@pytest.fixture
def mock_db_session():
    """Create mock database session"""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def sample_users(enhanced_security_service):
    """Create sample users for testing"""
    users = []
    
    # Admin user
    admin = _create_admin_test_user(enhanced_security_service)
    users.append(admin)
    
    # Regular user  
    user = _create_regular_test_user(enhanced_security_service)
    users.append(user)
    
    # Locked user
    locked = _create_locked_test_user(enhanced_security_service)
    users.append(locked)
    
    return users


class TestSecurityServiceAuthenticationEnhanced:
    """Enhanced tests for security service authentication"""
    
    async def test_successful_authentication_admin(self, enhanced_security_service, sample_users):
        """Test successful authentication for admin user"""
        admin_user = sample_users[0]
        
        with patch.object(enhanced_security_service, '_get_user_by_email', return_value=admin_user):
            result = await enhanced_security_service.enhanced_authenticate_user(
                admin_user.email, "admin_password"
            )
        
        assert_authentication_success(result)
        _assert_admin_permissions(result)
    
    async def test_successful_authentication_regular_user(self, enhanced_security_service, sample_users):
        """Test successful authentication for regular user"""
        regular_user = sample_users[1]
        
        with patch.object(enhanced_security_service, '_get_user_by_email', return_value=regular_user):
            result = await enhanced_security_service.enhanced_authenticate_user(
                regular_user.email, "user_password"
            )
        
        assert_authentication_success(result)
        _assert_user_permissions(result)
    
    async def test_failed_authentication_wrong_password(self, enhanced_security_service, sample_users):
        """Test failed authentication with wrong password"""
        admin_user = sample_users[0]
        
        with patch.object(enhanced_security_service, '_get_user_by_email', return_value=admin_user):
            result = await enhanced_security_service.enhanced_authenticate_user(
                admin_user.email, "wrong_password"
            )
        
        assert_authentication_failure(result)
    
    async def test_failed_authentication_nonexistent_user(self, enhanced_security_service):
        """Test failed authentication for nonexistent user"""
        with patch.object(enhanced_security_service, '_get_user_by_email', return_value=None):
            result = await enhanced_security_service.enhanced_authenticate_user(
                "nonexistent@test.com", "any_password"
            )
        
        assert_authentication_failure(result)
    
    async def test_locked_account_authentication(self, enhanced_security_service, sample_users):
        """Test authentication attempt on locked account"""
        locked_user = sample_users[2]
        
        with patch.object(enhanced_security_service, '_get_user_by_email', return_value=locked_user):
            result = await enhanced_security_service.enhanced_authenticate_user(
                locked_user.email, "locked_password"
            )
        
        assert_authentication_failure(result)
        assert "locked" in result.get('error', '').lower()
    
    async def test_token_generation_and_validation(self, enhanced_security_service, sample_users):
        """Test token generation and validation"""
        admin_user = sample_users[0]
        
        # Generate token
        token_data = _create_token_data(admin_user)
        token = enhanced_security_service.create_access_token(token_data)
        
        # Validate token
        validation_result = await enhanced_security_service.validate_token_jwt(token)
        _assert_token_validation_success(validation_result, admin_user)
    
    async def test_expired_token_validation(self, enhanced_security_service, sample_users):
        """Test validation of expired token"""
        admin_user = sample_users[0]
        
        # Create expired token
        expired_token_data = _create_expired_token_data(admin_user)
        token = enhanced_security_service.create_access_token(expired_token_data)
        
        # Validate expired token
        validation_result = await enhanced_security_service.validate_token_jwt(token)
        _assert_token_validation_failure(validation_result)
    
    async def test_session_caching_functionality(self, enhanced_security_service, sample_users):
        """Test session caching functionality"""
        admin_user = sample_users[0]
        token_data = _create_token_data(admin_user)
        token = enhanced_security_service.create_access_token(token_data)
        
        # First validation (cache miss)
        result1 = await enhanced_security_service.validate_session_with_cache(token)
        
        # Second validation (cache hit)
        result2 = await enhanced_security_service.validate_session_with_cache(token)
        
        _assert_cached_session_consistency(result1, result2)
    
    async def test_rate_limiting_functionality(self, enhanced_security_service):
        """Test rate limiting functionality"""
        identifier = "test_user_ip"
        
        # Should allow first few attempts
        for i in range(5):
            allowed = await enhanced_security_service.check_rate_limit(identifier, limit=10)
            assert allowed is True
            enhanced_security_service.record_rate_limit_attempt(identifier)
        
        # Should still be under limit
        allowed = await enhanced_security_service.check_rate_limit(identifier, limit=10)
        assert allowed is True


def _create_admin_test_user(security_service) -> MockUser:
    """Create admin test user"""
    admin = MockUser("admin_123", "admin@test.com", "Test Admin")
    admin.hashed_password = security_service.get_password_hash("admin_password")
    admin.roles = ['admin']
    admin.permissions = ['access_all_tools', 'manage_users']
    return admin


def _create_regular_test_user(security_service) -> MockUser:
    """Create regular test user"""
    user = MockUser("user_456", "user@test.com", "Test User")
    user.hashed_password = security_service.get_password_hash("user_password")
    user.roles = ['user']
    _set_user_tool_permissions(user)
    return user


def _set_user_tool_permissions(user: MockUser) -> None:
    """Set tool permissions for regular user"""
    user.tool_permissions = {
        'data_analyzer': {'allowed': True, 'rate_limit': 100},
        'premium_optimizer': {'allowed': False}
    }


def _create_locked_test_user(security_service) -> MockUser:
    """Create locked test user"""
    locked = MockUser("locked_789", "locked@test.com", "Locked User")
    locked.hashed_password = security_service.get_password_hash("locked_password")
    locked.lock_account(30)
    locked.failed_login_attempts = 5
    return locked


def _assert_admin_permissions(result: Dict[str, Any]) -> None:
    """Assert admin permissions in result"""
    user_data = result.get('user', {})
    assert 'admin' in user_data.get('roles', [])
    assert 'access_all_tools' in user_data.get('permissions', [])


def _assert_user_permissions(result: Dict[str, Any]) -> None:
    """Assert regular user permissions in result"""
    user_data = result.get('user', {})
    assert 'user' in user_data.get('roles', [])
    assert user_data.get('tool_permissions', {}).get('data_analyzer', {}).get('allowed') is True


def _create_token_data(user: MockUser):
    """Create token data for user"""
    from netra_backend.app.routes.unified_tools.models import TokenPayload
    return TokenPayload(
        sub=user.email,
        user_id=user.id,
        roles=user.roles,
        permissions=user.permissions
    )


def _create_expired_token_data(user: MockUser):
    """Create expired token data"""
    from netra_backend.app.routes.unified_tools.models import TokenPayload
    return TokenPayload(
        sub=user.email,
        user_id=user.id,
        roles=user.roles,
        permissions=user.permissions,
        exp=datetime.now(UTC) - timedelta(hours=1)  # Expired 1 hour ago
    )


def _assert_token_validation_success(validation_result: Dict[str, Any], user: MockUser) -> None:
    """Assert token validation was successful"""
    assert validation_result.get('valid') is True
    assert validation_result.get('user_id') == user.id
    assert validation_result.get('email') == user.email


def _assert_token_validation_failure(validation_result: Dict[str, Any]) -> None:
    """Assert token validation failed"""
    assert validation_result.get('valid') is False
    assert 'error' in validation_result


def _assert_cached_session_consistency(result1: Dict[str, Any], result2: Dict[str, Any]) -> None:
    """Assert cached session results are consistent"""
    assert result1.get('user_id') == result2.get('user_id')
    assert result1.get('email') == result2.get('email')
    assert result2.get('cached_at') is not None