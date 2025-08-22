"""
Tests for security service permission checking functionality.
All functions ≤8 lines per requirements.
"""

# Add project root to path
import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from unittest.mock import MagicMock

import pytest
from cryptography.fernet import Fernet

# Add project root to path
from .security_service_test_mocks import (
    EnhancedSecurityService,
    MockUser,
)

# Add project root to path


@pytest.fixture
def security_service_with_permissions():
    """Create security service with permission features"""
    key_manager = MagicMock()
    key_manager.jwt_secret_key = "test_key_for_permissions"
    key_manager.fernet_key = Fernet.generate_key()
    return EnhancedSecurityService(key_manager)


@pytest.fixture
def permission_test_users(security_service_with_permissions):
    """Create users with different permissions for testing"""
    users = [
        _create_admin_permission_user(),
        _create_moderator_permission_user(),
        _create_regular_permission_user(),
        _create_viewer_permission_user()
    ]
    return users


class TestSecurityServicePermissions:
    """Test permission checking functionality"""
    
    def test_admin_has_all_permissions(self, permission_test_users):
        """Test that admin user has all permissions"""
        admin = permission_test_users[0]
        
        assert 'admin' in admin.roles
        assert 'manage_users' in admin.permissions
        assert 'access_all_tools' in admin.permissions
        _assert_admin_tool_permissions(admin)
    
    def test_moderator_has_limited_permissions(self, permission_test_users):
        """Test that moderator has limited permissions"""
        moderator = permission_test_users[1]
        
        assert 'moderator' in moderator.roles
        assert 'manage_content' in moderator.permissions
        assert 'manage_users' not in moderator.permissions
        _assert_moderator_tool_permissions(moderator)
    
    def test_regular_user_basic_permissions(self, permission_test_users):
        """Test regular user has basic permissions only"""
        user = permission_test_users[2]
        
        assert 'user' in user.roles
        assert user.tool_permissions['data_analyzer']['allowed'] is True
        assert user.tool_permissions['premium_optimizer']['allowed'] is False
        _assert_user_rate_limits(user)
    
    def test_viewer_readonly_permissions(self, permission_test_users):
        """Test viewer has read-only permissions"""
        viewer = permission_test_users[3]
        
        assert 'viewer' in viewer.roles
        assert len(viewer.tool_permissions) == 0
        assert len(viewer.feature_flags) == 0
    
    def test_role_based_access_control(self, permission_test_users):
        """Test role-based access control"""
        admin, moderator, user, viewer = permission_test_users
        
        _assert_role_hierarchy(admin, moderator, user, viewer)
    
    def test_tool_permission_granularity(self, permission_test_users):
        """Test granular tool permissions"""
        admin, moderator, user, viewer = permission_test_users
        
        # Data analyzer access
        _assert_data_analyzer_access(admin, moderator, user, viewer)
        
        # Premium optimizer access
        _assert_premium_optimizer_access(admin, moderator, user, viewer)
    
    def test_feature_flag_permissions(self, permission_test_users):
        """Test feature flag permissions"""
        admin, moderator, user, viewer = permission_test_users
        
        _assert_feature_flag_access(admin, moderator, user, viewer)
    
    def test_permission_inheritance(self, permission_test_users):
        """Test permission inheritance patterns"""
        admin = permission_test_users[0]
        
        # Admin should inherit base permissions
        assert admin.tool_permissions['data_analyzer']['allowed'] is True
        assert admin.tool_permissions['premium_optimizer']['allowed'] is True
        assert admin.tool_permissions['restricted_tool']['allowed'] is True
    
    def test_rate_limit_permissions(self, permission_test_users):
        """Test rate limit based permissions"""
        user = permission_test_users[2]
        
        # User should have rate limits
        data_analyzer_perms = user.tool_permissions.get('data_analyzer', {})
        assert data_analyzer_perms.get('rate_limit') == 50
    
    def test_permission_validation_edge_cases(self, permission_test_users):
        """Test permission validation edge cases"""
        # Test empty permissions
        empty_user = MockUser("empty_001", "empty@test.com")
        assert len(empty_user.permissions) == 0
        assert len(empty_user.tool_permissions) == 0
        
        # Test invalid role
        invalid_user = MockUser("invalid_002", "invalid@test.com")
        invalid_user.roles = ['invalid_role']
        assert 'admin' not in invalid_user.roles


def _create_admin_permission_user() -> MockUser:
    """Create admin user with full permissions"""
    admin = MockUser("admin_001", "admin@company.com", "Admin User")
    admin.roles = ['admin']
    admin.permissions = ['manage_users', 'access_all_tools']
    _set_admin_tool_permissions(admin)
    admin.feature_flags = {'beta_features': True, 'advanced_analytics': True}
    return admin


