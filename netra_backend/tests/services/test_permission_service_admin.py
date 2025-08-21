"""
Comprehensive tests for Permission Service - Admin & Security
Critical security component - Admin checks and edge cases
Split from test_permission_service.py to maintain 450-line limit
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()


# Import the module under test
from netra_backend.app.services.permission_service import PermissionService, ROLE_HIERARCHY, ROLE_PERMISSIONS
from netra_backend.app.db.models_postgres import User


class TestAdminChecks:
    """Test admin and developer check functionality"""
    
    def test_is_admin_or_higher(self):
        """Test is_admin_or_higher checks"""
        user = Mock(spec=User)
        user.role = "admin"
        user.is_superuser = False
        assert PermissionService.is_admin_or_higher(user) == True
        
        user.role = "super_admin"
        assert PermissionService.is_admin_or_higher(user) == True
        
        user.role = "developer"
        assert PermissionService.is_admin_or_higher(user) == False
        
        user.role = "standard_user"
        user.is_superuser = True
        assert PermissionService.is_admin_or_higher(user) == True
    
    def test_is_developer_or_higher(self):
        """Test is_developer_or_higher checks"""
        user = Mock(spec=User)
        user.role = "developer"
        user.is_developer = True
        user.is_superuser = False
        assert PermissionService.is_developer_or_higher(user) == True
        
        user.role = "admin"
        assert PermissionService.is_developer_or_higher(user) == True
        
        user.role = "standard_user"
        user.is_developer = False
        assert PermissionService.is_developer_or_higher(user) == False


class TestPermissionGroups:
    """Test permission group functionality"""
    
    def test_has_any_permission(self):
        """Test has_any_permission checks"""
        user = Mock(spec=User)
        user.role = "developer"
        user.permissions = None
        
        # Should have at least one of these
        result = PermissionService.has_any_permission(user, ["debug_panel", "user_management"])
        assert result == True
        
        # Should not have any of these
        result = PermissionService.has_any_permission(user, ["billing_access", "security_settings"])
        assert result == False
    
    def test_has_all_permissions(self):
        """Test has_all_permissions checks"""
        user = Mock(spec=User)
        user.role = "developer"
        user.permissions = None
        
        # Should have all of these
        result = PermissionService.has_all_permissions(user, ["chat", "debug_panel"])
        assert result == True
        
        # Should not have all of these
        result = PermissionService.has_all_permissions(user, ["debug_panel", "user_management"])
        assert result == False


class TestSecurityEdgeCases:
    """Test security edge cases and attack vectors"""
    
    def test_sql_injection_in_permission_check(self):
        """Test that SQL injection attempts don't bypass permissions"""
        user = Mock(spec=User)
        user.role = "standard_user'; DROP TABLE users; --"
        user.permissions = None
        
        result = PermissionService.has_permission(user, "admin_panel")
        assert result == False
    
    def test_case_sensitivity_in_roles(self):
        """Test that role checks are case-sensitive"""
        user = Mock(spec=User)
        user.role = "ADMIN"  # Uppercase
        user.permissions = None
        
        result = PermissionService.has_permission(user, "user_management")
        assert result == False  # Should not match "admin"
    
    def test_permission_escalation_attempt(self):
        """Test that users cannot escalate their own permissions"""
        db = Mock(spec=Session)
        user = Mock(spec=User)
        user.email = "hacker@evil.com"
        user.role = "standard_user"
        user.is_developer = False
        
        # Attempt to modify role directly before update
        user.role = "admin"
        
        with patch.dict(os.environ, {}, clear=True):
            result = PermissionService.update_user_role(db, user, check_developer=True)
            
            # Should remain admin since detect_developer_status returns False
            assert user.role == "admin"
            db.commit.assert_not_called()


