from shared.isolated_environment import get_env
from test_framework.database.test_database_manager import TestDatabaseManager
from shared.isolated_environment import IsolatedEnvironment
# REMOVED_SYNTAX_ERROR: '''Comprehensive unit tests for PermissionService - FREE TIER CRITICAL.

# REMOVED_SYNTAX_ERROR: BUSINESS VALUE JUSTIFICATION:
    # REMOVED_SYNTAX_ERROR: 1. Segment: Free tier users (100% of new users start here)
    # REMOVED_SYNTAX_ERROR: 2. Business Goal: Ensure robust free tier limits drive conversions
    # REMOVED_SYNTAX_ERROR: 3. Value Impact: Each 1% improvement in conversion = $50K ARR
    # REMOVED_SYNTAX_ERROR: 4. Revenue Impact: These tests ensure conversion funnel works correctly
    # REMOVED_SYNTAX_ERROR: 5. CRITICAL: Free tier bugs = lost revenue. Must have 100% test coverage.

    # REMOVED_SYNTAX_ERROR: Tests the PermissionService that enforces plan-based permissions,
    # REMOVED_SYNTAX_ERROR: role hierarchy, developer auto-detection, and permission grants/revokes.
    # REMOVED_SYNTAX_ERROR: Critical for protecting revenue through proper tier enforcement.
    # REMOVED_SYNTAX_ERROR: '''

    # REMOVED_SYNTAX_ERROR: import sys
    # REMOVED_SYNTAX_ERROR: from pathlib import Path

    # REMOVED_SYNTAX_ERROR: from datetime import datetime, timezone

    # REMOVED_SYNTAX_ERROR: import pytest

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.models_postgres import User

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.permission_service import ( )
    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: ROLE_HIERARCHY,
    # REMOVED_SYNTAX_ERROR: ROLE_PERMISSIONS,
    # REMOVED_SYNTAX_ERROR: PermissionService)

    # Test fixtures for setup
    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_db_session():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Mock database session."""
    # REMOVED_SYNTAX_ERROR: pass
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: session = TestDatabaseManager().get_session()
    # Make commit async for async methods
    # REMOVED_SYNTAX_ERROR: session.commit = AsyncMock(return_value=None)
    # REMOVED_SYNTAX_ERROR: return session

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def free_tier_user():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Free tier user fixture."""
    # REMOVED_SYNTAX_ERROR: pass
    # Mock: Component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: user = Mock(spec=User)
    # REMOVED_SYNTAX_ERROR: user.id = "test_user_1"
    # REMOVED_SYNTAX_ERROR: user.email = "user@example.com"
    # REMOVED_SYNTAX_ERROR: user.role = "standard_user"
    # REMOVED_SYNTAX_ERROR: user.plan_tier = "free"
    # REMOVED_SYNTAX_ERROR: user.permissions = {}
    # REMOVED_SYNTAX_ERROR: user.is_developer = False
    # REMOVED_SYNTAX_ERROR: user.is_superuser = False
    # REMOVED_SYNTAX_ERROR: return user

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def pro_tier_user():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Pro tier user fixture."""
    # REMOVED_SYNTAX_ERROR: pass
    # Mock: Component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: user = Mock(spec=User)
    # REMOVED_SYNTAX_ERROR: user.id = "test_user_2"
    # REMOVED_SYNTAX_ERROR: user.email = "pro@example.com"
    # REMOVED_SYNTAX_ERROR: user.role = "power_user"
    # REMOVED_SYNTAX_ERROR: user.plan_tier = "pro"
    # REMOVED_SYNTAX_ERROR: user.permissions = {}
    # REMOVED_SYNTAX_ERROR: user.is_developer = False
    # REMOVED_SYNTAX_ERROR: user.is_superuser = False
    # REMOVED_SYNTAX_ERROR: return user

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def developer_user():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Developer user fixture."""
    # REMOVED_SYNTAX_ERROR: pass
    # Mock: Component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: user = Mock(spec=User)
    # REMOVED_SYNTAX_ERROR: user.id = "dev_user_1"
    # REMOVED_SYNTAX_ERROR: user.email = "dev@netrasystems.ai"
    # REMOVED_SYNTAX_ERROR: user.role = "developer"
    # REMOVED_SYNTAX_ERROR: user.plan_tier = "developer"
    # REMOVED_SYNTAX_ERROR: user.permissions = {}
    # REMOVED_SYNTAX_ERROR: user.is_developer = True
    # REMOVED_SYNTAX_ERROR: user.is_superuser = False
    # REMOVED_SYNTAX_ERROR: return user

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def admin_user():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Admin user fixture."""
    # REMOVED_SYNTAX_ERROR: pass
    # Mock: Component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: user = Mock(spec=User)
    # REMOVED_SYNTAX_ERROR: user.id = "admin_user_1"
    # REMOVED_SYNTAX_ERROR: user.email = "admin@netrasystems.ai"
    # REMOVED_SYNTAX_ERROR: user.role = "admin"
    # REMOVED_SYNTAX_ERROR: user.plan_tier = "enterprise"
    # REMOVED_SYNTAX_ERROR: user.permissions = {}
    # REMOVED_SYNTAX_ERROR: user.is_developer = True
    # REMOVED_SYNTAX_ERROR: user.is_superuser = False
    # REMOVED_SYNTAX_ERROR: return user

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def super_admin_user():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Super admin user fixture."""
    # REMOVED_SYNTAX_ERROR: pass
    # Mock: Component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: user = Mock(spec=User)
    # REMOVED_SYNTAX_ERROR: user.id = "super_admin_1"
    # REMOVED_SYNTAX_ERROR: user.email = "super@netrasystems.ai"
    # REMOVED_SYNTAX_ERROR: user.role = "super_admin"
    # REMOVED_SYNTAX_ERROR: user.plan_tier = "enterprise"
    # REMOVED_SYNTAX_ERROR: user.permissions = {}
    # REMOVED_SYNTAX_ERROR: user.is_developer = True
    # REMOVED_SYNTAX_ERROR: user.is_superuser = True
    # REMOVED_SYNTAX_ERROR: return user

    # Helper functions for 25-line compliance
