"""
Permission Service - Handles user permissions and developer auto-detection
"""
import os
from typing import Dict, List, Optional, Set

from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.models_postgres import User
from netra_backend.app.logging_config import central_logger

logger = central_logger

# Permission role hierarchy
ROLE_HIERARCHY = {
    "standard_user": 0,
    "power_user": 1,
    "developer": 2,
    "admin": 3,
    "super_admin": 4
}

# Permission mappings for each role
ROLE_PERMISSIONS = {
    "standard_user": {
        "chat", "history_own", "basic_tools", "view_own_threads"
    },
    "power_user": {
        "chat", "history_own", "basic_tools", "view_own_threads",
        "corpus_read", "synthetic_preview", "advanced_analytics", "api_keys_own"
    },
    "developer": {
        "chat", "history_own", "basic_tools", "view_own_threads",
        "corpus_read", "synthetic_preview", "advanced_analytics", "api_keys_own",
        "corpus_write", "synthetic_generate", "log_access", "debug_panel",
        "impersonation_readonly", "feature_flags", "view_all_threads"
    },
    "admin": {
        "chat", "history_own", "basic_tools", "view_own_threads",
        "corpus_read", "synthetic_preview", "advanced_analytics", "api_keys_own",
        "corpus_write", "synthetic_generate", "log_access", "debug_panel",
        "impersonation_readonly", "feature_flags", "view_all_threads",
        "user_management", "system_config", "billing_access", "security_settings",
        "audit_logs"
    },
    "super_admin": {
        "*"  # All permissions
    }
}

