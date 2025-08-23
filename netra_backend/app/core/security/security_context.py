"""Security context for managing user authentication and authorization state.

This module provides the SecurityContext class which tracks the current
user's authentication state, permissions, and tenant context.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Set
from datetime import datetime, timezone
from enum import Enum


class AuthenticationLevel(Enum):
    """Authentication levels for security context."""
    UNAUTHENTICATED = "unauthenticated"
    BASIC = "basic"
    MULTI_FACTOR = "multi_factor"
    ELEVATED = "elevated"


class PermissionLevel(Enum):
    """Permission levels for authorization."""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


@dataclass
class UserInfo:
    """User information for security context."""
    user_id: str
    username: str
    email: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    tenant_id: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None


@dataclass
class TenantContext:
    """Tenant context information."""
    tenant_id: str
    tenant_name: str
    subscription_tier: str = "free"
    max_users: int = 10
    features_enabled: Set[str] = field(default_factory=set)
    custom_permissions: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True


@dataclass
class SessionInfo:
    """Session information for security context."""
    session_id: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_valid: bool = True


class SecurityContext:
    """Security context for managing authentication and authorization state."""
    
    def __init__(self):
        """Initialize security context."""
        self._user: Optional[UserInfo] = None
        self._tenant: Optional[TenantContext] = None
        self._session: Optional[SessionInfo] = None
        self._permissions: Set[str] = set()
        self._auth_level: AuthenticationLevel = AuthenticationLevel.UNAUTHENTICATED
        self._metadata: Dict[str, Any] = {}
        self._created_at = datetime.now(timezone.utc)
        
    @property
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return (self._user is not None and 
                self._auth_level != AuthenticationLevel.UNAUTHENTICATED and
                self._session is not None and 
                self._session.is_valid)
    
    @property
    def user(self) -> Optional[UserInfo]:
        """Get current user information."""
        return self._user
    
    @property
    def tenant(self) -> Optional[TenantContext]:
        """Get current tenant context."""
        return self._tenant
    
    @property
    def session(self) -> Optional[SessionInfo]:
        """Get current session information."""
        return self._session
    
    @property
    def auth_level(self) -> AuthenticationLevel:
        """Get current authentication level."""
        return self._auth_level
    
    @property
    def permissions(self) -> Set[str]:
        """Get current user permissions."""
        return self._permissions.copy()
    
    def authenticate(self, 
                    user_info: UserInfo, 
                    session_info: SessionInfo,
                    auth_level: AuthenticationLevel = AuthenticationLevel.BASIC,
                    permissions: Optional[Set[str]] = None) -> None:
        """Authenticate user and set security context."""
        self._user = user_info
        self._session = session_info
        self._auth_level = auth_level
        
        if permissions:
            self._permissions = permissions.copy()
        else:
            # Set default permissions based on roles
            self._permissions = self._calculate_permissions_from_roles(user_info.roles)
        
        # Update session last activity
        if self._session:
            self._session.last_activity = datetime.now(timezone.utc)
    
    def set_tenant_context(self, tenant: TenantContext) -> None:
        """Set tenant context for multi-tenant operations."""
        self._tenant = tenant
        
        # Add tenant-specific permissions
        if tenant.custom_permissions:
            for permission, granted in tenant.custom_permissions.items():
                if granted:
                    self._permissions.add(permission)
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission."""
        if not self.is_authenticated:
            return False
        
        # Check direct permissions
        if permission in self._permissions:
            return True
        
        # Check role-based permissions
        if self._user and self._has_role_permission(permission, self._user.roles):
            return True
        
        # Check tenant permissions
        if self._tenant and self._has_tenant_permission(permission):
            return True
        
        return False
    
    def has_role(self, role: str) -> bool:
        """Check if user has specific role."""
        return self._user is not None and role in self._user.roles
    
    def has_any_role(self, roles: List[str]) -> bool:
        """Check if user has any of the specified roles."""
        if not self._user:
            return False
        return any(role in self._user.roles for role in roles)
    
    def has_all_roles(self, roles: List[str]) -> bool:
        """Check if user has all specified roles."""
        if not self._user:
            return False
        return all(role in self._user.roles for role in roles)
    
    def is_tenant_member(self, tenant_id: str) -> bool:
        """Check if user is member of specified tenant."""
        return (self._user is not None and 
                self._user.tenant_id == tenant_id)
    
    def can_access_resource(self, resource: str, action: str = "read") -> bool:
        """Check if user can access resource with specified action."""
        permission = f"{resource}:{action}"
        return self.has_permission(permission)
    
    def elevate_auth_level(self, new_level: AuthenticationLevel) -> bool:
        """Elevate authentication level (e.g., for sensitive operations)."""
        if not self.is_authenticated:
            return False
        
        # Only allow elevation, not downgrade
        level_order = {
            AuthenticationLevel.UNAUTHENTICATED: 0,
            AuthenticationLevel.BASIC: 1,
            AuthenticationLevel.MULTI_FACTOR: 2,
            AuthenticationLevel.ELEVATED: 3
        }
        
        current_level = level_order.get(self._auth_level, 0)
        new_level_value = level_order.get(new_level, 0)
        
        if new_level_value > current_level:
            self._auth_level = new_level
            return True
        
        return False
    
    def invalidate_session(self) -> None:
        """Invalidate current session."""
        if self._session:
            self._session.is_valid = False
        self._auth_level = AuthenticationLevel.UNAUTHENTICATED
        self._permissions.clear()
    
    def refresh_session(self, new_expires_at: Optional[datetime] = None) -> bool:
        """Refresh session with new expiration time."""
        if not self._session or not self._session.is_valid:
            return False
        
        self._session.last_activity = datetime.now(timezone.utc)
        
        if new_expires_at:
            self._session.expires_at = new_expires_at
        
        return True
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata for security context."""
        self._metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata from security context."""
        return self._metadata.get(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert security context to dictionary."""
        return {
            "is_authenticated": self.is_authenticated,
            "user": {
                "user_id": self._user.user_id,
                "username": self._user.username,
                "email": self._user.email,
                "roles": self._user.roles,
                "tenant_id": self._user.tenant_id
            } if self._user else None,
            "tenant": {
                "tenant_id": self._tenant.tenant_id,
                "tenant_name": self._tenant.tenant_name,
                "subscription_tier": self._tenant.subscription_tier
            } if self._tenant else None,
            "session": {
                "session_id": self._session.session_id,
                "created_at": self._session.created_at.isoformat(),
                "is_valid": self._session.is_valid
            } if self._session else None,
            "auth_level": self._auth_level.value,
            "permissions": list(self._permissions),
            "metadata": self._metadata
        }
    
    def _calculate_permissions_from_roles(self, roles: List[str]) -> Set[str]:
        """Calculate permissions based on user roles."""
        permissions = set()
        
        role_permissions = {
            "user": {"read:basic", "write:own"},
            "moderator": {"read:basic", "write:own", "read:others", "moderate:content"},
            "admin": {"read:all", "write:all", "admin:users", "admin:system"},
            "super_admin": {"*"}  # All permissions
        }
        
        for role in roles:
            if role in role_permissions:
                if "*" in role_permissions[role]:
                    # Super admin gets all permissions
                    permissions.add("*")
                    break
                else:
                    permissions.update(role_permissions[role])
        
        return permissions
    
    def _has_role_permission(self, permission: str, roles: List[str]) -> bool:
        """Check if any role grants the permission."""
        # Super admin check
        if "super_admin" in roles:
            return True
        
        # Check specific role permissions
        role_permissions = {
            "admin": {"read:all", "write:all", "admin:users", "admin:system"},
            "moderator": {"read:basic", "read:others", "moderate:content"}
        }
        
        for role in roles:
            if role in role_permissions and permission in role_permissions[role]:
                return True
        
        return False
    
    def _has_tenant_permission(self, permission: str) -> bool:
        """Check if tenant grants the permission."""
        if not self._tenant or not self._tenant.custom_permissions:
            return False
        
        return self._tenant.custom_permissions.get(permission, False)


# Default security context instance
current_security_context = SecurityContext()