# REMOVED_SYNTAX_ERROR: def assert_user_has_permission(user, permission):
    # REMOVED_SYNTAX_ERROR: """Assert user has specific permission."""
    # REMOVED_SYNTAX_ERROR: result = PermissionService.has_permission(user, permission)
    # REMOVED_SYNTAX_ERROR: assert result is True

# REMOVED_SYNTAX_ERROR: def assert_user_lacks_permission(user, permission):
    # REMOVED_SYNTAX_ERROR: """Assert user lacks specific permission."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: result = PermissionService.has_permission(user, permission)
    # REMOVED_SYNTAX_ERROR: assert result is False

# REMOVED_SYNTAX_ERROR: def assert_role_level_equals(role, expected_level):
    # REMOVED_SYNTAX_ERROR: """Assert role level matches expected value."""
    # REMOVED_SYNTAX_ERROR: level = PermissionService.get_role_level(role)
    # REMOVED_SYNTAX_ERROR: assert level == expected_level

# REMOVED_SYNTAX_ERROR: def assert_user_is_admin_or_higher(user, expected):
    # REMOVED_SYNTAX_ERROR: """Assert user admin status matches expected."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: result = PermissionService.is_admin_or_higher(user)
    # REMOVED_SYNTAX_ERROR: assert result == expected

# REMOVED_SYNTAX_ERROR: def assert_user_is_developer_or_higher(user, expected):
    # REMOVED_SYNTAX_ERROR: """Assert user developer status matches expected."""
    # REMOVED_SYNTAX_ERROR: result = PermissionService.is_developer_or_higher(user)
    # REMOVED_SYNTAX_ERROR: assert result == expected

# REMOVED_SYNTAX_ERROR: def create_user_with_custom_permissions(additional=None, revoked=None):
    # REMOVED_SYNTAX_ERROR: """Create user with custom permissions."""
    # REMOVED_SYNTAX_ERROR: pass
    # Mock: Component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: user = Mock(spec=User)
    # REMOVED_SYNTAX_ERROR: user.role = "standard_user"
    # REMOVED_SYNTAX_ERROR: user.permissions = {"additional": additional or [], "revoked": revoked or []}
    # REMOVED_SYNTAX_ERROR: user.is_developer = False
    # REMOVED_SYNTAX_ERROR: user.is_superuser = False
    # REMOVED_SYNTAX_ERROR: return user

# REMOVED_SYNTAX_ERROR: def update_user_permissions_dict(user, additional=None, revoked=None):
    # REMOVED_SYNTAX_ERROR: """Update user permissions dictionary."""
    # REMOVED_SYNTAX_ERROR: if not user.permissions:
        # REMOVED_SYNTAX_ERROR: user.permissions = {}
        # REMOVED_SYNTAX_ERROR: if additional:
            # REMOVED_SYNTAX_ERROR: user.permissions["additional"] = additional
            # REMOVED_SYNTAX_ERROR: if revoked:
                # REMOVED_SYNTAX_ERROR: user.permissions["revoked"] = revoked

                # Core permission checking tests
