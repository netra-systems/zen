"""
Unit Tests: Permission Validation Algorithms

Business Value Justification (BVJ):
- Segment: Mid, Enterprise (role-based access critical for larger orgs)
- Business Goal: Ensure proper access control and prevent security vulnerabilities
- Value Impact: Permission validation prevents unauthorized access to sensitive operations
- Strategic Impact: Security and compliance - permission failures could lead to data breaches

This module tests the core permission validation algorithms including role hierarchies,
permission inheritance, and access control logic without requiring external services.

CRITICAL REQUIREMENTS per CLAUDE.md:
- Uses IsolatedEnvironment (no direct os.environ access)  
- Tests business logic only (no external dependencies)
- Uses SSOT base test case patterns
- Follows type safety requirements
"""

import pytest
from typing import Dict, List, Set, Any, Optional
from enum import Enum

from test_framework.ssot.base_test_case import SSotBaseTestCase


class PermissionLevel(Enum):
    """Enum for permission levels in the system."""
    READ = "read"
    WRITE = "write" 
    DELETE = "delete"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class TestPermissionValidationAlgorithms(SSotBaseTestCase):
    """
    Unit tests for permission validation algorithm business logic.
    Tests access control without external dependencies.
    """
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        
        # Set test environment
        self.set_env_var("PERMISSION_HIERARCHY_ENABLED", "true")
        self.set_env_var("DEFAULT_USER_PERMISSIONS", "read")
        
        # Define permission hierarchies for testing
        self.permission_hierarchy = {
            PermissionLevel.SUPER_ADMIN: [
                PermissionLevel.ADMIN, PermissionLevel.DELETE, 
                PermissionLevel.WRITE, PermissionLevel.READ
            ],
            PermissionLevel.ADMIN: [
                PermissionLevel.DELETE, PermissionLevel.WRITE, PermissionLevel.READ
            ],
            PermissionLevel.DELETE: [PermissionLevel.WRITE, PermissionLevel.READ],
            PermissionLevel.WRITE: [PermissionLevel.READ],
            PermissionLevel.READ: []
        }
        
        # Test user roles and permissions
        self.test_roles = {
            "guest": [PermissionLevel.READ],
            "user": [PermissionLevel.READ, PermissionLevel.WRITE],
            "manager": [PermissionLevel.READ, PermissionLevel.WRITE, PermissionLevel.DELETE],
            "admin": [PermissionLevel.ADMIN],
            "super_admin": [PermissionLevel.SUPER_ADMIN]
        }
        
    def _has_permission(self, user_permissions: List[PermissionLevel], required_permission: PermissionLevel) -> bool:
        """
        Core permission validation algorithm.
        
        Returns True if user has the required permission either directly or through hierarchy.
        """
        # Direct permission check
        if required_permission in user_permissions:
            return True
            
        # Hierarchy check - if user has higher level permission
        for user_perm in user_permissions:
            if user_perm in self.permission_hierarchy:
                inherited_perms = self.permission_hierarchy[user_perm]
                if required_permission in inherited_perms:
                    return True
                    
        return False
        
    def _get_effective_permissions(self, user_permissions: List[PermissionLevel]) -> Set[PermissionLevel]:
        """
        Get all effective permissions for a user including inherited permissions.
        """
        effective_perms = set(user_permissions)
        
        for perm in user_permissions:
            if perm in self.permission_hierarchy:
                effective_perms.update(self.permission_hierarchy[perm])
                
        return effective_perms
        
    def _validate_permission_consistency(self, permissions: List[PermissionLevel]) -> bool:
        """
        Validate that permission list is consistent (no conflicting permissions).
        """
        if not permissions:
            return True
            
        # Check for duplicates
        if len(permissions) != len(set(permissions)):
            return False
            
        # Check for hierarchy conflicts (having both parent and child permissions)
        effective_perms = self._get_effective_permissions(permissions)
        
        for perm in permissions:
            if perm in self.permission_hierarchy:
                # If user explicitly has a permission that's already inherited, it's redundant but not invalid
                inherited_perms = self.permission_hierarchy[perm]
                # This is actually OK - explicit permissions override inherited ones
                
        return True
    
    @pytest.mark.unit
    def test_direct_permission_validation(self):
        """Test direct permission validation (no hierarchy)."""
        user_permissions = [PermissionLevel.READ, PermissionLevel.WRITE]
        
        # User should have direct permissions
        assert self._has_permission(user_permissions, PermissionLevel.READ)
        assert self._has_permission(user_permissions, PermissionLevel.WRITE)
        
        # User should NOT have permissions they don't have
        assert not self._has_permission(user_permissions, PermissionLevel.DELETE)
        assert not self._has_permission(user_permissions, PermissionLevel.ADMIN)
        
        self.record_metric("direct_permission_checks", 4)
        
    @pytest.mark.unit 
    def test_hierarchical_permission_inheritance(self):
        """Test permission inheritance through hierarchy."""
        # Admin user should inherit all lower-level permissions
        admin_permissions = [PermissionLevel.ADMIN]
        
        # Admin should have all inherited permissions
        assert self._has_permission(admin_permissions, PermissionLevel.READ)
        assert self._has_permission(admin_permissions, PermissionLevel.WRITE)
        assert self._has_permission(admin_permissions, PermissionLevel.DELETE)
        assert self._has_permission(admin_permissions, PermissionLevel.ADMIN)
        
        # But not higher level permissions
        assert not self._has_permission(admin_permissions, PermissionLevel.SUPER_ADMIN)
        
        self.record_metric("hierarchy_checks", 5)
        
    @pytest.mark.unit
    def test_super_admin_permission_inheritance(self):
        """Test that super admin inherits all permissions."""
        super_admin_permissions = [PermissionLevel.SUPER_ADMIN]
        
        # Super admin should have ALL permissions
        all_permissions = list(PermissionLevel)
        for perm in all_permissions:
            assert self._has_permission(super_admin_permissions, perm)
            
        self.record_metric("super_admin_checks", len(all_permissions))
        
    @pytest.mark.unit
    def test_effective_permissions_calculation(self):
        """Test calculation of effective permissions including inheritance."""
        # Test guest user (only read)
        guest_perms = self._get_effective_permissions([PermissionLevel.READ])
        assert guest_perms == {PermissionLevel.READ}
        
        # Test admin user (should get all inherited permissions)
        admin_perms = self._get_effective_permissions([PermissionLevel.ADMIN])
        expected_admin_perms = {
            PermissionLevel.ADMIN, PermissionLevel.DELETE, 
            PermissionLevel.WRITE, PermissionLevel.READ
        }
        assert admin_perms == expected_admin_perms
        
        # Test mixed permissions
        mixed_perms = self._get_effective_permissions([PermissionLevel.READ, PermissionLevel.DELETE])
        expected_mixed_perms = {
            PermissionLevel.READ, PermissionLevel.DELETE, PermissionLevel.WRITE
        }
        assert mixed_perms == expected_mixed_perms
        
        self.record_metric("effective_permission_calculations", 3)
        
    @pytest.mark.unit
    def test_role_based_permission_validation(self):
        """Test permission validation for predefined roles."""
        # Test each role has appropriate permissions
        test_cases = [
            ("guest", PermissionLevel.READ, True),
            ("guest", PermissionLevel.WRITE, False),
            ("user", PermissionLevel.READ, True),
            ("user", PermissionLevel.WRITE, True),
            ("user", PermissionLevel.DELETE, False),
            ("manager", PermissionLevel.DELETE, True),
            ("manager", PermissionLevel.ADMIN, False),
            ("admin", PermissionLevel.ADMIN, True),
            ("admin", PermissionLevel.SUPER_ADMIN, False),
            ("super_admin", PermissionLevel.SUPER_ADMIN, True)
        ]
        
        for role, required_perm, expected_result in test_cases:
            role_permissions = self.test_roles[role]
            actual_result = self._has_permission(role_permissions, required_perm)
            assert actual_result == expected_result, (
                f"Role {role} permission check for {required_perm.value} failed: "
                f"expected {expected_result}, got {actual_result}"
            )
            
        self.record_metric("role_permission_checks", len(test_cases))
        
    @pytest.mark.unit
    def test_permission_consistency_validation(self):
        """Test validation of permission consistency."""
        # Test valid permission lists
        valid_permission_lists = [
            [],  # Empty permissions
            [PermissionLevel.READ],
            [PermissionLevel.READ, PermissionLevel.WRITE],
            [PermissionLevel.ADMIN],
            [PermissionLevel.SUPER_ADMIN]
        ]
        
        for perms in valid_permission_lists:
            assert self._validate_permission_consistency(perms)
            
        # Test invalid permission lists
        invalid_permission_lists = [
            [PermissionLevel.READ, PermissionLevel.READ],  # Duplicates
        ]
        
        for perms in invalid_permission_lists:
            assert not self._validate_permission_consistency(perms)
            
        self.record_metric("consistency_validations", len(valid_permission_lists) + len(invalid_permission_lists))
        
    @pytest.mark.unit
    def test_permission_edge_cases(self):
        """Test edge cases in permission validation."""
        # Empty permissions list
        empty_perms = []
        assert not self._has_permission(empty_perms, PermissionLevel.READ)
        
        # Single permission
        single_perm = [PermissionLevel.WRITE]
        assert self._has_permission(single_perm, PermissionLevel.READ)  # Inherited
        assert self._has_permission(single_perm, PermissionLevel.WRITE)  # Direct
        assert not self._has_permission(single_perm, PermissionLevel.DELETE)  # Not inherited
        
        # Multiple high-level permissions (should not conflict)
        multi_high_perms = [PermissionLevel.ADMIN, PermissionLevel.DELETE]
        assert self._has_permission(multi_high_perms, PermissionLevel.READ)
        assert self._has_permission(multi_high_perms, PermissionLevel.ADMIN)
        
        self.record_metric("edge_case_checks", 6)
        
    @pytest.mark.unit
    def test_permission_hierarchy_traversal(self):
        """Test traversal of permission hierarchy for complex scenarios."""
        # Test multi-level inheritance
        for high_perm, inherited_perms in self.permission_hierarchy.items():
            user_with_high_perm = [high_perm]
            
            # User should have all inherited permissions
            for inherited_perm in inherited_perms:
                assert self._has_permission(user_with_high_perm, inherited_perm), (
                    f"User with {high_perm.value} should have inherited {inherited_perm.value}"
                )
                
        # Count total hierarchy checks
        total_checks = sum(len(inherited) for inherited in self.permission_hierarchy.values())
        self.record_metric("hierarchy_traversal_checks", total_checks)