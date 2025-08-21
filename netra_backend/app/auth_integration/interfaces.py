"""
Auth Interface Definitions - Protocol Contracts
Type-safe interfaces for authentication service integration.

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise)  
- Business Goal: Type-safe auth integration
- Value Impact: Reduce integration bugs by 25%
- Revenue Impact: +$1K MRR from stability

Architecture:
- 450-line module limit enforced
- 25-line function limit enforced  
- Protocol-based interfaces for type safety
- Clear contracts for auth service integration
"""
from abc import ABC, abstractmethod
from typing import Protocol, Optional, Dict, Any, List
from datetime import datetime

from netra_backend.app.models import (
    LoginRequest, LoginResponse, TokenData, TokenRequest, TokenResponse,
    RefreshRequest, ServiceTokenRequest, ServiceTokenResponse,
    HealthResponse, SessionInfo, UserPermission, AuditLog
)


class AuthClientProtocol(Protocol):
    """Protocol for auth service client implementations"""
    
    async def login(self, request: LoginRequest) -> Optional[LoginResponse]:
        """Authenticate user and return tokens"""
        ...
    
    async def validate_token(self, token: str) -> Optional[TokenResponse]:
        """Validate access token"""
        ...
    
    async def refresh_token(self, request: RefreshRequest) -> Optional[LoginResponse]:
        """Refresh access token using refresh token"""
        ...
    
    async def logout(self, token: str) -> bool:
        """Logout user and invalidate tokens"""
        ...
    
    async def get_health(self) -> Optional[HealthResponse]:
        """Get auth service health status"""
        ...


class AuthServiceProtocol(Protocol):
    """Protocol for auth service implementations"""
    
    async def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user credentials"""
        ...
    
    async def create_tokens(self, user_id: str, permissions: List[str]) -> Dict[str, str]:
        """Create access and refresh tokens"""
        ...
    
    async def validate_access_token(self, token: str) -> Optional[TokenData]:
        """Validate and decode access token"""
        ...
    
    async def invalidate_token(self, token: str) -> bool:
        """Invalidate token (logout)"""
        ...


class SessionManagerProtocol(Protocol):
    """Protocol for session management"""
    
    async def create_session(self, user_id: str, metadata: Dict[str, Any]) -> SessionInfo:
        """Create new user session"""
        ...
    
    async def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Get session by ID"""
        ...
    
    async def update_session_activity(self, session_id: str) -> bool:
        """Update session last activity timestamp"""
        ...
    
    async def destroy_session(self, session_id: str) -> bool:
        """Destroy user session"""
        ...


class PermissionManagerProtocol(Protocol):
    """Protocol for permission management"""
    
    async def grant_permission(self, user_id: str, permission: str) -> UserPermission:
        """Grant permission to user"""
        ...
    
    async def revoke_permission(self, user_id: str, permission: str) -> bool:
        """Revoke permission from user"""
        ...
    
    async def check_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has permission"""
        ...
    
    async def get_user_permissions(self, user_id: str) -> List[UserPermission]:
        """Get all user permissions"""
        ...


class AuditLoggerProtocol(Protocol):
    """Protocol for auth audit logging"""
    
    async def log_auth_event(self, event: AuditLog) -> bool:
        """Log authentication event"""
        ...
    
    async def get_audit_logs(self, user_id: str, limit: int = 100) -> List[AuditLog]:
        """Get audit logs for user"""
        ...


class TokenValidatorProtocol(Protocol):
    """Protocol for token validation"""
    
    def validate_token_format(self, token: str) -> bool:
        """Validate token format"""
        ...
    
    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode token payload"""
        ...
    
    def is_token_expired(self, token: str) -> bool:
        """Check if token is expired"""
        ...


class PasswordManagerProtocol(Protocol):
    """Protocol for password management"""
    
    def hash_password(self, password: str) -> str:
        """Hash password securely"""
        ...
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        ...
    
    def check_password_strength(self, password: str) -> Dict[str, Any]:
        """Check password strength"""
        ...


class OAuthProviderProtocol(Protocol):
    """Protocol for OAuth provider integration"""
    
    async def get_authorization_url(self, state: str) -> str:
        """Get OAuth authorization URL"""
        ...
    
    async def exchange_code_for_token(self, code: str, state: str) -> Optional[Dict[str, Any]]:
        """Exchange auth code for access token"""
        ...
    
    async def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user info from OAuth provider"""
        ...


class RateLimiterProtocol(Protocol):
    """Protocol for rate limiting"""
    
    async def check_rate_limit(self, key: str, limit: int, window: int) -> bool:
        """Check if request is within rate limit"""
        ...
    
    async def increment_counter(self, key: str, window: int) -> int:
        """Increment rate limit counter"""
        ...


# Abstract base classes for implementations

class BaseAuthClient(ABC):
    """Base implementation for auth service clients"""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout
    
    @abstractmethod
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to auth service"""
        pass
    
    @abstractmethod
    async def _handle_response(self, response: Any) -> Optional[Dict[str, Any]]:
        """Handle auth service response"""
        pass


class BaseAuthService(ABC):
    """Base implementation for auth services"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    @abstractmethod
    async def _validate_credentials(self, email: str, password: str) -> bool:
        """Validate user credentials"""
        pass
    
    @abstractmethod
    async def _create_user_session(self, user_id: str) -> str:
        """Create user session"""
        pass


class BaseSessionManager(ABC):
    """Base implementation for session management"""
    
    @abstractmethod
    async def _store_session(self, session: SessionInfo) -> bool:
        """Store session data"""
        pass
    
    @abstractmethod
    async def _retrieve_session(self, session_id: str) -> Optional[SessionInfo]:
        """Retrieve session data"""
        pass


class BasePermissionManager(ABC):
    """Base implementation for permission management"""
    
    @abstractmethod
    async def _store_permission(self, permission: UserPermission) -> bool:
        """Store user permission"""
        pass
    
    @abstractmethod
    async def _remove_permission(self, user_id: str, permission: str) -> bool:
        """Remove user permission"""
        pass


# Type aliases for common use cases
AuthClient = AuthClientProtocol
AuthService = AuthServiceProtocol
SessionManager = SessionManagerProtocol
PermissionManager = PermissionManagerProtocol
AuditLogger = AuditLoggerProtocol
TokenValidator = TokenValidatorProtocol
PasswordManager = PasswordManagerProtocol
OAuthProvider = OAuthProviderProtocol
RateLimiter = RateLimiterProtocol

# Dependency injection types
class AuthDependencies:
    """Container for auth service dependencies"""
    
    def __init__(
        self,
        auth_client: AuthClient,
        session_manager: SessionManager,
        permission_manager: PermissionManager,
        audit_logger: AuditLogger,
        token_validator: TokenValidator,
        password_manager: PasswordManager
    ):
        self._init_core_components(auth_client, session_manager, permission_manager)
        self._init_utility_components(audit_logger, token_validator, password_manager)

    def _init_core_components(self, auth_client: AuthClient, session_manager: SessionManager, permission_manager: PermissionManager) -> None:
        """Initialize core auth components."""
        self.auth_client = auth_client
        self.session_manager = session_manager
        self.permission_manager = permission_manager

    def _init_utility_components(self, audit_logger: AuditLogger, token_validator: TokenValidator, password_manager: PasswordManager) -> None:
        """Initialize utility auth components."""
        self.audit_logger = audit_logger
        self.token_validator = token_validator
        self.password_manager = password_manager