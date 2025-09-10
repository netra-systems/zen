"""Auth Models Module - Compatibility Layer

This module provides backward compatibility for auth model imports.
Imports SQLAlchemy models from the auth service (SSOT) and Pydantic models 
from auth integration to provide a unified import interface.

The SQLAlchemy models (AuthUser, AuthSession, AuthAuditLog, PasswordResetToken)
are imported directly from the auth service, maintaining SSOT principles
while providing test compatibility through enhanced initialization.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Maintain test compatibility while following SSOT principles
- Value Impact: Ensures existing tests continue to work without breaking changes
- Strategic Impact: Maintains system stability during module consolidation
"""

# Import SQLAlchemy Base for database model compatibility
from netra_backend.app.db.base import Base

# Import SQLAlchemy models from auth service (SSOT)
from auth_service.auth_core.database.models import (
    AuthUser,
    AuthSession, 
    AuthAuditLog,
    PasswordResetToken
)

from netra_backend.app.auth_integration.models import (
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
    # Backward compatibility aliases
    HealthCheck,
    UserToken,
    AuthRequest,
    AuthResponse,
)

# Re-export all functionality
__all__ = [
    'Base',
    # SQLAlchemy models from auth service
    'AuthUser',
    'AuthSession', 
    'AuthAuditLog',
    'PasswordResetToken',
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