class TestRoleManagement:
    """Test role management and permission operations"""
    
    def test_grant_permission(self):
        """Test granting additional permissions to user"""
        db = Mock(spec=Session)
        user = Mock(spec=User)
        user.email = "test@example.com"
        user.permissions = None
        
        result = PermissionService.grant_permission(db, user, "special_access")
        
        assert user.permissions["additional"] == ["special_access"]
        db.commit.assert_called_once()
        assert result == user
    
    def test_grant_permission_existing_permissions(self):
        """Test granting permission when user already has permissions"""
        db = Mock(spec=Session)
        user = Mock(spec=User)
        user.email = "test@example.com"
        user.permissions = {"additional": ["existing_perm"]}
        
        result = PermissionService.grant_permission(db, user, "new_perm")
        
        assert "existing_perm" in user.permissions["additional"]
        assert "new_perm" in user.permissions["additional"]
        db.commit.assert_called_once()
    
    def test_grant_permission_duplicate(self):
        """Test granting permission that user already has"""
        db = Mock(spec=Session)
        user = Mock(spec=User)
        user.email = "test@example.com"
        user.permissions = {"additional": ["existing_perm"]}
        
        result = PermissionService.grant_permission(db, user, "existing_perm")
        
        # Should not duplicate
        assert user.permissions["additional"].count("existing_perm") == 1
        db.commit.assert_not_called()
    
    def test_revoke_permission(self):
        """Test revoking permissions from user"""
        db = Mock(spec=Session)
        user = Mock(spec=User)
        user.email = "test@example.com"
        user.permissions = None
        
        result = PermissionService.revoke_permission(db, user, "restricted_access")
        
        assert user.permissions["revoked"] == ["restricted_access"]
        db.commit.assert_called_once()
        assert result == user
    
    def test_revoke_permission_existing(self):
        """Test revoking permission when user already has revoked permissions"""
        db = Mock(spec=Session)
        user = Mock(spec=User)
        user.email = "test@example.com"
        user.permissions = {"revoked": ["old_revoked"]}
        
        result = PermissionService.revoke_permission(db, user, "new_revoked")
        
        assert "old_revoked" in user.permissions["revoked"]
        assert "new_revoked" in user.permissions["revoked"]
        db.commit.assert_called_once()
    
    def test_set_user_role_valid(self):
        """Test setting user role to valid role"""
        db = Mock(spec=Session)
        user = Mock(spec=User)
        user.email = "test@example.com"
        user.role = "standard_user"
        user.is_developer = False
        
        result = PermissionService.set_user_role(db, user, "developer")
        
        assert user.role == "developer"
        assert user.is_developer == True
        db.commit.assert_called_once()
        assert result == user
    
    def test_set_user_role_invalid(self):
        """Test setting user role to invalid role"""
        db = Mock(spec=Session)
        user = Mock(spec=User)
        user.email = "test@example.com"
        user.role = "standard_user"
        
        with pytest.raises(ValueError) as exc_info:
            PermissionService.set_user_role(db, user, "invalid_role")
        
        assert "Invalid role: invalid_role" in str(exc_info.value)
        db.commit.assert_not_called()
    
    def test_get_role_level(self):
        """Test getting numeric role levels"""
        assert PermissionService.get_role_level("standard_user") == 0
        assert PermissionService.get_role_level("power_user") == 1
        assert PermissionService.get_role_level("developer") == 2
        assert PermissionService.get_role_level("admin") == 3
        assert PermissionService.get_role_level("super_admin") == 4
        assert PermissionService.get_role_level("invalid_role") == 0


class TestPermissionLogic:
    """Test complex permission logic scenarios"""
    
    def test_custom_permissions_override_role(self):
        """Test that custom permissions can override role permissions"""
        user = Mock(spec=User)
        user.role = "standard_user"
        user.permissions = {
            "additional": ["admin_panel"],
            "revoked": ["chat"]
        }
        
        # Should have admin_panel despite being standard_user
        assert PermissionService.has_permission(user, "admin_panel") == True
        
        # Should not have chat despite role normally having it
        assert PermissionService.has_permission(user, "chat") == False
    
    def test_super_admin_permissions_comprehensive(self):
        """Test that super admin gets comprehensive permission set"""
        user = Mock(spec=User)
        user.role = "super_admin"
        user.permissions = None
        
        permissions = PermissionService.get_user_permissions(user)
        
        # Should include permissions from all role levels
        assert "chat" in permissions  # standard_user
        assert "corpus_read" in permissions  # power_user
        assert "debug_panel" in permissions  # developer
        assert "user_management" in permissions  # admin
        
        # Should have a substantial number of permissions
        assert len(permissions) > 10
    
    def test_permission_inheritance_chain(self):
        """Test that permission inheritance works correctly"""
        # Test that admin has all developer permissions
        admin_perms = ROLE_PERMISSIONS["admin"]
        dev_perms = ROLE_PERMISSIONS["developer"]
        
        assert dev_perms.issubset(admin_perms)
        
        # Test that developer has all power_user permissions
        power_perms = ROLE_PERMISSIONS["power_user"]
        assert power_perms.issubset(dev_perms)
        
        # Test that power_user has all standard_user permissions
        standard_perms = ROLE_PERMISSIONS["standard_user"]
        assert standard_perms.issubset(power_perms)


