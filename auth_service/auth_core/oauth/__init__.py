"""OAuth providers and configuration for auth service.

This module provides comprehensive OAuth support including:
- OAuth configuration management (OAuthConfig)
- OAuth state management for CSRF protection (OAuthStateManager)
- Google OAuth provider integration (GoogleOAuthProvider)
- OAuth database models and repository operations

All OAuth operations should use these SSOT components.
"""

# Import all OAuth components for easy access
from auth_service.auth_core.oauth.google_oauth import GoogleOAuthProvider, GoogleOAuthError
from auth_service.auth_core.oauth.oauth_config import OAuthConfig, OAuthProviderConfig, OAuthConfigError
from auth_service.auth_core.oauth.oauth_state_manager import OAuthStateManager, OAuthStateData, OAuthStateValidation, OAuthStateError

__all__ = [
    # OAuth Providers
    "GoogleOAuthProvider",
    
    # Configuration
    "OAuthConfig", 
    "OAuthProviderConfig",
    
    # State Management
    "OAuthStateManager",
    "OAuthStateData",
    "OAuthStateValidation",
    
    # Exceptions
    "GoogleOAuthError",
    "OAuthConfigError", 
    "OAuthStateError"
]