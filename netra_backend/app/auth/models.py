"""Auth Models Module - SSOT Compatibility Layer

This module provides backward compatibility for auth model imports while
following SSOT principles. Uses backend's own User model and provides
compatibility aliases for auth-related functionality.

SSOT COMPLIANCE:
- The actual User model is defined in models_user.py (SSOT location)
- This module provides backward compatibility for existing imports
- Service boundaries maintained: netra_backend owns User database model
- Auth service handles authentication logic, not data models

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Fix Issue #1319 auth_service import regression
- Value Impact: Prevents ModuleNotFoundError in GCP deployment
- Strategic Impact: Maintains Golden Path functionality
"""

# Import SQLAlchemy Base for database model compatibility
from netra_backend.app.db.base import Base

# Import SSOT User model from backend (NOT from auth_service)
from netra_backend.app.db.models_user import User, Secret, ToolUsageLog

# Create compatibility aliases for auth service models
# These reference the backend's User model instead of auth_service models
AuthUser = User  # Alias for compatibility - backend owns user data
AuthSession = dict  # Placeholder - sessions handled by auth service
AuthAuditLog = dict  # Placeholder - audit logs handled by auth service
PasswordResetToken = dict  # Placeholder - password resets handled by auth service

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

# Backward compatibility aliases
HealthCheck = AuthConfigResponse  
UserToken = TokenData
AuthRequest = LoginRequest
AuthResponse = LoginResponse

# Re-export all functionality
__all__ = [
    'Base',
    # SSOT User models from backend (compatibility aliases)
    'AuthUser',
    'AuthSession',
    'AuthAuditLog',
    'PasswordResetToken',
    # Backend user models
    'User',
    'Secret',
    'ToolUsageLog',
    # Pydantic models from auth integration
    'AuditLog',
    'AuthConfig',
    'AuthConfigResponse',
    'AuthEndpoints',
    'AuthError',
    'AuthProvider',
    'DevLoginRequest',
    'DevUser',
    'GoogleUser',
    'HealthResponse',
    'LoginRequest',
    'LoginResponse',
    'RefreshRequest',
    'ServiceTokenRequest',
    'ServiceTokenResponse',
    'SessionInfo',
    'Token',
    'TokenClaims',
    'TokenData',
    'TokenPayload',
    'TokenRequest',
    'TokenResponse',
    'TokenType',
    'UserPermission',
    'HealthCheck',
    'UserToken',
    'AuthRequest',
    'AuthResponse',
]