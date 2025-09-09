"""
Auth service models module.
"""

# Import all models to make them available for external imports
from auth_service.auth_core.models.auth_models import (
    User,
    TokenType,
    AuthProvider,
    LoginRequest,
    LoginResponse,
    TokenRequest,
    TokenResponse,
    RefreshRequest,
    ServiceTokenRequest,
    ServiceTokenResponse,
    SessionInfo,
    UserPermission,
    AuthConfig,
    AuthError,
    AuthException,
    HealthResponse,
    AuditLog,
    AuthEndpoints,
    AuthConfigResponse,
    PasswordResetRequest,
    PasswordResetResponse,
    PasswordResetConfirm,
    PasswordResetConfirmResponse,
    OAuthState,
    OAuthCallbackRequest,
)

from auth_service.auth_core.models.oauth_user import OAuthUser

# Export all models for external use
__all__ = [
    "User",
    "OAuthUser",
    "TokenType",
    "AuthProvider",
    "LoginRequest",
    "LoginResponse",
    "TokenRequest",
    "TokenResponse",
    "RefreshRequest",
    "ServiceTokenRequest",
    "ServiceTokenResponse",
    "SessionInfo",
    "UserPermission",
    "AuthConfig",
    "AuthError",
    "AuthException",
    "HealthResponse",
    "AuditLog",
    "AuthEndpoints",
    "AuthConfigResponse",
    "PasswordResetRequest",
    "PasswordResetResponse",
    "PasswordResetConfirm",
    "PasswordResetConfirmResponse",
    "OAuthState",
    "OAuthCallbackRequest",
]