"""
🔴 DEPRECATED: Auth Service Client - USE UNIFIED AUTH INTERFACE INSTEAD

DEPRECATION NOTICE: This module is DEPRECATED.
All authentication now uses auth_service unified interface.

MIGRATION:
OLD: from netra_backend.app.clients.auth_client import auth_client
NEW: from auth_service.auth_core.unified_auth_interface import get_unified_auth

Business Value: Eliminates duplicate auth logic, prevents security inconsistencies
Single Source of Truth: auth_service is now the ONLY authentication provider
"""

# DEPRECATED: Import shim for backward compatibility
from netra_backend.app.clients.auth_client_unified_shim import (
    AuthClientUnifiedShim,
    auth_client_unified_shim
)

# DEPRECATED: Keep old imports for backward compatibility
from netra_backend.app.clients.auth_client_cache import (
    AuthCircuitBreakerManager,
    AuthServiceSettings, 
    AuthTokenCache,
    CachedToken,
)
from netra_backend.app.clients.auth_client_config import (
    Environment,
    EnvironmentDetector,
    OAuthConfig,
    OAuthConfigGenerator,
)

# DEPRECATED: Alias for backward compatibility
AuthServiceClient = AuthClientUnifiedShim
AuthClient = AuthClientUnifiedShim
auth_client = auth_client_unified_shim

# DEPRECATED: Re-export for backward compatibility
__all__ = [
    'AuthServiceClient',
    'AuthClient', 
    'auth_client',
    'Environment',
    'OAuthConfig',
    'EnvironmentDetector', 
    'OAuthConfigGenerator',
    'CachedToken',
    'AuthTokenCache',
    'AuthCircuitBreakerManager',
    'AuthServiceSettings'
]