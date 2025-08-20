"""
Permission Service Core Tests - Constants, Detection, Role Updates, Permissions
Split from test_permission_service.py to maintain 450-line limit
"""

import pytest
import os
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from app.services.permission_service import PermissionService, ROLE_HIERARCHY, ROLE_PERMISSIONS
from app.db.models_postgres import User


class TestPermissionServiceConstants:
    """Test permission service constants and configuration"""
    
    def test_role_hierarchy_ordering(self):
        """Test that role hierarchy is properly ordered"""
        assert ROLE_HIERARCHY["standard_user"] < ROLE_HIERARCHY["power_user"]
        assert ROLE_HIERARCHY["power_user"] < ROLE_HIERARCHY["developer"]
        assert ROLE_HIERARCHY["developer"] < ROLE_HIERARCHY["admin"]
        assert ROLE_HIERARCHY["admin"] < ROLE_HIERARCHY["super_admin"]
    
    def test_role_permissions_inheritance(self):
        """Test that higher roles inherit lower role permissions"""
        standard_perms = ROLE_PERMISSIONS["standard_user"]
        power_perms = ROLE_PERMISSIONS["power_user"]
        dev_perms = ROLE_PERMISSIONS["developer"]
        admin_perms = ROLE_PERMISSIONS["admin"]
        
        assert standard_perms.issubset(power_perms)
        assert power_perms.issubset(dev_perms)
        assert dev_perms.issubset(admin_perms)
        assert ROLE_PERMISSIONS["super_admin"] == {"*"}
    
    def test_critical_permissions_restricted(self):
        """Test that critical permissions are restricted to appropriate roles"""
        critical_perms = {"user_management", "system_config", "security_settings", "audit_logs"}
        
        assert critical_perms.isdisjoint(ROLE_PERMISSIONS["standard_user"])
        assert critical_perms.isdisjoint(ROLE_PERMISSIONS["power_user"])
        assert critical_perms.issubset(ROLE_PERMISSIONS["admin"])


class TestDetectDeveloperStatus:
    """Test developer status detection logic"""
    
    def test_detect_developer_with_dev_mode_env(self):
        """Test developer detection with DEV_MODE environment variable"""
        user = Mock(spec=User)
        user.email = "test@example.com"
        
        with patch.dict(os.environ, {"DEV_MODE": "true"}):
            result = PermissionService.detect_developer_status(user)
            assert result == True
        
        with patch.dict(os.environ, {"DEV_MODE": "TRUE"}):
            result = PermissionService.detect_developer_status(user)
            assert result == True
        
        with patch.dict(os.environ, {"DEV_MODE": "false"}, clear=True):
            result = PermissionService.detect_developer_status(user)
            assert result == False
    
    def test_detect_developer_with_netra_email(self):
        """Test developer detection with @netrasystems.ai email"""
        user = Mock(spec=User)
        
        user.email = "developer@netrasystems.ai"
        result = PermissionService.detect_developer_status(user)
        assert result == True
        
        user.email = "Developer@NETRA.AI"
        result = PermissionService.detect_developer_status(user)
        assert result == True
        
        user.email = "user@example.com"
        with patch.dict(os.environ, {}, clear=True):
            result = PermissionService.detect_developer_status(user)
            assert result == False
    
    def test_detect_developer_with_dev_environment(self):
        """Test developer detection with development environment"""
        user = Mock(spec=User)
        user.email = "test@example.com"
        
        test_envs = ["development", "dev", "local"]
        for env in test_envs:
            with patch.dict(os.environ, {"ENVIRONMENT": env}, clear=True):
                result = PermissionService.detect_developer_status(user)
                assert result == True, f"Failed for environment: {env}"
        
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True):
            result = PermissionService.detect_developer_status(user)
            assert result == False
    
    def test_detect_developer_priority_order(self):
        """Test that detection methods are checked in correct priority order"""
        user = Mock(spec=User)
        user.email = "test@example.com"
        
        with patch.dict(os.environ, {"DEV_MODE": "true", "ENVIRONMENT": "production"}):
            result = PermissionService.detect_developer_status(user)
            assert result == True
    
    def test_detect_developer_with_none_email(self):
        """Test developer detection with None email"""
        user = Mock(spec=User)
        user.email = None
        
        with patch.dict(os.environ, {}, clear=True):
            result = PermissionService.detect_developer_status(user)
            assert result == False
        
        with patch.dict(os.environ, {"DEV_MODE": "true"}):
            result = PermissionService.detect_developer_status(user)
            assert result == True