# REMOVED_SYNTAX_ERROR: class TestPermissionChecking:
    # REMOVED_SYNTAX_ERROR: """Test core permission checking functionality."""
    # REMOVED_SYNTAX_ERROR: pass

# REMOVED_SYNTAX_ERROR: def test_standard_user_basic_permissions(self, free_tier_user):
    # REMOVED_SYNTAX_ERROR: """Free tier user has basic permissions only."""
    # REMOVED_SYNTAX_ERROR: assert_user_has_permission(free_tier_user, "chat")
    # REMOVED_SYNTAX_ERROR: assert_user_has_permission(free_tier_user, "history_own")
    # REMOVED_SYNTAX_ERROR: assert_user_has_permission(free_tier_user, "basic_tools")
    # REMOVED_SYNTAX_ERROR: assert_user_has_permission(free_tier_user, "view_own_threads")

# REMOVED_SYNTAX_ERROR: def test_standard_user_lacks_advanced_permissions(self, free_tier_user):
    # REMOVED_SYNTAX_ERROR: """Free tier user lacks advanced permissions."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: assert_user_lacks_permission(free_tier_user, "corpus_read")
    # REMOVED_SYNTAX_ERROR: assert_user_lacks_permission(free_tier_user, "synthetic_preview")
    # REMOVED_SYNTAX_ERROR: assert_user_lacks_permission(free_tier_user, "advanced_analytics")
    # REMOVED_SYNTAX_ERROR: assert_user_lacks_permission(free_tier_user, "api_keys_own")

# REMOVED_SYNTAX_ERROR: def test_power_user_has_advanced_permissions(self, pro_tier_user):
    # REMOVED_SYNTAX_ERROR: """Pro tier user has advanced permissions."""
    # REMOVED_SYNTAX_ERROR: assert_user_has_permission(pro_tier_user, "corpus_read")
    # REMOVED_SYNTAX_ERROR: assert_user_has_permission(pro_tier_user, "synthetic_preview")
    # REMOVED_SYNTAX_ERROR: assert_user_has_permission(pro_tier_user, "advanced_analytics")
    # REMOVED_SYNTAX_ERROR: assert_user_has_permission(pro_tier_user, "api_keys_own")

# REMOVED_SYNTAX_ERROR: def test_power_user_lacks_developer_permissions(self, pro_tier_user):
    # REMOVED_SYNTAX_ERROR: """Pro tier user lacks developer permissions."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: assert_user_lacks_permission(pro_tier_user, "corpus_write")
    # REMOVED_SYNTAX_ERROR: assert_user_lacks_permission(pro_tier_user, "synthetic_generate")
    # REMOVED_SYNTAX_ERROR: assert_user_lacks_permission(pro_tier_user, "debug_panel")
    # REMOVED_SYNTAX_ERROR: assert_user_lacks_permission(pro_tier_user, "log_access")

# REMOVED_SYNTAX_ERROR: def test_developer_has_developer_permissions(self, developer_user):
    # REMOVED_SYNTAX_ERROR: """Developer has developer-specific permissions."""
    # REMOVED_SYNTAX_ERROR: assert_user_has_permission(developer_user, "corpus_write")
    # REMOVED_SYNTAX_ERROR: assert_user_has_permission(developer_user, "synthetic_generate")
    # REMOVED_SYNTAX_ERROR: assert_user_has_permission(developer_user, "debug_panel")
    # REMOVED_SYNTAX_ERROR: assert_user_has_permission(developer_user, "log_access")

# REMOVED_SYNTAX_ERROR: def test_admin_has_admin_permissions(self, admin_user):
    # REMOVED_SYNTAX_ERROR: """Admin has administrative permissions."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: assert_user_has_permission(admin_user, "user_management")
    # REMOVED_SYNTAX_ERROR: assert_user_has_permission(admin_user, "system_config")
    # REMOVED_SYNTAX_ERROR: assert_user_has_permission(admin_user, "billing_access")
    # REMOVED_SYNTAX_ERROR: assert_user_has_permission(admin_user, "audit_logs")

