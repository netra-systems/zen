"""
Auth Service Pydantic Models - Type safety and validation
Single Source of Truth for auth data structures
"""
from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime, UTC
from enum import Enum

class TokenType(str, Enum):
    """Token type enumeration"""
    ACCESS = "access"
    REFRESH = "refresh"
    SERVICE = "service"

class AuthProvider(str, Enum):
    """Authentication provider types"""
    LOCAL = "local"
    GOOGLE = "google"
    GITHUB = "github"
    API_KEY = "api_key"

class LoginRequest(BaseModel):
    """User login request model"""
    email: EmailStr
    password: Optional[str] = None
    provider: AuthProvider = AuthProvider.LOCAL
    oauth_token: Optional[str] = None
    
    @model_validator(mode='after')
    def validate_password_for_local(self):
        if self.provider == AuthProvider.LOCAL and not self.password:
            raise ValueError('Password required for local auth')
        return self

class LoginResponse(BaseModel):
    """Login response with tokens"""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = Field(description="Seconds until expiration")
    user: Dict[str, Any]

class TokenRequest(BaseModel):
    """Token validation/refresh request"""
    token: str
    token_type: TokenType = TokenType.ACCESS

class TokenResponse(BaseModel):
    """Token validation response"""
    valid: bool
    user_id: Optional[str] = None
    email: Optional[str] = None
    permissions: List[str] = []
    expires_at: Optional[datetime] = None

class RefreshRequest(BaseModel):
    """Token refresh request"""
    refresh_token: str

class ServiceTokenRequest(BaseModel):
    """Service-to-service auth request"""
    service_id: str
    service_secret: str
    requested_permissions: List[str] = []

class ServiceTokenResponse(BaseModel):
    """Service token response"""
    token: str
    expires_in: int
    service_name: str

class SessionInfo(BaseModel):
    """Session information model"""
    session_id: str
    user_id: str
    created_at: datetime
    last_activity: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Dict[str, Any] = {}

class UserPermission(BaseModel):
    """User permission model"""
    permission_id: str
    resource: str
    action: str
    granted_at: datetime
    granted_by: Optional[str] = None

class AuthConfig(BaseModel):
    """Auth service configuration"""
    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    session_expire_hours: int = 24
    max_sessions_per_user: int = 5
    enable_rate_limiting: bool = True
    rate_limit_requests: int = 10
    rate_limit_window_seconds: int = 60

class AuthError(BaseModel):
    """Auth error response"""
    error: str
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str = "auth-service"
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    redis_connected: bool
    database_connected: bool

class AuditLog(BaseModel):
    """Audit log entry for auth events"""
    event_id: str
    event_type: str
    user_id: Optional[str] = None
    service_id: Optional[str] = None
    ip_address: str
    user_agent: Optional[str] = None
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

class AuthEndpoints(BaseModel):
    """Auth service endpoint configuration"""
    login: str
    logout: str
    callback: str
    token: str
    user: str
    dev_login: Optional[str] = None
    validate_token: Optional[str] = None
    refresh: Optional[str] = None
    health: Optional[str] = None

class AuthConfigResponse(BaseModel):
    """Auth configuration response for frontend integration"""
    google_client_id: str
    endpoints: AuthEndpoints
    development_mode: bool
    user: Optional[Dict[str, Any]] = None
    authorized_javascript_origins: List[str]
    authorized_redirect_uris: List[str]
    pr_number: Optional[str] = None
    use_proxy: Optional[bool] = False
    proxy_url: Optional[str] = None

class PasswordResetRequest(BaseModel):
    """Password reset request model"""
    email: EmailStr

class PasswordResetResponse(BaseModel):
    """Password reset response model"""
    success: bool
    message: str
    reset_token: Optional[str] = None  # For testing only

class PasswordResetConfirm(BaseModel):
    """Password reset confirmation model"""
    reset_token: str
    new_password: str = Field(min_length=8, max_length=128)
    
class PasswordResetConfirmResponse(BaseModel):
    """Password reset confirmation response"""
    success: bool
    message: str