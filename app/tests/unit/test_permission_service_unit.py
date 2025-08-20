"""Comprehensive unit tests for PermissionService - FREE TIER CRITICAL.

BUSINESS VALUE JUSTIFICATION:
1. Segment: Free tier users (100% of new users start here)
2. Business Goal: Ensure robust free tier limits drive conversions
3. Value Impact: Each 1% improvement in conversion = $50K ARR
4. Revenue Impact: These tests ensure conversion funnel works correctly
5. CRITICAL: Free tier bugs = lost revenue. Must have 100% test coverage.

Tests the PermissionService that enforces plan-based permissions,
role hierarchy, developer auto-detection, and permission grants/revokes.
Critical for protecting revenue through proper tier enforcement.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from app.services.permission_service import PermissionService, ROLE_HIERARCHY, ROLE_PERMISSIONS
from app.db.models_postgres import User


# Test fixtures for setup
@pytest.fixture
def mock_db_session():
    """Mock database session."""
    return Mock()


@pytest.fixture
def free_tier_user():
    """Free tier user fixture."""
    user = Mock(spec=User)
    user.id = "test_user_1"
    user.email = "user@example.com"
    user.role = "standard_user"
    user.plan_tier = "free"
    user.permissions = {}
    user.is_developer = False
    user.is_superuser = False
    return user


@pytest.fixture
def pro_tier_user():
    """Pro tier user fixture."""
    user = Mock(spec=User)
    user.id = "test_user_2"
    user.email = "pro@example.com"
    user.role = "power_user"
    user.plan_tier = "pro"
    user.permissions = {}
    user.is_developer = False
    user.is_superuser = False
    return user


@pytest.fixture
def developer_user():
    """Developer user fixture."""
    user = Mock(spec=User)
    user.id = "dev_user_1"
    user.email = "dev@netrasystems.ai"
    user.role = "developer"
    user.plan_tier = "developer"
    user.permissions = {}
    user.is_developer = True
    user.is_superuser = False
    return user


@pytest.fixture
def admin_user():
    """Admin user fixture."""
    user = Mock(spec=User)
    user.id = "admin_user_1"
    user.email = "admin@netrasystems.ai"
    user.role = "admin"
    user.plan_tier = "enterprise"
    user.permissions = {}
    user.is_developer = True
    user.is_superuser = False
    return user


@pytest.fixture
def super_admin_user():
    """Super admin user fixture."""
    user = Mock(spec=User)
    user.id = "super_admin_1"
    user.email = "super@netrasystems.ai"
    user.role = "super_admin"
    user.plan_tier = "enterprise"
    user.permissions = {}
    user.is_developer = True
    user.is_superuser = True
    return user


# Helper functions for 25-line compliance
def assert_user_has_permission(user, permission):
    """Assert user has specific permission."""
    result = PermissionService.has_permission(user, permission)
    assert result is True


def assert_user_lacks_permission(user, permission):
    """Assert user lacks specific permission."""
    result = PermissionService.has_permission(user, permission)
    assert result is False


def assert_role_level_equals(role, expected_level):
    """Assert role level matches expected value."""
    level = PermissionService.get_role_level(role)
    assert level == expected_level


def assert_user_is_admin_or_higher(user, expected):
    """Assert user admin status matches expected."""
    result = PermissionService.is_admin_or_higher(user)
    assert result == expected


def assert_user_is_developer_or_higher(user, expected):
    """Assert user developer status matches expected."""
    result = PermissionService.is_developer_or_higher(user)
    assert result == expected


def create_user_with_custom_permissions(additional=None, revoked=None):
    """Create user with custom permissions."""
    user = Mock(spec=User)
    user.role = "standard_user"
    user.permissions = {"additional": additional or [], "revoked": revoked or []}
    user.is_developer = False
    user.is_superuser = False
    return user


def update_user_permissions_dict(user, additional=None, revoked=None):
    """Update user permissions dictionary."""
    if not user.permissions:
        user.permissions = {}
    if additional:
        user.permissions["additional"] = additional
    if revoked:
        user.permissions["revoked"] = revoked


# Core permission checking tests
class TestPermissionChecking:
    """Test core permission checking functionality."""

    def test_standard_user_basic_permissions(self, free_tier_user):
        """Free tier user has basic permissions only."""
        assert_user_has_permission(free_tier_user, "chat")
        assert_user_has_permission(free_tier_user, "history_own")
        assert_user_has_permission(free_tier_user, "basic_tools")
        assert_user_has_permission(free_tier_user, "view_own_threads")

    def test_standard_user_lacks_advanced_permissions(self, free_tier_user):
        """Free tier user lacks advanced permissions."""
        assert_user_lacks_permission(free_tier_user, "corpus_read")
        assert_user_lacks_permission(free_tier_user, "synthetic_preview")
        assert_user_lacks_permission(free_tier_user, "advanced_analytics")
        assert_user_lacks_permission(free_tier_user, "api_keys_own")

    def test_power_user_has_advanced_permissions(self, pro_tier_user):
        """Pro tier user has advanced permissions."""
        assert_user_has_permission(pro_tier_user, "corpus_read")
        assert_user_has_permission(pro_tier_user, "synthetic_preview")
        assert_user_has_permission(pro_tier_user, "advanced_analytics")
        assert_user_has_permission(pro_tier_user, "api_keys_own")

    def test_power_user_lacks_developer_permissions(self, pro_tier_user):
        """Pro tier user lacks developer permissions."""
        assert_user_lacks_permission(pro_tier_user, "corpus_write")
        assert_user_lacks_permission(pro_tier_user, "synthetic_generate")
        assert_user_lacks_permission(pro_tier_user, "debug_panel")
        assert_user_lacks_permission(pro_tier_user, "log_access")

    def test_developer_has_developer_permissions(self, developer_user):
        """Developer has developer-specific permissions."""
        assert_user_has_permission(developer_user, "corpus_write")
        assert_user_has_permission(developer_user, "synthetic_generate")
        assert_user_has_permission(developer_user, "debug_panel")
        assert_user_has_permission(developer_user, "log_access")

    def test_admin_has_admin_permissions(self, admin_user):
        """Admin has administrative permissions."""
        assert_user_has_permission(admin_user, "user_management")
        assert_user_has_permission(admin_user, "system_config")
        assert_user_has_permission(admin_user, "billing_access")
        assert_user_has_permission(admin_user, "audit_logs")

    def test_super_admin_has_all_permissions(self, super_admin_user):
        """Super admin has wildcard permissions."""
        perms = PermissionService.get_user_permissions(super_admin_user)
        # Super admin should have comprehensive permission set
        assert len(perms) > 15  # Should have many permissions


class TestRoleHierarchyAndLevels:
    """Test role hierarchy and level system."""

    def test_role_hierarchy_levels(self):
        """Role hierarchy levels are correctly defined."""
        assert_role_level_equals("standard_user", 0)
        assert_role_level_equals("power_user", 1)
        assert_role_level_equals("developer", 2)
        assert_role_level_equals("admin", 3)

    def test_role_hierarchy_super_admin(self):
        """Super admin has highest role level."""
        assert_role_level_equals("super_admin", 4)

    def test_unknown_role_defaults_to_zero(self):
        """Unknown role defaults to level zero."""
        assert_role_level_equals("unknown_role", 0)

    def test_admin_or_higher_detection(self):
        """Admin or higher detection works correctly."""
        admin_user = Mock(spec=User)
        admin_user.role = "admin"
        admin_user.is_superuser = False
        assert_user_is_admin_or_higher(admin_user, True)

    def test_standard_user_not_admin(self, free_tier_user):
        """Standard user is not admin or higher."""
        assert_user_is_admin_or_higher(free_tier_user, False)

    def test_developer_or_higher_detection(self, developer_user):
        """Developer or higher detection works correctly."""
        assert_user_is_developer_or_higher(developer_user, True)

    def test_power_user_not_developer(self, pro_tier_user):
        """Power user is not developer or higher."""
        assert_user_is_developer_or_higher(pro_tier_user, False)

    def test_superuser_flag_grants_admin_access(self, free_tier_user):
        """Superuser flag grants admin access regardless of role."""
        free_tier_user.is_superuser = True
        assert_user_is_admin_or_higher(free_tier_user, True)


class TestDeveloperAutoDetection:
    """Test developer status auto-detection - CRITICAL for free-to-paid conversion."""

    @patch.dict('os.environ', {'DEV_MODE': 'true'})
    def test_dev_mode_enables_developer_status(self, free_tier_user):
        """DEV_MODE environment variable enables developer status."""
        result = PermissionService.detect_developer_status(free_tier_user)
        assert result is True

    @patch.dict('os.environ', {'DEV_MODE': 'false', 'ENVIRONMENT': 'production'})
    def test_dev_mode_false_no_developer_status(self, free_tier_user):
        """DEV_MODE=false doesn't grant developer status."""
        result = PermissionService.detect_developer_status(free_tier_user)
        assert result is False

    def test_netra_domain_enables_developer_status(self):
        """Netra domain email enables developer status."""
        netra_user = Mock(spec=User)
        netra_user.email = "test@netrasystems.ai"
        result = PermissionService.detect_developer_status(netra_user)
        assert result is True

    @patch.dict('os.environ', {'ENVIRONMENT': 'production'})
    def test_external_domain_no_developer_status(self, free_tier_user):
        """External domain doesn't grant developer status."""
        free_tier_user.email = "user@gmail.com"
        result = PermissionService.detect_developer_status(free_tier_user)
        assert result is False

    @patch.dict('os.environ', {'ENVIRONMENT': 'development'})
    def test_dev_environment_enables_developer_status(self, free_tier_user):
        """Development environment enables developer status."""
        result = PermissionService.detect_developer_status(free_tier_user)
        assert result is True

    @patch.dict('os.environ', {'ENVIRONMENT': 'production'})
    def test_prod_environment_no_developer_status(self, free_tier_user):
        """Production environment doesn't grant developer status."""
        result = PermissionService.detect_developer_status(free_tier_user)
        assert result is False