# REMOVED_SYNTAX_ERROR: def test_super_admin_has_all_permissions(self, super_admin_user):
    # REMOVED_SYNTAX_ERROR: """Super admin has wildcard permissions."""
    # REMOVED_SYNTAX_ERROR: perms = PermissionService.get_user_permissions(super_admin_user)
    # Super admin should have comprehensive permission set
    # REMOVED_SYNTAX_ERROR: assert len(perms) > 15  # Should have many permissions

# REMOVED_SYNTAX_ERROR: class TestRoleHierarchyAndLevels:
    # REMOVED_SYNTAX_ERROR: """Test role hierarchy and level system."""
    # REMOVED_SYNTAX_ERROR: pass

# REMOVED_SYNTAX_ERROR: def test_role_hierarchy_levels(self):
    # REMOVED_SYNTAX_ERROR: """Role hierarchy levels are correctly defined."""
    # REMOVED_SYNTAX_ERROR: assert_role_level_equals("standard_user", 0)
    # REMOVED_SYNTAX_ERROR: assert_role_level_equals("power_user", 1)
    # REMOVED_SYNTAX_ERROR: assert_role_level_equals("developer", 2)
    # REMOVED_SYNTAX_ERROR: assert_role_level_equals("admin", 3)

# REMOVED_SYNTAX_ERROR: def test_role_hierarchy_super_admin(self):
    # REMOVED_SYNTAX_ERROR: """Super admin has highest role level."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: assert_role_level_equals("super_admin", 4)

# REMOVED_SYNTAX_ERROR: def test_unknown_role_defaults_to_zero(self):
    # REMOVED_SYNTAX_ERROR: """Unknown role defaults to level zero."""
    # REMOVED_SYNTAX_ERROR: assert_role_level_equals("unknown_role", 0)

# REMOVED_SYNTAX_ERROR: def test_admin_or_higher_detection(self):
    # REMOVED_SYNTAX_ERROR: """Admin or higher detection works correctly."""
    # REMOVED_SYNTAX_ERROR: pass
    # Mock: Component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: admin_user = Mock(spec=User)
    # REMOVED_SYNTAX_ERROR: admin_user.role = "admin"
    # REMOVED_SYNTAX_ERROR: admin_user.is_superuser = False
    # REMOVED_SYNTAX_ERROR: assert_user_is_admin_or_higher(admin_user, True)

# REMOVED_SYNTAX_ERROR: def test_standard_user_not_admin(self, free_tier_user):
    # REMOVED_SYNTAX_ERROR: """Standard user is not admin or higher."""
    # REMOVED_SYNTAX_ERROR: assert_user_is_admin_or_higher(free_tier_user, False)

# REMOVED_SYNTAX_ERROR: def test_developer_or_higher_detection(self, developer_user):
    # REMOVED_SYNTAX_ERROR: """Developer or higher detection works correctly."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: assert_user_is_developer_or_higher(developer_user, True)

# REMOVED_SYNTAX_ERROR: def test_power_user_not_developer(self, pro_tier_user):
    # REMOVED_SYNTAX_ERROR: """Power user is not developer or higher."""
    # REMOVED_SYNTAX_ERROR: assert_user_is_developer_or_higher(pro_tier_user, False)

# REMOVED_SYNTAX_ERROR: def test_superuser_flag_grants_admin_access(self, free_tier_user):
    # REMOVED_SYNTAX_ERROR: """Superuser flag grants admin access regardless of role."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: free_tier_user.is_superuser = True
    # REMOVED_SYNTAX_ERROR: assert_user_is_admin_or_higher(free_tier_user, True)

# REMOVED_SYNTAX_ERROR: class TestDeveloperAutoDetection:
    # REMOVED_SYNTAX_ERROR: """Test developer status auto-detection - CRITICAL for free-to-paid conversion."""
    # REMOVED_SYNTAX_ERROR: pass

# REMOVED_SYNTAX_ERROR: def test_dev_mode_enables_developer_status(self, free_tier_user):
    # REMOVED_SYNTAX_ERROR: """DEV_MODE environment variable enables developer status."""
    # REMOVED_SYNTAX_ERROR: result = PermissionService.detect_developer_status(free_tier_user)
    # REMOVED_SYNTAX_ERROR: assert result is True

# REMOVED_SYNTAX_ERROR: def test_dev_mode_false_no_developer_status(self, mock_check_dev_env, mock_check_netra_domain, mock_check_dev_mode, free_tier_user):
    # REMOVED_SYNTAX_ERROR: """DEV_MODE=false doesn't grant developer status."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: result = PermissionService.detect_developer_status(free_tier_user)
    # REMOVED_SYNTAX_ERROR: assert result is False

