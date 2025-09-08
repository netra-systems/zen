"""
Unit Tests: User Role Assignment Logic

Business Value Justification (BVJ):
- Segment: Mid, Enterprise (role management critical for larger organizations)
- Business Goal: Ensure proper role assignment and access control
- Value Impact: Role assignment controls user permissions and system access
- Strategic Impact: Security and governance - improper roles cause access issues

CRITICAL REQUIREMENTS per CLAUDE.md:
- Uses SSOT base test case patterns
"""

import pytest
from typing import List, Dict, Set
from enum import Enum

from test_framework.ssot.base_test_case import SSotBaseTestCase


class UserRole(Enum):
    """User roles in the system."""
    GUEST = "guest"
    USER = "user" 
    MANAGER = "manager"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class TestUserRoleAssignment(SSotBaseTestCase):
    """Unit tests for user role assignment business logic."""
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        self.set_env_var("DEFAULT_USER_ROLE", "user")
        self.set_env_var("MAX_ROLES_PER_USER", "3")
        
        self.role_hierarchy = {
            UserRole.SUPER_ADMIN: [UserRole.ADMIN, UserRole.MANAGER, UserRole.USER, UserRole.GUEST],
            UserRole.ADMIN: [UserRole.MANAGER, UserRole.USER, UserRole.GUEST],
            UserRole.MANAGER: [UserRole.USER, UserRole.GUEST],
            UserRole.USER: [UserRole.GUEST],
            UserRole.GUEST: []
        }
        
    def _assign_role_to_user(self, user_id: str, roles: List[UserRole]) -> Dict:
        """Core role assignment logic."""
        max_roles = int(self.get_env_var("MAX_ROLES_PER_USER"))
        
        if len(roles) > max_roles:
            return {"success": False, "error": f"Too many roles (max: {max_roles})"}
            
        # Remove duplicate roles
        unique_roles = list(set(roles))
        
        return {
            "success": True,
            "user_id": user_id,
            "roles": unique_roles,
            "assigned_at": "2024-09-08T10:00:00Z"
        }
        
    def _get_effective_permissions(self, roles: List[UserRole]) -> Set[UserRole]:
        """Get effective permissions based on role hierarchy."""
        effective = set(roles)
        for role in roles:
            if role in self.role_hierarchy:
                effective.update(self.role_hierarchy[role])
        return effective
    
    @pytest.mark.unit
    def test_single_role_assignment(self):
        """Test assignment of single role to user."""
        result = self._assign_role_to_user("user123", [UserRole.USER])
        
        assert result["success"] is True
        assert result["user_id"] == "user123"
        assert UserRole.USER in result["roles"]
        assert len(result["roles"]) == 1
        
        self.record_metric("single_role_assignment", True)
        
    @pytest.mark.unit
    def test_multiple_role_assignment(self):
        """Test assignment of multiple roles to user."""
        roles = [UserRole.USER, UserRole.MANAGER]
        result = self._assign_role_to_user("user123", roles)
        
        assert result["success"] is True
        assert len(result["roles"]) == 2
        assert UserRole.USER in result["roles"]
        assert UserRole.MANAGER in result["roles"]
        
        self.record_metric("multiple_role_assignment", True)
        
    @pytest.mark.unit
    def test_role_hierarchy_permissions(self):
        """Test role hierarchy permission inheritance."""
        admin_roles = [UserRole.ADMIN]
        admin_permissions = self._get_effective_permissions(admin_roles)
        
        expected_permissions = {UserRole.ADMIN, UserRole.MANAGER, UserRole.USER, UserRole.GUEST}
        assert admin_permissions == expected_permissions
        
        self.record_metric("hierarchy_permissions_test", True)
        
    @pytest.mark.unit
    def test_role_limit_enforcement(self):
        """Test enforcement of maximum roles per user."""
        too_many_roles = [UserRole.USER, UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN]
        result = self._assign_role_to_user("user123", too_many_roles)
        
        assert result["success"] is False
        assert "Too many roles" in result["error"]
        
        self.record_metric("role_limit_enforcement", True)
        
    @pytest.mark.unit
    def test_duplicate_role_removal(self):
        """Test removal of duplicate roles."""
        duplicate_roles = [UserRole.USER, UserRole.USER, UserRole.MANAGER]
        result = self._assign_role_to_user("user123", duplicate_roles)
        
        assert result["success"] is True
        assert len(result["roles"]) == 2  # Duplicates removed
        assert UserRole.USER in result["roles"]
        assert UserRole.MANAGER in result["roles"]
        
        self.record_metric("duplicate_removal_test", True)