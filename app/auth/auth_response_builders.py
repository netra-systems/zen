"""Auth response builders for consistent API responses.

Builds standardized responses for auth endpoints.
All functions ≤8 lines (MANDATORY). File ≤300 lines (MANDATORY).

Business Value Justification (BVJ):
1. Segment: All customer segments (Free through Enterprise)
2. Business Goal: Consistent auth API responses
3. Value Impact: Improves frontend integration and user experience
4. Revenue Impact: Enables smooth authentication workflows
"""

from typing import Dict, Any
from fastapi.responses import RedirectResponse, JSONResponse
import logging

logger = logging.getLogger(__name__)

def build_oauth_callback_response(
    jwt_token: str, 
    user_info: Dict[str, Any], 
    state_data: Dict[str, Any]
) -> RedirectResponse:
    """Build OAuth callback redirect response."""
    return_url = state_data.get("return_url", "http://localhost:3000")
    
    # Add token to URL params for frontend to capture
    separator = "&" if "?" in return_url else "?"
    redirect_url = f"{return_url}{separator}token={jwt_token}"
    
    response = RedirectResponse(url=redirect_url)
    set_auth_cookies(response, jwt_token, user_info)
    
    return response

def set_auth_cookies(
    response: RedirectResponse, 
    token: str, 
    user_info: Dict[str, Any]
):
    """Set authentication cookies on response."""
    # Set secure HTTP-only token cookie
    response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=86400  # 24 hours
    )
    
    # Set user info cookie (not HTTP-only for frontend access)
    response.set_cookie(
        key="user_info",
        value=f"{user_info.get('email', '')}|{user_info.get('name', '')}",
        secure=True,
        samesite="lax",
        max_age=86400
    )

def clear_auth_cookies(response: JSONResponse):
    """Clear authentication cookies."""
    response.set_cookie(
        key="auth_token",
        value="",
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=0
    )
    
    response.set_cookie(
        key="user_info",
        value="",
        secure=True,
        samesite="lax",
        max_age=0
    )

def build_service_status(redis_connected: bool) -> Dict[str, Any]:
    """Build auth service status response."""
    return {
        "status": "healthy",
        "service": "netra-auth-service",
        "redis_connected": redis_connected,
        "version": "1.0.0"
    }

def add_auth_urls(config: Dict[str, Any], base_url: str):
    """Add auth URLs to frontend configuration."""
    config["login_url"] = f"{base_url}/auth/login"
    config["logout_url"] = f"{base_url}/auth/logout"
    config["callback_url"] = f"{base_url}/auth/callback"
    config["token_url"] = f"{base_url}/auth/token"
    config["status_url"] = f"{base_url}/auth/status"

def build_error_response(error_code: str, message: str) -> Dict[str, Any]:
    """Build standardized error response."""
    return {
        "error": error_code,
        "message": message,
        "service": "netra-auth-service"
    }

def build_token_response(token: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
    """Build token exchange response."""
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_info": user_info,
        "expires_in": 86400  # 24 hours
    }