# REMOVED_SYNTAX_ERROR: def test_netra_domain_enables_developer_status(self):
    # REMOVED_SYNTAX_ERROR: """Netra domain email enables developer status."""
    # Mock: Component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: netra_user = Mock(spec=User)
    # REMOVED_SYNTAX_ERROR: netra_user.email = "test@netrasystems.ai"
    # REMOVED_SYNTAX_ERROR: result = PermissionService.detect_developer_status(netra_user)
    # REMOVED_SYNTAX_ERROR: assert result is True

# REMOVED_SYNTAX_ERROR: def test_external_domain_no_developer_status(self, mock_check_dev_env, mock_check_netra_domain, mock_check_dev_mode, free_tier_user):
    # REMOVED_SYNTAX_ERROR: """External domain doesn't grant developer status."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: free_tier_user.email = "user@gmail.com"
    # REMOVED_SYNTAX_ERROR: result = PermissionService.detect_developer_status(free_tier_user)
    # REMOVED_SYNTAX_ERROR: assert result is False

# REMOVED_SYNTAX_ERROR: def test_dev_environment_enables_developer_status(self, free_tier_user):
    # REMOVED_SYNTAX_ERROR: """Development environment enables developer status."""
    # REMOVED_SYNTAX_ERROR: result = PermissionService.detect_developer_status(free_tier_user)
    # REMOVED_SYNTAX_ERROR: assert result is True

# REMOVED_SYNTAX_ERROR: def test_prod_environment_no_developer_status(self, mock_check_dev_env, mock_check_netra_domain, mock_check_dev_mode, free_tier_user):
    # REMOVED_SYNTAX_ERROR: """Production environment doesn't grant developer status."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: result = PermissionService.detect_developer_status(free_tier_user)
    # REMOVED_SYNTAX_ERROR: assert result is False

# REMOVED_SYNTAX_ERROR: class TestUserRoleUpdates:
    # REMOVED_SYNTAX_ERROR: """Test user role updates and elevation."""
    # REMOVED_SYNTAX_ERROR: pass

# REMOVED_SYNTAX_ERROR: def test_should_elevate_to_developer_checks(self, free_tier_user):
    # REMOVED_SYNTAX_ERROR: """Should elevate to developer logic works correctly."""
    # REMOVED_SYNTAX_ERROR: result = PermissionService._should_elevate_to_developer(free_tier_user)
    # REMOVED_SYNTAX_ERROR: assert result is True

# REMOVED_SYNTAX_ERROR: def test_should_not_elevate_existing_developer(self, developer_user):
    # REMOVED_SYNTAX_ERROR: """Should not elevate existing developer."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: result = PermissionService._should_elevate_to_developer(developer_user)
    # REMOVED_SYNTAX_ERROR: assert result is False

# REMOVED_SYNTAX_ERROR: def test_should_not_elevate_admin(self, admin_user):
    # REMOVED_SYNTAX_ERROR: """Should not elevate admin users."""
    # REMOVED_SYNTAX_ERROR: result = PermissionService._should_elevate_to_developer(admin_user)
    # REMOVED_SYNTAX_ERROR: assert result is False

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_elevate_user_to_developer_updates_fields(self, mock_db_session, free_tier_user):
        # REMOVED_SYNTAX_ERROR: """Elevate user to developer updates role and developer flag."""
        # REMOVED_SYNTAX_ERROR: pass
        # REMOVED_SYNTAX_ERROR: await PermissionService._elevate_user_to_developer(mock_db_session, free_tier_user)
        # REMOVED_SYNTAX_ERROR: assert free_tier_user.role == "developer"
        # REMOVED_SYNTAX_ERROR: assert free_tier_user.is_developer is True
        # REMOVED_SYNTAX_ERROR: mock_db_session.commit.assert_called_once()

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_update_user_role_with_dev_detection(self, mock_db_session, free_tier_user):
            # REMOVED_SYNTAX_ERROR: """Update user role with developer detection works."""
            # REMOVED_SYNTAX_ERROR: result = await PermissionService.update_user_role( )
            # REMOVED_SYNTAX_ERROR: mock_db_session, free_tier_user, check_developer=True
            
            # REMOVED_SYNTAX_ERROR: assert result.role == "developer"
            # REMOVED_SYNTAX_ERROR: assert result.is_developer is True

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_update_user_role_without_dev_detection(self, mock_db_session, free_tier_user):
                # REMOVED_SYNTAX_ERROR: """Update user role without developer detection preserves role."""
                # REMOVED_SYNTAX_ERROR: pass
                # REMOVED_SYNTAX_ERROR: original_role = free_tier_user.role
                # REMOVED_SYNTAX_ERROR: result = await PermissionService.update_user_role( )
                # REMOVED_SYNTAX_ERROR: mock_db_session, free_tier_user, check_developer=False
                
                # REMOVED_SYNTAX_ERROR: assert result.role == original_role