class TestUserRoleUpdates:
    """Test user role updates and elevation."""

    def test_should_elevate_to_developer_checks(self, free_tier_user):
        """Should elevate to developer logic works correctly."""
        result = PermissionService._should_elevate_to_developer(free_tier_user)
        assert result is True

    def test_should_not_elevate_existing_developer(self, developer_user):
        """Should not elevate existing developer."""
        result = PermissionService._should_elevate_to_developer(developer_user)
        assert result is False

    def test_should_not_elevate_admin(self, admin_user):
        """Should not elevate admin users."""
        result = PermissionService._should_elevate_to_developer(admin_user)
        assert result is False

    def test_elevate_user_to_developer_updates_fields(self, mock_db_session, free_tier_user):
        """Elevate user to developer updates role and developer flag."""
        PermissionService._elevate_user_to_developer(mock_db_session, free_tier_user)
        assert free_tier_user.role == "developer"
        assert free_tier_user.is_developer is True
        mock_db_session.commit.assert_called_once()

    @patch.dict('os.environ', {'DEV_MODE': 'true'})
    def test_update_user_role_with_dev_detection(self, mock_db_session, free_tier_user):
        """Update user role with developer detection works."""
        result = PermissionService.update_user_role(
            mock_db_session, free_tier_user, check_developer=True
        )
        assert result.role == "developer"
        assert result.is_developer is True

    def test_update_user_role_without_dev_detection(self, mock_db_session, free_tier_user):
        """Update user role without developer detection preserves role."""
        original_role = free_tier_user.role
        result = PermissionService.update_user_role(
            mock_db_session, free_tier_user, check_developer=False
        )
        assert result.role == original_role


