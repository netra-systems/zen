"""
Shared Auth Models - DEPRECATED - USE app.schemas.auth_types INSTEAD

This module is now a compatibility wrapper that imports from the canonical source.
All new code should import directly from app.schemas.auth_types.

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise)
- Business Goal: Eliminate $5K MRR loss from auth inconsistencies 
- Value Impact: 5-10% conversion improvement
- Revenue Impact: +$5K MRR recovered
"""

# Import all types from canonical source
from netra_backend.app.schemas.auth_types import (
    AuditLog,
    AuthConfig,
    AuthConfigResponse,
    AuthEndpoints,
    AuthError,
    AuthProvider,
    DevLoginRequest,
    DevUser,
    GoogleUser,
    HealthResponse,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    ServiceTokenRequest,
    ServiceTokenResponse,
    SessionInfo,
    Token,
    TokenClaims,
    TokenData,
    TokenPayload,
    TokenRequest,
    TokenResponse,
    TokenType,
    UserPermission,
)

# Backward compatibility aliases - All types are imported from canonical source above
HealthCheck = AuthConfigResponse  
UserToken = TokenData
AuthRequest = LoginRequest
AuthResponse = LoginResponse

# Re-export for backward compatibility
__all__ = [
    "TokenType",
    "AuthProvider", 
    "Token",
    "TokenPayload",
    "TokenData",
    "TokenClaims",
    "TokenRequest",
    "TokenResponse",
    "RefreshRequest",
    "LoginRequest",
    "LoginResponse",
    "ServiceTokenRequest",
    "ServiceTokenResponse",
    "AuthEndpoints",
    "AuthConfigResponse",
    "AuthConfig",
    "SessionInfo",
    "UserPermission",
    "AuthError",
    "DevUser",
    "DevLoginRequest", 
    "GoogleUser",
    "HealthResponse",
    "AuditLog",
    "HealthCheck",
    "UserToken",
    "AuthRequest",
    "AuthResponse"
]
