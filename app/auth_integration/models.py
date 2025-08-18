"""
Shared Auth Models - Single Source of Truth
Consolidated authentication models for Netra Apex platform.

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise)
- Business Goal: Eliminate $5K MRR loss from auth inconsistencies 
- Value Impact: 5-10% conversion improvement
- Revenue Impact: +$5K MRR recovered

Architecture:
- 300-line module limit enforced
- 8-line function limit enforced
- Single source of truth for all auth models
- Strong typing with Pydantic validation
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
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
    """Universal login request model - handles all auth types"""
    email: EmailStr
    password: Optional[str] = None
    provider: AuthProvider = AuthProvider.LOCAL
    oauth_token: Optional[str] = None
    
    @validator('password')
    def validate_password_required(cls, v, values):
        """Validate password required for local auth"""
        if values.get('provider') == AuthProvider.LOCAL and not v:
            raise ValueError('Password required for local auth')
        return v


class LoginResponse(BaseModel):
    """Universal login response with tokens and user data"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: int = Field(description="Seconds until expiration")
    user: Optional[Dict[str, Any]] = None


class TokenData(BaseModel):
    """Token payload data structure"""
    email: Optional[str] = None
    user_id: Optional[str] = None
    permissions: List[str] = []
    expires_at: Optional[datetime] = None


class TokenRequest(BaseModel):
    """Token validation/refresh request"""
    token: str
    token_type: TokenType = TokenType.ACCESS


class TokenResponse(BaseModel):
    """Token validation response with user data"""
    valid: bool
    user_id: Optional[str] = None
    email: Optional[str] = None
    permissions: List[str] = []
    expires_at: Optional[datetime] = None


class RefreshRequest(BaseModel):
    """Token refresh request"""
    refresh_token: str


class ServiceTokenRequest(BaseModel):
    """Service-to-service authentication request"""
    service_id: str
    service_secret: str
    requested_permissions: List[str] = []


class ServiceTokenResponse(BaseModel):
    """Service token response"""
    token: str
    expires_in: int
    service_name: str


class HealthResponse(BaseModel):
    """Universal health check response"""
    status: str
    service: str = "auth-service"
    version: str = "1.0.0"
    environment: str = "development"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    redis_connected: Optional[bool] = None
    database_connected: Optional[bool] = None


class SessionInfo(BaseModel):
    """User session information"""
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


class AuthError(BaseModel):
    """Standardized auth error response"""
    error: str
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AuditLog(BaseModel):
    """Auth audit log entry"""
    event_id: str
    event_type: str
    user_id: Optional[str] = None
    service_id: Optional[str] = None
    ip_address: str
    user_agent: Optional[str] = None
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# OAuth-specific models
class GoogleUser(BaseModel):
    """Google OAuth user information"""
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None


class DevUser(BaseModel):
    """Development environment user"""
    email: str = "dev@example.com"
    full_name: str = "Dev User"
    picture: Optional[str] = None
    is_dev: bool = True


class DevLoginRequest(BaseModel):
    """Development login request"""
    email: str


class AuthEndpoints(BaseModel):
    """Auth service endpoint configuration"""
    login: str
    logout: str
    callback: str
    token: str
    user: str
    dev_login: Optional[str] = None


class AuthConfigResponse(BaseModel):
    """Auth configuration response"""
    google_client_id: str
    endpoints: AuthEndpoints
    development_mode: bool
    user: Optional[Dict[str, Any]] = None
    authorized_javascript_origins: List[str]
    authorized_redirect_uris: List[str]
    pr_number: Optional[str] = None
    use_proxy: Optional[bool] = False
    proxy_url: Optional[str] = None


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


# Backward compatibility aliases
HealthCheck = HealthResponse
UserToken = TokenData
AuthRequest = LoginRequest
AuthResponse = LoginResponse
