"""
Permission Test Data Factory
Creates test permission data for role-based access control testing.
Supports various permission patterns and user permission assignments.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from auth_service.auth_core.models.auth_models import UserPermission


class PermissionFactory:
    """Factory for creating test permission data"""
    
    # Standard permission sets
    USER_PERMISSIONS = [
        "user:read_profile",
        "user:update_profile",
        "chat:create",
        "chat:read_own"
    ]
    
    ADMIN_PERMISSIONS = [
        "admin:read_users",
        "admin:update_users",
        "admin:delete_users",
        "system:view_logs",
        "system:manage_settings"
    ]
    
    SERVICE_PERMISSIONS = [
        "service:auth_validate",
        "service:user_lookup",
        "service:session_create",
        "service:session_revoke"
    ]
    
    ENTERPRISE_PERMISSIONS = [
        "enterprise:manage_teams",
        "enterprise:view_analytics",
        "enterprise:manage_billing",
        "enterprise:api_access"
    ]
    
    @staticmethod
    def create_permission_data(
        permission_id: str = None,
        resource: str = "user",
        action: str = "read",
        granted_by: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create permission data dictionary"""
        return {
            "permission_id": permission_id or f"{resource}:{action}",
            "resource": resource,
            "action": action,
            "granted_at": datetime.now(timezone.utc),
            "granted_by": granted_by,
            **kwargs
        }
    
    @staticmethod
    def create_user_permission_data(
        user_id: str = None,
        permission_id: str = None,
        resource: str = "user",
        action: str = "read",
        **kwargs
    ) -> Dict[str, Any]:
        """Create user permission assignment data"""
        permission_data = PermissionFactory.create_permission_data(
            permission_id=permission_id,
            resource=resource,
            action=action,
            **kwargs
        )
        
        permission_data["user_id"] = user_id or str(uuid.uuid4())
        return permission_data
    
    @staticmethod
    def create_basic_user_permissions(user_id: str) -> List[Dict[str, Any]]:
        """Create basic user permission set"""
        permissions = []
        for perm in PermissionFactory.USER_PERMISSIONS:
            resource, action = perm.split(":", 1)
            permissions.append(
                PermissionFactory.create_user_permission_data(
                    user_id=user_id,
                    permission_id=perm,
                    resource=resource,
                    action=action
                )
            )
        return permissions
    
    @staticmethod
    def create_admin_permissions(user_id: str) -> List[Dict[str, Any]]:
        """Create admin permission set"""
        permissions = []
        
        # Include basic user permissions
        permissions.extend(PermissionFactory.create_basic_user_permissions(user_id))
        
        # Add admin permissions
        for perm in PermissionFactory.ADMIN_PERMISSIONS:
            resource, action = perm.split(":", 1)
            permissions.append(
                PermissionFactory.create_user_permission_data(
                    user_id=user_id,
                    permission_id=perm,
                    resource=resource,
                    action=action
                )
            )
        return permissions
    
    @staticmethod
    def create_service_permissions(service_id: str) -> List[Dict[str, Any]]:
        """Create service permission set"""
        permissions = []
        for perm in PermissionFactory.SERVICE_PERMISSIONS:
            resource, action = perm.split(":", 1)
            permissions.append(
                PermissionFactory.create_user_permission_data(
                    user_id=service_id,
                    permission_id=perm,
                    resource=resource,
                    action=action
                )
            )
        return permissions
    
    @staticmethod
    def create_enterprise_permissions(user_id: str) -> List[Dict[str, Any]]:
        """Create enterprise permission set"""
        permissions = []
        
        # Include admin permissions
        permissions.extend(PermissionFactory.create_admin_permissions(user_id))
        
        # Add enterprise permissions
        for perm in PermissionFactory.ENTERPRISE_PERMISSIONS:
            resource, action = perm.split(":", 1)
            permissions.append(
                PermissionFactory.create_user_permission_data(
                    user_id=user_id,
                    permission_id=perm,
                    resource=resource,
                    action=action
                )
            )
        return permissions
    
    @staticmethod
    def create_custom_permissions(
        user_id: str,
        permissions: List[str]
    ) -> List[Dict[str, Any]]:
        """Create custom permission set"""
        permission_list = []
        for perm in permissions:
            if ":" in perm:
                resource, action = perm.split(":", 1)
            else:
                resource, action = "custom", perm
            
            permission_list.append(
                PermissionFactory.create_user_permission_data(
                    user_id=user_id,
                    permission_id=perm,
                    resource=resource,
                    action=action
                )
            )
        return permission_list
    
    @staticmethod
    def create_read_only_permissions(user_id: str) -> List[Dict[str, Any]]:
        """Create read-only permission set"""
        read_permissions = [
            "user:read_profile",
            "chat:read_own",
            "system:view_status"
        ]
        return PermissionFactory.create_custom_permissions(user_id, read_permissions)
    
    @staticmethod
    def has_permission(
        user_permissions: List[Dict[str, Any]],
        required_permission: str
    ) -> bool:
        """Check if user has required permission"""
        for perm in user_permissions:
            if perm["permission_id"] == required_permission:
                return True
        return False
    
    @staticmethod
    def get_permissions_by_resource(
        user_permissions: List[Dict[str, Any]],
        resource: str
    ) -> List[Dict[str, Any]]:
        """Get all permissions for a specific resource"""
        return [
            perm for perm in user_permissions
            if perm["resource"] == resource
        ]
    
    @staticmethod
    def create_permission_strings(permissions_data: List[Dict[str, Any]]) -> List[str]:
        """Convert permission data to permission strings"""
        return [perm["permission_id"] for perm in permissions_data]


class RoleFactory:
    """Factory for creating role-based permission sets"""
    
    ROLES = {
        "user": PermissionFactory.USER_PERMISSIONS,
        "admin": PermissionFactory.ADMIN_PERMISSIONS + PermissionFactory.USER_PERMISSIONS,
        "service": PermissionFactory.SERVICE_PERMISSIONS,
        "enterprise": (
            PermissionFactory.ENTERPRISE_PERMISSIONS + 
            PermissionFactory.ADMIN_PERMISSIONS + 
            PermissionFactory.USER_PERMISSIONS
        )
    }
    
    @staticmethod
    def create_role_permissions(user_id: str, role: str) -> List[Dict[str, Any]]:
        """Create permissions for a specific role"""
        if role not in RoleFactory.ROLES:
            raise ValueError(f"Unknown role: {role}")
        
        return PermissionFactory.create_custom_permissions(
            user_id,
            RoleFactory.ROLES[role]
        )
    
    @staticmethod
    def get_role_permissions(role: str) -> List[str]:
        """Get permission list for a role"""
        return RoleFactory.ROLES.get(role, [])