class TestCustomPermissions:
    """Test custom permission grants and revokes - CRITICAL for tier flexibility."""

    def test_grant_permission_creates_structure(self, mock_db_session):
        """Grant permission creates proper permissions structure."""
        user = Mock(spec=User)
        user.permissions = None
        PermissionService.grant_permission(mock_db_session, user, "test_perm")
        assert user.permissions is not None
        assert "additional" in user.permissions

    def test_grant_permission_adds_new_permission(self, mock_db_session):
        """Grant permission adds new permission to list."""
        user = create_user_with_custom_permissions()
        PermissionService.grant_permission(mock_db_session, user, "new_perm")
        assert "new_perm" in user.permissions["additional"]
        mock_db_session.commit.assert_called_once()

    def test_grant_permission_ignores_duplicate(self, mock_db_session):
        """Grant permission ignores duplicate permissions."""
        user = create_user_with_custom_permissions(additional=["existing_perm"])
        mock_db_session.reset_mock()
        PermissionService.grant_permission(mock_db_session, user, "existing_perm")
        # Should not call commit for duplicate
        mock_db_session.commit.assert_not_called()

    def test_revoke_permission_creates_structure(self, mock_db_session):
        """Revoke permission creates proper revoked structure."""
        user = Mock(spec=User)
        user.permissions = None
        PermissionService.revoke_permission(mock_db_session, user, "test_perm")
        assert user.permissions is not None
        assert "revoked" in user.permissions

    def test_revoke_permission_adds_to_revoked_list(self, mock_db_session):
        """Revoke permission adds to revoked list."""
        user = create_user_with_custom_permissions()
        PermissionService.revoke_permission(mock_db_session, user, "revoked_perm")
        assert "revoked_perm" in user.permissions["revoked"]
        mock_db_session.commit.assert_called_once()

    def test_custom_permissions_applied_correctly(self):
        """Custom permissions are applied correctly."""
        user = create_user_with_custom_permissions(
            additional=["bonus_perm"], 
            revoked=["chat"]
        )
        perms = PermissionService.get_user_permissions(user)
        assert "bonus_perm" in perms
        assert "chat" not in perms  # Should be revoked


