"""Authentication response builders for OAuth flows.

Secure response building with proper cookie handling and security headers.
All functions ≤8 lines (MANDATORY). File ≤300 lines (MANDATORY).
"""

from typing import Dict, Any
from fastapi import Response
from fastapi.responses import RedirectResponse, JSONResponse

from app.auth.oauth_session_manager import StateData
from app.auth.oauth_utils import UserInfo


def build_standard_callback_response(return_url: str, jwt_token: str) -> RedirectResponse:
    """Build standard callback response."""
    redirect_url = f"{return_url}/auth/complete"
    response = RedirectResponse(url=redirect_url)
    set_auth_cookies(response, jwt_token)
    return response


def build_oauth_callback_response(state_data: StateData, jwt_token: str, user_info: UserInfo):
    """Build OAuth callback response with redirect."""
    return_url = state_data["return_url"]
    if state_data.get("pr_number"):
        return build_pr_environment_response(return_url, jwt_token, user_info, state_data["pr_number"])
    return build_standard_callback_response(return_url, jwt_token)


def build_pr_environment_response(return_url: str, jwt_token: str, user_info: UserInfo, pr_number: str):
    """Build response for PR environment with token transfer."""
    redirect_url = f"{return_url}/auth/complete?token={jwt_token}"
    response = RedirectResponse(url=redirect_url)
    set_pr_auth_cookies(response, jwt_token, pr_number)
    return response


def set_standard_security_headers(response: Response) -> None:
    """Set standard security headers."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"


def set_auth_cookies(response: Response, jwt_token: str) -> None:
    """Set secure authentication cookies with enhanced security."""
    response.set_cookie(
        key="netra_auth_token", value=jwt_token, max_age=3600,
        secure=True, httponly=True, samesite="strict", path="/",
        domain=None  # Restrict to exact domain for security
    )
    set_standard_security_headers(response)


def set_pr_security_headers(response: Response) -> None:
    """Set security headers for PR environment."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'"


def set_pr_auth_cookies(response: Response, jwt_token: str, pr_number: str) -> None:
    """Set authentication cookies for PR environment with enhanced security."""
    response.set_cookie(
        key="netra_auth_token", value=jwt_token, max_age=3600,
        secure=True, httponly=True, samesite="none", path="/",
        domain=f"pr-{pr_number}.staging.netrasystems.ai"
    )
    set_pr_security_headers(response)


def build_token_response(jwt_token: str, user_info: UserInfo) -> Dict[str, Any]:
    """Build token exchange response."""
    return {"access_token": jwt_token, "token_type": "Bearer", "expires_in": 3600, "user_info": user_info}


def clear_auth_cookies(response: Response) -> None:
    """Clear authentication cookies."""
    response.delete_cookie("netra_auth_token")
    response.delete_cookie("netra_auth_token", domain=".staging.netrasystems.ai")


def get_service_status_data(redis_status: bool) -> Dict[str, Any]:
    """Get basic service status data."""
    from app.auth.environment_config import auth_env_config
    return {
        "status": "healthy", "environment": auth_env_config.environment.value,
        "is_pr_environment": auth_env_config.is_pr_environment,
        "pr_number": auth_env_config.pr_number, "redis_connected": redis_status
    }

def build_service_status(redis_status: bool) -> Dict[str, Any]:
    """Build service status response."""
    from datetime import datetime, timezone
    status_data = get_service_status_data(redis_status)
    status_data["timestamp"] = datetime.now(timezone.utc).isoformat()
    return status_data


def add_auth_urls(config: Dict[str, Any], auth_service_url: str) -> None:
    """Add authentication URLs to config."""
    config.update({
        "auth_service_url": auth_service_url,
        "login_url": f"{auth_service_url}/auth/login",
        "logout_url": f"{auth_service_url}/auth/logout"
    })