class PermissionService:
    """Service for managing user permissions and role-based access control"""
    
    @staticmethod
    def _check_dev_mode_enabled(user: User) -> bool:
        """Check if dev mode is globally enabled"""
        from netra_backend.app.core.configuration import unified_config_manager
        config = unified_config_manager.get_config()
        if getattr(config, 'dev_mode', False):
            logger.info(f"Developer mode enabled globally - granting developer access to {user.email}")
            return True
        return False
    
    @staticmethod
    def _check_netra_domain(user: User) -> bool:
        """Check if user has Netra domain email"""
        if user.email and "@netrasystems.ai" in user.email.lower():
            logger.info(f"netrasystems.ai domain detected - granting developer access to {user.email}")
            return True
        return False
    
    @staticmethod
    def _check_dev_environment(user: User) -> bool:
        """Check if running in development environment"""
        from netra_backend.app.core.configuration import unified_config_manager
        config = unified_config_manager.get_config()
        if getattr(config, 'environment', '').lower() in ["development", "dev", "local"]:
            logger.info(f"Development environment detected - granting developer access to {user.email}")
            return True
        return False
    
    @staticmethod
    def detect_developer_status(user: User) -> bool:
        """Auto-detect if a user should have developer privileges"""
        dev_mode = PermissionService._check_dev_mode_enabled(user)
        netra_domain = PermissionService._check_netra_domain(user)
        dev_env = PermissionService._check_dev_environment(user)
        return dev_mode or netra_domain or dev_env
    
    @staticmethod
    def _should_elevate_to_developer(user: User) -> bool:
        """Check if user should be elevated to developer"""
        is_not_developer = user.role != "developer"
        is_not_elevated = user.role not in ["admin", "super_admin"]
        return is_not_developer and is_not_elevated
    
    @staticmethod
    async def _elevate_user_to_developer(db: AsyncSession, user: User) -> None:
        """Elevate user to developer role"""
        user.role = "developer"
        user.is_developer = True
        await db.commit()
        logger.info(f"Auto-elevated user {user.email} to developer role")
    
    @staticmethod
    async def update_user_role(db: AsyncSession, user: User, check_developer: bool = True) -> User:
        """Update user role based on detection rules"""
        should_check_dev = check_developer and PermissionService.detect_developer_status(user)
        should_elevate = PermissionService._should_elevate_to_developer(user)
        if should_check_dev and should_elevate:
            await PermissionService._elevate_user_to_developer(db, user)
        return user
    
    @staticmethod
    def _get_all_permissions_for_superadmin() -> Set[str]:
        """Get comprehensive set of all permissions for super admin"""
        all_perms = set()
        for perms in ROLE_PERMISSIONS.values():
            if isinstance(perms, set) and "*" not in perms:
                all_perms.update(perms)
        return all_perms
    
    @staticmethod
    def _apply_custom_permissions(permissions: Set[str], user: User) -> Set[str]:
        """Apply custom additional and revoked permissions"""
        if not user.permissions:
            return permissions
        custom_perms = user.permissions.get("additional", [])
        permissions.update(custom_perms)
        revoked_perms = user.permissions.get("revoked", [])
        permissions -= set(revoked_perms)
        return permissions
    
    @staticmethod
    def get_user_permissions(user: User) -> Set[str]:
        """Get all permissions for a user based on their role and custom permissions"""
        role_perms = ROLE_PERMISSIONS.get(user.role, set())
        if "*" in role_perms:
            return PermissionService._get_all_permissions_for_superadmin()
        permissions = set(role_perms)
        return PermissionService._apply_custom_permissions(permissions, user)
    
    @staticmethod
    def has_permission(user: User, permission: str) -> bool:
        """Check if a user has a specific permission"""
        permissions = PermissionService.get_user_permissions(user)
        return permission in permissions or "*" in permissions
    
    @staticmethod
    def has_any_permission(user: User, permissions: List[str]) -> bool:
        """Check if a user has any of the specified permissions"""
        user_perms = PermissionService.get_user_permissions(user)
        has_wildcard = "*" in user_perms
        has_specific = any(perm in user_perms for perm in permissions)
        return has_specific or has_wildcard
    
    @staticmethod
    def has_all_permissions(user: User, permissions: List[str]) -> bool:
        """Check if a user has all of the specified permissions"""
        user_perms = PermissionService.get_user_permissions(user)
        has_wildcard = "*" in user_perms
        has_all_specific = all(perm in user_perms for perm in permissions)
        return has_all_specific or has_wildcard
    
    @staticmethod
    def is_admin_or_higher(user: User) -> bool:
        """Check if user has admin role or higher"""
        has_admin_role = user.role in ["admin", "super_admin"]
        return has_admin_role or user.is_superuser
    
    @staticmethod
    def is_developer_or_higher(user: User) -> bool:
        """Check if user has developer role or higher"""
        has_elevated_role = user.role in ["developer", "admin", "super_admin"]
        has_dev_flags = user.is_developer or user.is_superuser
        return has_elevated_role or has_dev_flags
    
    @staticmethod
    def get_role_level(role: str) -> int:
        """Get the numeric level of a role for comparison"""
        return ROLE_HIERARCHY.get(role, 0)
    
    @staticmethod
    def _ensure_permissions_structure(user: User) -> None:
        """Ensure permissions dict has proper structure"""
        if not user.permissions:
            user.permissions = {}
        if "additional" not in user.permissions:
            user.permissions["additional"] = []
    
    @staticmethod
    async def _add_permission_if_new(db: AsyncSession, user: User, permission: str) -> None:
        """Add permission if not already present"""
        if permission not in user.permissions["additional"]:
            user.permissions["additional"].append(permission)
            await db.commit()
            logger.info(f"Granted permission '{permission}' to user {user.email}")
    
    @staticmethod
    async def grant_permission(db: AsyncSession, user: User, permission: str) -> User:
        """Grant a specific permission to a user"""
        PermissionService._ensure_permissions_structure(user)
        await PermissionService._add_permission_if_new(db, user, permission)
        return user
    
    @staticmethod
    def _ensure_revoked_permissions_structure(user: User) -> None:
        """Ensure permissions dict has proper revoked structure"""
        if not user.permissions:
            user.permissions = {}
        if "revoked" not in user.permissions:
            user.permissions["revoked"] = []
    
    @staticmethod
    async def _add_revoked_permission_if_new(db: AsyncSession, user: User, permission: str) -> None:
        """Add revoked permission if not already present"""
        if permission not in user.permissions["revoked"]:
            user.permissions["revoked"].append(permission)
            await db.commit()
            logger.info(f"Revoked permission '{permission}' from user {user.email}")
    
    @staticmethod
    async def revoke_permission(db: AsyncSession, user: User, permission: str) -> User:
        """Revoke a specific permission from a user"""
        PermissionService._ensure_revoked_permissions_structure(user)
        await PermissionService._add_revoked_permission_if_new(db, user, permission)
        return user
    
    @staticmethod
    def _validate_role(role: str) -> None:
        """Validate role is in hierarchy"""
        if role not in ROLE_HIERARCHY:
            raise ValueError(f"Invalid role: {role}")
    
    @staticmethod
    def _update_user_role_fields(user: User, role: str) -> str:
        """Update user role and developer flag, return old role"""
        old_role = user.role
        user.role = role
        user.is_developer = role in ["developer", "admin", "super_admin"]
        return old_role
    
    @staticmethod
    async def set_user_role(db: AsyncSession, user: User, role: str) -> User:
        """Set a user's role"""
        PermissionService._validate_role(role)
        old_role = PermissionService._update_user_role_fields(user, role)
        await db.commit()
        logger.info(f"Changed role for user {user.email} from {old_role} to {role}")
        return user