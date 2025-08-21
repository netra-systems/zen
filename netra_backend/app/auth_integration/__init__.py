"""
🔴 SHARED AUTH SERVICE - Single Source of Truth
Consolidated authentication models and dependency injection.

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise)
- Business Goal: Single auth source eliminates $5K MRR loss
- Value Impact: 5-10% conversion improvement
- Revenue Impact: +$5K MRR recovered

This module provides:
- Consolidated auth models (LoginRequest, LoginResponse, etc.)
- Dependency functions for authentication/authorization
- Type-safe interfaces and protocols
- Validation utilities
"""

# Import from parent dependencies.py file for backward compatibility
# NOTE: Conditional import to avoid circular dependency with schemas
try:
    from netra_backend.app.dependencies import DbDep, get_db_dependency, get_llm_manager
except ImportError:
    # Handle circular import during schema initialization
    DbDep = None
    get_db_dependency = None
    get_llm_manager = None

# Auth dependency functions
from netra_backend.app.auth_integration.auth import (
    ActiveUserDep,
    DeveloperDep,
    AdminDep,
    ActiveUserWsDep,
    require_permission,
    get_current_user,
    get_current_active_user,
    get_current_user_optional,
    require_admin,
    require_developer,
    get_password_hash,
    verify_password,
    create_access_token,
    validate_token_jwt
)

# 🔴 CONSOLIDATED AUTH MODELS - Single Source of Truth
from netra_backend.app.schemas.auth_types import (
    # Core auth models
    LoginRequest,
    LoginResponse,
    TokenData,
    TokenRequest,
    TokenResponse,
    RefreshRequest,
    HealthResponse,
    
    # Service auth models
    ServiceTokenRequest,
    ServiceTokenResponse,
    
    # Session and audit models
    SessionInfo,
    UserPermission,
    AuthError,
    AuditLog,
    
    # OAuth models
    GoogleUser,
    DevUser,
    DevLoginRequest,
    AuthEndpoints,
    AuthConfigResponse,
    AuthConfig,
    
    # Enums
    TokenType,
    AuthProvider,
    
    # Backward compatibility aliases
    HealthCheck,
    UserToken,
    AuthRequest,
    AuthResponse
)

# Validation utilities
from netra_backend.app.auth_integration.validators import (
    validate_email_format,
    validate_password_strength,
    validate_token_format,
    validate_service_id,
    validate_permission_format,
    AuthValidationError
)

# Type-safe interfaces
from netra_backend.app.auth_integration.interfaces import (
    AuthClientProtocol,
    AuthServiceProtocol,
    SessionManagerProtocol,
    PermissionManagerProtocol,
    AuditLoggerProtocol,
    TokenValidatorProtocol,
    PasswordManagerProtocol,
    OAuthProviderProtocol,
    RateLimiterProtocol,
    AuthDependencies
)

__all__ = [
    # Auth dependencies
    'ActiveUserDep',
    'DeveloperDep',
    'AdminDep',
    'ActiveUserWsDep',
    'require_permission',
    'get_current_user',
    'get_current_active_user',
    'get_current_user_optional',
    'require_admin',
    'require_developer',
    'get_password_hash',
    'verify_password',
    'create_access_token',
    'validate_token_jwt',
    
    # 🔴 CONSOLIDATED MODELS - Use these instead of duplicates
    'LoginRequest',
    'LoginResponse', 
    'TokenData',
    'TokenRequest',
    'TokenResponse',
    'RefreshRequest',
    'HealthResponse',
    'ServiceTokenRequest',
    'ServiceTokenResponse',
    'SessionInfo',
    'UserPermission',
    'AuthError',
    'AuditLog',
    'GoogleUser',
    'DevUser',
    'DevLoginRequest',
    'AuthEndpoints',
    'AuthConfigResponse',
    'AuthConfig',
    'TokenType',
    'AuthProvider',
    
    # Backward compatibility
    'HealthCheck',
    'UserToken',
    'AuthRequest',
    'AuthResponse',
    
    # Validation
    'validate_email_format',
    'validate_password_strength',
    'validate_token_format',
    'validate_service_id',
    'validate_permission_format',
    'AuthValidationError',
    
    # Interfaces
    'AuthClientProtocol',
    'AuthServiceProtocol',
    'SessionManagerProtocol',
    'PermissionManagerProtocol',
    'AuditLoggerProtocol',
    'TokenValidatorProtocol',
    'PasswordManagerProtocol',
    'OAuthProviderProtocol',
    'RateLimiterProtocol',
    'AuthDependencies'
]

# Add dependency items if available
if DbDep is not None:
    __all__.extend(['DbDep', 'get_db_dependency', 'get_llm_manager'])