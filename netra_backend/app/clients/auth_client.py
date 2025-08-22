"""
🔴 CRITICAL: Auth Service Client - HTTP Client to EXTERNAL Auth Service

This client connects to an EXTERNAL auth microservice via HTTP.
The auth service runs SEPARATELY from the main backend.

ARCHITECTURE:
- Auth Service: Runs at AUTH_SERVICE_URL (e.g., http://localhost:8001)
- This Client: Makes HTTP calls to auth service endpoints
- Main Backend: Uses this client for ALL auth operations

⚠️ IMPORTANT:
- This is NOT implementing auth - it's calling an external service
- The auth service is a SEPARATE application (see app/auth/auth_service.py)
- ALL auth logic lives in the auth service, NOT here

See: app/auth_integration/CRITICAL_AUTH_ARCHITECTURE.md
"""

# Import core functionality
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
from netra_backend.app.clients.auth_client_core import AuthServiceClient, auth_client

# Re-export for backward compatibility
__all__ = [
    'AuthServiceClient',
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