class TestUpdateUserRole:
    """Test user role update functionality"""
    
    def test_update_user_role_auto_elevate_to_developer(self):
        """Test auto-elevation to developer role"""
        db = Mock(spec=Session)
        user = Mock(spec=User)
        user.email = "test@netrasystems.ai"
        user.role = "standard_user"
        user.is_developer = False
        
        result = PermissionService.update_user_role(db, user, check_developer=True)
        
        assert user.role == "developer"
        assert user.is_developer == True
        db.commit.assert_called_once()
        assert result == user
    
    def test_update_user_role_no_elevation_for_admin(self):
        """Test that admins are not downgraded to developer"""
        db = Mock(spec=Session)
        user = Mock(spec=User)
        user.email = "admin@netrasystems.ai"
        user.role = "admin"
        user.is_developer = True
        
        result = PermissionService.update_user_role(db, user, check_developer=True)
        
        assert user.role == "admin"  # Should remain admin
        db.commit.assert_not_called()
        assert result == user
    
    def test_update_user_role_no_elevation_for_super_admin(self):
        """Test that super admins are not changed"""
        db = Mock(spec=Session)
        user = Mock(spec=User)
        user.email = "superadmin@netrasystems.ai"
        user.role = "super_admin"
        user.is_developer = True
        
        result = PermissionService.update_user_role(db, user, check_developer=True)
        
        assert user.role == "super_admin"  # Should remain super_admin
        db.commit.assert_not_called()
        assert result == user
    
    def test_update_user_role_skip_developer_check(self):
        """Test skipping developer check"""
        db = Mock(spec=Session)
        user = Mock(spec=User)
        user.email = "test@netrasystems.ai"
        user.role = "standard_user"
        user.is_developer = False
        
        result = PermissionService.update_user_role(db, user, check_developer=False)
        
        assert user.role == "standard_user"  # Should not change
        assert user.is_developer == False
        db.commit.assert_not_called()
        assert result == user
    
    def test_update_user_role_already_developer(self):
        """Test that developers are not re-elevated"""
        db = Mock(spec=Session)
        user = Mock(spec=User)
        user.email = "dev@netrasystems.ai"
        user.role = "developer"
        user.is_developer = True
        
        result = PermissionService.update_user_role(db, user, check_developer=True)
        
        assert user.role == "developer"  # Should remain developer
        db.commit.assert_not_called()  # No commit needed
        assert result == user
    
    def test_update_user_role_power_user_elevation(self):
        """Test power user elevation to developer"""
        db = Mock(spec=Session)
        user = Mock(spec=User)
        user.email = "power@netrasystems.ai"
        user.role = "power_user"
        user.is_developer = False
        
        result = PermissionService.update_user_role(db, user, check_developer=True)
        
        assert user.role == "developer"
        assert user.is_developer == True
        db.commit.assert_called_once()
        assert result == user


class TestCheckPermission:
    """Test permission checking functionality"""
    
    def test_check_permission_standard_user(self):
        """Test permission checks for standard user"""
        user = Mock(spec=User)
        user.role = "standard_user"
        user.permissions = None
        
        result = PermissionService.has_permission(user, "chat")
        assert result == True
        
        result = PermissionService.has_permission(user, "user_management")
        assert result == False
    
    def test_check_permission_super_admin(self):
        """Test permission checks for super admin (wildcard)"""
        user = Mock(spec=User)
        user.role = "super_admin"
        user.permissions = None
        
        # Super admin should have all real permissions
        result = PermissionService.has_permission(user, "user_management")
        assert result == True
        
        result = PermissionService.has_permission(user, "debug_panel")
        assert result == True
    
    def test_check_permission_developer(self):
        """Test permission checks for developer"""
        user = Mock(spec=User)
        user.role = "developer"
        user.permissions = None
        
        result = PermissionService.has_permission(user, "debug_panel")
        assert result == True
        
        result = PermissionService.has_permission(user, "user_management")
        assert result == False
    
    def test_check_permission_invalid_role(self):
        """Test permission check with invalid role"""
        user = Mock(spec=User)
        user.role = "invalid_role"
        user.permissions = None
        
        result = PermissionService.has_permission(user, "chat")
        assert result == False
    
    def test_check_permission_none_role(self):
        """Test permission check with None role"""
        user = Mock(spec=User)
        user.role = None
        user.permissions = None
        
        result = PermissionService.has_permission(user, "chat")
        assert result == False


class TestGetUserPermissions:
    """Test getting user permissions"""
    
    def test_get_user_permissions_standard_user(self):
        """Test getting permissions for standard user"""
        user = Mock(spec=User)
        user.role = "standard_user"
        user.permissions = None  # No custom permissions
        
        permissions = PermissionService.get_user_permissions(user)
        assert permissions == ROLE_PERMISSIONS["standard_user"]
    
    def test_get_user_permissions_super_admin(self):
        """Test getting permissions for super admin"""
        user = Mock(spec=User)
        user.role = "super_admin"
        user.permissions = None
        
        permissions = PermissionService.get_user_permissions(user)
        # Super admin gets all permissions from all roles
        assert "user_management" in permissions
        assert "debug_panel" in permissions
        assert "chat" in permissions
    
    def test_get_user_permissions_invalid_role(self):
        """Test getting permissions for invalid role"""
        user = Mock(spec=User)
        user.role = "invalid_role"
        user.permissions = None
        
        permissions = PermissionService.get_user_permissions(user)
        assert permissions == set()  # Should return empty set