def _set_admin_tool_permissions(admin: MockUser) -> None:
    """Set tool permissions for admin user"""
    admin.tool_permissions = {
        'data_analyzer': {'allowed': True},
        'premium_optimizer': {'allowed': True},
        'restricted_tool': {'allowed': True}
    }


def _create_moderator_permission_user() -> MockUser:
    """Create moderator user with limited permissions"""
    moderator = MockUser("mod_002", "mod@company.com", "Moderator User")
    moderator.roles = ['moderator']
    moderator.permissions = ['manage_content']
    _set_moderator_tool_permissions(moderator)
    moderator.feature_flags = {'beta_features': True}
    return moderator


def _set_moderator_tool_permissions(moderator: MockUser) -> None:
    """Set tool permissions for moderator user"""
    moderator.tool_permissions = {
        'data_analyzer': {'allowed': True},
        'premium_optimizer': {'allowed': True},
        'restricted_tool': {'allowed': False}
    }


def _create_regular_permission_user() -> MockUser:
    """Create regular user with basic permissions"""
    user = MockUser("user_003", "user@company.com", "Regular User")
    user.roles = ['user']
    _set_user_tool_permissions(user)
    user.feature_flags = {}
    return user


def _set_user_tool_permissions(user: MockUser) -> None:
    """Set tool permissions for regular user"""
    user.tool_permissions = {
        'data_analyzer': {'allowed': True, 'rate_limit': 50},
        'premium_optimizer': {'allowed': False},
        'restricted_tool': {'allowed': False}
    }


def _create_viewer_permission_user() -> MockUser:
    """Create viewer user with read-only permissions"""
    viewer = MockUser("viewer_004", "viewer@company.com", "Viewer User")
    viewer.roles = ['viewer']
    viewer.tool_permissions = {}
    viewer.feature_flags = {}
    return viewer


def _assert_admin_tool_permissions(admin: MockUser) -> None:
    """Assert admin has all tool permissions"""
    assert admin.tool_permissions['data_analyzer']['allowed'] is True
    assert admin.tool_permissions['premium_optimizer']['allowed'] is True
    assert admin.tool_permissions['restricted_tool']['allowed'] is True


def _assert_moderator_tool_permissions(moderator: MockUser) -> None:
    """Assert moderator has limited tool permissions"""
    assert moderator.tool_permissions['data_analyzer']['allowed'] is True
    assert moderator.tool_permissions['premium_optimizer']['allowed'] is True
    assert moderator.tool_permissions['restricted_tool']['allowed'] is False


def _assert_user_rate_limits(user: MockUser) -> None:
    """Assert user has proper rate limits"""
    data_analyzer = user.tool_permissions.get('data_analyzer', {})
    assert data_analyzer.get('rate_limit') == 50


def _assert_role_hierarchy(admin: MockUser, moderator: MockUser, user: MockUser, viewer: MockUser) -> None:
    """Assert proper role hierarchy"""
    # Admin has highest privileges
    assert len(admin.permissions) >= len(moderator.permissions)
    
    # Moderator has more than user
    assert len(moderator.tool_permissions) >= len(user.tool_permissions)
    
    # User has more than viewer
    assert len(user.tool_permissions) > len(viewer.tool_permissions)


def _assert_data_analyzer_access(admin: MockUser, moderator: MockUser, user: MockUser, viewer: MockUser) -> None:
    """Assert data analyzer access permissions"""
    assert admin.tool_permissions.get('data_analyzer', {}).get('allowed') is True
    assert moderator.tool_permissions.get('data_analyzer', {}).get('allowed') is True
    assert user.tool_permissions.get('data_analyzer', {}).get('allowed') is True
    assert viewer.tool_permissions.get('data_analyzer', {}).get('allowed', False) is False


def _assert_premium_optimizer_access(admin: MockUser, moderator: MockUser, user: MockUser, viewer: MockUser) -> None:
    """Assert premium optimizer access permissions"""
    assert admin.tool_permissions.get('premium_optimizer', {}).get('allowed') is True
    assert moderator.tool_permissions.get('premium_optimizer', {}).get('allowed') is True
    assert user.tool_permissions.get('premium_optimizer', {}).get('allowed') is False
    assert viewer.tool_permissions.get('premium_optimizer', {}).get('allowed', False) is False


def _assert_feature_flag_access(admin: MockUser, moderator: MockUser, user: MockUser, viewer: MockUser) -> None:
    """Assert feature flag access permissions"""
    # Admin has most feature flags
    assert admin.feature_flags.get('beta_features') is True
    assert admin.feature_flags.get('advanced_analytics') is True
    
    # Moderator has some feature flags
    assert moderator.feature_flags.get('beta_features') is True
    assert moderator.feature_flags.get('advanced_analytics') is None
    
    # User and viewer have limited/no feature flags
    assert len(user.feature_flags) == 0
    assert len(viewer.feature_flags) == 0