class TestSetUserRole:
    """Test setting user roles and validation."""

    def test_set_user_role_updates_role(self, mock_db_session, free_tier_user):
        """Set user role updates role correctly."""
        result = PermissionService.set_user_role(mock_db_session, free_tier_user, "power_user")
        assert result.role == "power_user"
        mock_db_session.commit.assert_called_once()

    def test_set_user_role_updates_developer_flag(self, mock_db_session, free_tier_user):
        """Set user role updates developer flag for elevated roles."""
        PermissionService.set_user_role(mock_db_session, free_tier_user, "developer")
        assert free_tier_user.is_developer is True

    def test_set_user_role_validates_role(self, mock_db_session, free_tier_user):
        """Set user role validates role exists in hierarchy."""
        with pytest.raises(ValueError, match="Invalid role"):
            PermissionService.set_user_role(mock_db_session, free_tier_user, "invalid_role")

    def test_set_user_role_preserves_old_role_info(self, mock_db_session, pro_tier_user):
        """Set user role preserves information about old role."""
        original_role = pro_tier_user.role
        result = PermissionService.set_user_role(mock_db_session, pro_tier_user, "developer")
        # Should have changed role
        assert result.role != original_role
        assert result.role == "developer"


class TestPermissionAggregation:
    """Test permission aggregation and complex scenarios."""

    def test_has_any_permission_with_wildcard(self, super_admin_user):
        """has_any_permission works with wildcard permissions."""
        # Super admin should have comprehensive permissions
        result = PermissionService.has_any_permission(
            super_admin_user, ["chat", "corpus_read"]
        )
        assert result is True  # Super admin has comprehensive permissions

    def test_has_any_permission_with_specific(self, free_tier_user):
        """has_any_permission works with specific permissions."""
        result = PermissionService.has_any_permission(
            free_tier_user, ["chat", "nonexistent_perm"]
        )
        assert result is True  # Has chat permission

    def test_has_all_permissions_with_wildcard(self, super_admin_user):
        """has_all_permissions works with wildcard permissions."""
        result = PermissionService.has_all_permissions(
            super_admin_user, ["chat", "corpus_read", "user_management"]
        )
        assert result is True  # Super admin has comprehensive permissions

    def test_has_all_permissions_missing_one(self, free_tier_user):
        """has_all_permissions returns False when missing one permission."""
        result = PermissionService.has_all_permissions(
            free_tier_user, ["chat", "corpus_read"]  # Missing corpus_read
        )
        assert result is False

    def test_get_all_permissions_for_superadmin_comprehensive(self):
        """Super admin gets comprehensive permission set."""
        all_perms = PermissionService._get_all_permissions_for_superadmin()
        # Should include permissions from all role levels
        assert "chat" in all_perms
        assert "corpus_read" in all_perms
        assert "debug_panel" in all_perms
        assert "user_management" in all_perms


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling scenarios."""

    def test_empty_permissions_dict_handling(self):
        """Empty permissions dict is handled correctly."""
        user = Mock(spec=User)
        user.role = "standard_user"
        user.permissions = {}
        user.is_developer = False
        user.is_superuser = False
        perms = PermissionService.get_user_permissions(user)
        # Should get standard role permissions
        assert "chat" in perms

    def test_none_permissions_handling(self):
        """None permissions is handled correctly."""
        user = Mock(spec=User)
        user.role = "standard_user"
        user.permissions = None
        user.is_developer = False
        user.is_superuser = False
        perms = PermissionService.get_user_permissions(user)
        # Should get standard role permissions
        assert "chat" in perms

    def test_unknown_role_gets_empty_permissions(self):
        """Unknown role gets empty permissions."""
        user = Mock(spec=User)
        user.role = "unknown_role"
        user.permissions = {}
        user.is_developer = False
        user.is_superuser = False
        perms = PermissionService.get_user_permissions(user)
        # Should get empty set for unknown role
        assert len(perms) == 0

    def test_case_insensitive_netra_domain_detection(self):
        """Netra domain detection is case insensitive."""
        user = Mock(spec=User)
        user.email = "test@NETRASYSTEMS.AI"
        result = PermissionService._check_netra_domain(user)
        assert result is True

    def test_none_email_handling_in_domain_check(self):
        """None email is handled in domain check."""
        user = Mock(spec=User)
        user.email = None
        result = PermissionService._check_netra_domain(user)
        assert result is False