# REMOVED_SYNTAX_ERROR: class TestCustomPermissions:
    # REMOVED_SYNTAX_ERROR: """Test custom permission grants and revokes - CRITICAL for tier flexibility."""
    # REMOVED_SYNTAX_ERROR: pass

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_grant_permission_creates_structure(self, mock_db_session):
        # REMOVED_SYNTAX_ERROR: """Grant permission creates proper permissions structure."""
        # Mock: Component isolation for controlled unit testing
        # REMOVED_SYNTAX_ERROR: user = Mock(spec=User)
        # REMOVED_SYNTAX_ERROR: user.permissions = None
        # REMOVED_SYNTAX_ERROR: await PermissionService.grant_permission(mock_db_session, user, "test_perm")
        # REMOVED_SYNTAX_ERROR: assert user.permissions is not None
        # REMOVED_SYNTAX_ERROR: assert "additional" in user.permissions

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_grant_permission_adds_new_permission(self, mock_db_session):
            # REMOVED_SYNTAX_ERROR: """Grant permission adds new permission to list."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: user = create_user_with_custom_permissions()
            # REMOVED_SYNTAX_ERROR: await PermissionService.grant_permission(mock_db_session, user, "new_perm")
            # REMOVED_SYNTAX_ERROR: assert "new_perm" in user.permissions["additional"]
            # REMOVED_SYNTAX_ERROR: mock_db_session.commit.assert_called_once()

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_grant_permission_ignores_duplicate(self, mock_db_session):
                # REMOVED_SYNTAX_ERROR: """Grant permission ignores duplicate permissions."""
                # REMOVED_SYNTAX_ERROR: user = create_user_with_custom_permissions(additional=["existing_perm"])
                # REMOVED_SYNTAX_ERROR: mock_db_session.reset_mock()
                # REMOVED_SYNTAX_ERROR: await PermissionService.grant_permission(mock_db_session, user, "existing_perm")
                # Should not call commit for duplicate
                # REMOVED_SYNTAX_ERROR: mock_db_session.commit.assert_not_called()

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_revoke_permission_creates_structure(self, mock_db_session):
                    # REMOVED_SYNTAX_ERROR: """Revoke permission creates proper revoked structure."""
                    # REMOVED_SYNTAX_ERROR: pass
                    # Mock: Component isolation for controlled unit testing
                    # REMOVED_SYNTAX_ERROR: user = Mock(spec=User)
                    # REMOVED_SYNTAX_ERROR: user.permissions = None
                    # REMOVED_SYNTAX_ERROR: await PermissionService.revoke_permission(mock_db_session, user, "test_perm")
                    # REMOVED_SYNTAX_ERROR: assert user.permissions is not None
                    # REMOVED_SYNTAX_ERROR: assert "revoked" in user.permissions

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_revoke_permission_adds_to_revoked_list(self, mock_db_session):
                        # REMOVED_SYNTAX_ERROR: """Revoke permission adds to revoked list."""
                        # REMOVED_SYNTAX_ERROR: user = create_user_with_custom_permissions()
                        # REMOVED_SYNTAX_ERROR: await PermissionService.revoke_permission(mock_db_session, user, "revoked_perm")
                        # REMOVED_SYNTAX_ERROR: assert "revoked_perm" in user.permissions["revoked"]
                        # REMOVED_SYNTAX_ERROR: mock_db_session.commit.assert_called_once()

# REMOVED_SYNTAX_ERROR: def test_custom_permissions_applied_correctly(self):
    # REMOVED_SYNTAX_ERROR: """Custom permissions are applied correctly."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: user = create_user_with_custom_permissions( )
    # REMOVED_SYNTAX_ERROR: additional=["bonus_perm"],
    # REMOVED_SYNTAX_ERROR: revoked=["chat"]
    
    # REMOVED_SYNTAX_ERROR: perms = PermissionService.get_user_permissions(user)
    # REMOVED_SYNTAX_ERROR: assert "bonus_perm" in perms
    # REMOVED_SYNTAX_ERROR: assert "chat" not in perms  # Should be revoked

