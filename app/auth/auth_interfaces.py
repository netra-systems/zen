"""Authentication module interface definitions.

Defines clear boundaries and interfaces for auth module components.
All functions ≤8 lines (MANDATORY). File ≤300 lines (MANDATORY).
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Protocol, TypedDict
from fastapi import Response


class UserInfo(TypedDict):
    """User information structure."""
    id: str
    email: str
    name: str
    picture: Optional[str]


class OAuthTokenData(TypedDict):
    """OAuth token response structure."""
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str]


class StateData(TypedDict):
    """OAuth state data structure."""
    csrf_token: str
    return_url: str
    timestamp: int
    pr_number: Optional[str]


class TokenServiceInterface(Protocol):
    """Interface for JWT token services."""
    
    def generate_jwt(self, user_info: UserInfo) -> str:
        """Generate JWT token with user claims."""
        ...
    
    def validate_jwt(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate JWT token and return claims."""
        ...


class SessionManagerInterface(Protocol):
    """Interface for OAuth session managers."""
    
    async def create_oauth_state(self, pr_number: Optional[str], return_url: str) -> str:
        """Create secure OAuth state parameter."""
        ...
    
    async def validate_and_consume_state(self, state_id: str) -> StateData:
        """Validate OAuth state and consume it."""
        ...


class URLValidatorInterface(Protocol):
    """Interface for URL validation services."""
    
    def validate_and_get_return_url(self, return_url: Optional[str]) -> str:
        """Validate and sanitize return URL."""
        ...
    
    def get_oauth_redirect_uri(self) -> str:
        """Get OAuth redirect URI based on environment."""
        ...


class OAuthUtilsInterface(Protocol):
    """Interface for OAuth utility services."""
    
    async def exchange_code_for_tokens(self, code: str, oauth_config: Any) -> OAuthTokenData:
        """Exchange authorization code for access tokens."""
        ...
    
    async def get_user_info_from_google(self, access_token: str) -> UserInfo:
        """Get user information from Google API."""
        ...
    
    def build_google_oauth_url(self, oauth_config: Any, state_id: str) -> str:
        """Build Google OAuth authorization URL."""
        ...


class ResponseBuilderInterface(Protocol):
    """Interface for response building services."""
    
    def build_oauth_callback_response(self, state_data: StateData, jwt_token: str, user_info: UserInfo) -> Response:
        """Build OAuth callback response with redirect."""
        ...
    
    def build_token_response(self, jwt_token: str, user_info: UserInfo) -> Dict[str, Any]:
        """Build token exchange response."""
        ...
    
    def clear_auth_cookies(self, response: Response) -> None:
        """Clear authentication cookies."""
        ...


class AuthModuleBoundary:
    """Defines clear boundaries for auth module components."""
    
    # Core Services
    TOKEN_SERVICE = "auth_token_service"
    SESSION_MANAGER = "oauth_session_manager"
    
    # Utility Services
    URL_VALIDATORS = "url_validators"
    OAUTH_UTILS = "oauth_utils"
    RESPONSE_BUILDERS = "auth_response_builders"
    
    # Main Application
    AUTH_SERVICE = "auth_service"
    
    @staticmethod
    def get_service_dependencies() -> Dict[str, list]:
        """Get service dependency mapping."""
        return {
            AuthModuleBoundary.AUTH_SERVICE: [
                AuthModuleBoundary.TOKEN_SERVICE,
                AuthModuleBoundary.SESSION_MANAGER,
                AuthModuleBoundary.URL_VALIDATORS,
                AuthModuleBoundary.OAUTH_UTILS,
                AuthModuleBoundary.RESPONSE_BUILDERS
            ],
            AuthModuleBoundary.RESPONSE_BUILDERS: [],
            AuthModuleBoundary.URL_VALIDATORS: [],
            AuthModuleBoundary.OAUTH_UTILS: [AuthModuleBoundary.URL_VALIDATORS],
            AuthModuleBoundary.SESSION_MANAGER: [],
            AuthModuleBoundary.TOKEN_SERVICE: []
        }
    
    @staticmethod
    def validate_dependency_order(dependencies: Dict[str, list]) -> bool:
        """Validate that dependencies form a proper DAG."""
        visited = set()
        rec_stack = set()
        
        def has_cycle(service: str) -> bool:
            visited.add(service)
            rec_stack.add(service)
            
            for dep in dependencies.get(service, []):
                if dep not in visited and has_cycle(dep):
                    return True
                elif dep in rec_stack:
                    return True
            
            rec_stack.remove(service)
            return False
        
        for service in dependencies:
            if service not in visited and has_cycle(service):
                return False
        return True