"""Authentication module - Clean modular architecture.

Exports the authentication module's public interface with clear boundaries.
All components follow the 300-line file limit and 8-line function limit.

Module Architecture:
- auth_service.py: Main FastAPI application (184 lines)
- auth_token_service.py: JWT token management  
- oauth_session_manager.py: OAuth state management
- oauth_utils.py: OAuth token exchange and user info
- url_validators.py: Secure URL validation
- auth_response_builders.py: Response building utilities
- auth_interfaces.py: Interface definitions and boundaries

Public Interface:
- AuthTokenService: JWT token generation and validation
- OAuthSessionManager: OAuth state and session management
- FastAPI app: Main authentication service application
"""

# Core Services
from .auth_token_service import AuthTokenService, UserInfo
from .oauth_session_manager import OAuthSessionManager, StateData
from .auth_service import app as auth_app

# Utility Services  
from .oauth_utils import (
    exchange_code_for_tokens, 
    get_user_info_from_google,
    build_google_oauth_url,
    OAuthTokenData
)
from .url_validators import (
    validate_and_get_return_url,
    get_oauth_redirect_uri,
    get_auth_service_url
)
from .auth_response_builders import (
    build_oauth_callback_response,
    build_token_response,
    clear_auth_cookies,
    build_service_status
)

# Interfaces
from .auth_interfaces import (
    TokenServiceInterface,
    SessionManagerInterface, 
    URLValidatorInterface,
    OAuthUtilsInterface,
    ResponseBuilderInterface,
    AuthModuleBoundary
)

# Public exports
__all__ = [
    # Core Services
    "AuthTokenService",
    "OAuthSessionManager", 
    "auth_app",
    
    # Data Types
    "UserInfo",
    "StateData", 
    "OAuthTokenData",
    
    # OAuth Utilities
    "exchange_code_for_tokens",
    "get_user_info_from_google",
    "build_google_oauth_url",
    
    # URL Validation
    "validate_and_get_return_url",
    "get_oauth_redirect_uri",
    "get_auth_service_url",
    
    # Response Building
    "build_oauth_callback_response",
    "build_token_response", 
    "clear_auth_cookies",
    "build_service_status",
    
    # Interfaces
    "TokenServiceInterface",
    "SessionManagerInterface",
    "URLValidatorInterface", 
    "OAuthUtilsInterface",
    "ResponseBuilderInterface",
    "AuthModuleBoundary"
]