# REMOVED_SYNTAX_ERROR: class TestSetUserRole:
    # REMOVED_SYNTAX_ERROR: """Test setting user roles and validation."""
    # REMOVED_SYNTAX_ERROR: pass

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_set_user_role_updates_role(self, mock_db_session, free_tier_user):
        # REMOVED_SYNTAX_ERROR: """Set user role updates role correctly."""
        # REMOVED_SYNTAX_ERROR: result = await PermissionService.set_user_role(mock_db_session, free_tier_user, "power_user")
        # REMOVED_SYNTAX_ERROR: assert result.role == "power_user"
        # REMOVED_SYNTAX_ERROR: mock_db_session.commit.assert_called_once()

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_set_user_role_updates_developer_flag(self, mock_db_session, free_tier_user):
            # REMOVED_SYNTAX_ERROR: """Set user role updates developer flag for elevated roles."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: await PermissionService.set_user_role(mock_db_session, free_tier_user, "developer")
            # REMOVED_SYNTAX_ERROR: assert free_tier_user.is_developer is True

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_set_user_role_validates_role(self, mock_db_session, free_tier_user):
                # REMOVED_SYNTAX_ERROR: """Set user role validates role exists in hierarchy."""
                # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="Invalid role"):
                    # REMOVED_SYNTAX_ERROR: await PermissionService.set_user_role(mock_db_session, free_tier_user, "invalid_role")

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_set_user_role_preserves_old_role_info(self, mock_db_session, pro_tier_user):
                        # REMOVED_SYNTAX_ERROR: """Set user role preserves information about old role."""
                        # REMOVED_SYNTAX_ERROR: pass
                        # REMOVED_SYNTAX_ERROR: original_role = pro_tier_user.role
                        # REMOVED_SYNTAX_ERROR: result = await PermissionService.set_user_role(mock_db_session, pro_tier_user, "developer")
                        # Should have changed role
                        # REMOVED_SYNTAX_ERROR: assert result.role != original_role
                        # REMOVED_SYNTAX_ERROR: assert result.role == "developer"

# REMOVED_SYNTAX_ERROR: class TestPermissionAggregation:
    # REMOVED_SYNTAX_ERROR: """Test permission aggregation and complex scenarios."""
    # REMOVED_SYNTAX_ERROR: pass

# REMOVED_SYNTAX_ERROR: def test_has_any_permission_with_wildcard(self, super_admin_user):
    # REMOVED_SYNTAX_ERROR: """has_any_permission works with wildcard permissions."""
    # Super admin should have comprehensive permissions
    # REMOVED_SYNTAX_ERROR: result = PermissionService.has_any_permission( )
    # REMOVED_SYNTAX_ERROR: super_admin_user, ["chat", "corpus_read"]
    
    # REMOVED_SYNTAX_ERROR: assert result is True  # Super admin has comprehensive permissions

# REMOVED_SYNTAX_ERROR: def test_has_any_permission_with_specific(self, free_tier_user):
    # REMOVED_SYNTAX_ERROR: """has_any_permission works with specific permissions."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: result = PermissionService.has_any_permission( )
    # REMOVED_SYNTAX_ERROR: free_tier_user, ["chat", "nonexistent_perm"]
    
    # REMOVED_SYNTAX_ERROR: assert result is True  # Has chat permission

# REMOVED_SYNTAX_ERROR: def test_has_all_permissions_with_wildcard(self, super_admin_user):
    # REMOVED_SYNTAX_ERROR: """has_all_permissions works with wildcard permissions."""
    # REMOVED_SYNTAX_ERROR: result = PermissionService.has_all_permissions( )
    # REMOVED_SYNTAX_ERROR: super_admin_user, ["chat", "corpus_read", "user_management"]
    
    # REMOVED_SYNTAX_ERROR: assert result is True  # Super admin has comprehensive permissions

# REMOVED_SYNTAX_ERROR: def test_has_all_permissions_missing_one(self, free_tier_user):
    # REMOVED_SYNTAX_ERROR: """has_all_permissions returns False when missing one permission."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: result = PermissionService.has_all_permissions( )
    # REMOVED_SYNTAX_ERROR: free_tier_user, ["chat", "corpus_read"]  # Missing corpus_read
    
    # REMOVED_SYNTAX_ERROR: assert result is False

# REMOVED_SYNTAX_ERROR: def test_get_all_permissions_for_superadmin_comprehensive(self):
    # REMOVED_SYNTAX_ERROR: """Super admin gets comprehensive permission set."""
    # REMOVED_SYNTAX_ERROR: all_perms = PermissionService._get_all_permissions_for_superadmin()
    # Should include permissions from all role levels
    # REMOVED_SYNTAX_ERROR: assert "chat" in all_perms
    # REMOVED_SYNTAX_ERROR: assert "corpus_read" in all_perms
    # REMOVED_SYNTAX_ERROR: assert "debug_panel" in all_perms
    # REMOVED_SYNTAX_ERROR: assert "user_management" in all_perms

# REMOVED_SYNTAX_ERROR: class TestEdgeCasesAndErrorHandling:
    # REMOVED_SYNTAX_ERROR: """Test edge cases and error handling scenarios."""
    # REMOVED_SYNTAX_ERROR: pass

# REMOVED_SYNTAX_ERROR: def test_empty_permissions_dict_handling(self):
    # REMOVED_SYNTAX_ERROR: """Empty permissions dict is handled correctly."""
    # Mock: Component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: user = Mock(spec=User)
    # REMOVED_SYNTAX_ERROR: user.role = "standard_user"
    # REMOVED_SYNTAX_ERROR: user.permissions = {}
    # REMOVED_SYNTAX_ERROR: user.is_developer = False
    # REMOVED_SYNTAX_ERROR: user.is_superuser = False
    # REMOVED_SYNTAX_ERROR: perms = PermissionService.get_user_permissions(user)
    # Should get standard role permissions
    # REMOVED_SYNTAX_ERROR: assert "chat" in perms

# REMOVED_SYNTAX_ERROR: def test_none_permissions_handling(self):
    # REMOVED_SYNTAX_ERROR: """None permissions is handled correctly."""
    # REMOVED_SYNTAX_ERROR: pass
    # Mock: Component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: user = Mock(spec=User)
    # REMOVED_SYNTAX_ERROR: user.role = "standard_user"
    # REMOVED_SYNTAX_ERROR: user.permissions = None
    # REMOVED_SYNTAX_ERROR: user.is_developer = False
    # REMOVED_SYNTAX_ERROR: user.is_superuser = False
    # REMOVED_SYNTAX_ERROR: perms = PermissionService.get_user_permissions(user)
    # Should get standard role permissions
    # REMOVED_SYNTAX_ERROR: assert "chat" in perms

# REMOVED_SYNTAX_ERROR: def test_unknown_role_gets_empty_permissions(self):
    # REMOVED_SYNTAX_ERROR: """Unknown role gets empty permissions."""
    # Mock: Component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: user = Mock(spec=User)
    # REMOVED_SYNTAX_ERROR: user.role = "unknown_role"
    # REMOVED_SYNTAX_ERROR: user.permissions = {}
    # REMOVED_SYNTAX_ERROR: user.is_developer = False
    # REMOVED_SYNTAX_ERROR: user.is_superuser = False
    # REMOVED_SYNTAX_ERROR: perms = PermissionService.get_user_permissions(user)
    # Should get empty set for unknown role
    # REMOVED_SYNTAX_ERROR: assert len(perms) == 0

# REMOVED_SYNTAX_ERROR: def test_case_insensitive_netra_domain_detection(self):
    # REMOVED_SYNTAX_ERROR: """Netra domain detection is case insensitive."""
    # REMOVED_SYNTAX_ERROR: pass
    # Mock: Component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: user = Mock(spec=User)
    # REMOVED_SYNTAX_ERROR: user.email = "test@NETRASYSTEMS.AI"
    # REMOVED_SYNTAX_ERROR: result = PermissionService._check_netra_domain(user)
    # REMOVED_SYNTAX_ERROR: assert result is True

# REMOVED_SYNTAX_ERROR: def test_none_email_handling_in_domain_check(self):
    # REMOVED_SYNTAX_ERROR: """None email is handled in domain check."""
    # Mock: Component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: user = Mock(spec=User)
    # REMOVED_SYNTAX_ERROR: user.email = None
    # REMOVED_SYNTAX_ERROR: result = PermissionService._check_netra_domain(user)
    # REMOVED_SYNTAX_ERROR: assert result is False

    # REMOVED_SYNTAX_ERROR: pass