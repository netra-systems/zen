"""OAuth utilities for token exchange and user info retrieval.

Handles Google OAuth token exchange and user information fetching.
All functions ≤8 lines (MANDATORY). File ≤300 lines (MANDATORY).
"""

from typing import Dict, Any, TypedDict, Tuple
from urllib.parse import urlencode
from fastapi import HTTPException
import httpx

from app.logging_config import central_logger
from app.auth.url_validators import get_oauth_redirect_uri

logger = central_logger.get_logger(__name__)


class OAuthTokenData(TypedDict):
    """OAuth token response structure."""
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str


class UserInfo(TypedDict):
    """Google OAuth user information structure."""
    id: str
    email: str
    name: str
    picture: str


def build_oauth_params(oauth_config, state_id: str) -> Dict[str, str]:
    """Build OAuth authorization parameters."""
    return {
        "client_id": oauth_config.client_id, "redirect_uri": get_oauth_redirect_uri(),
        "response_type": "code", "scope": "openid email profile",
        "state": state_id, "access_type": "online"
    }


def build_google_oauth_url(oauth_config, state_id: str) -> str:
    """Build Google OAuth authorization URL."""
    params = build_oauth_params(oauth_config, state_id)
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


def build_token_exchange_data(code: str, oauth_config) -> Dict[str, str]:
    """Build token exchange request data."""
    return {
        "code": code, "client_id": oauth_config.client_id,
        "client_secret": oauth_config.client_secret, "redirect_uri": get_oauth_redirect_uri(),
        "grant_type": "authorization_code"
    }


async def exchange_code_for_tokens(code: str, oauth_config) -> OAuthTokenData:
    """Exchange authorization code for access tokens."""
    token_url = "https://oauth2.googleapis.com/token"
    data = build_token_exchange_data(code, oauth_config)
    return await perform_token_exchange_request(token_url, data)


def validate_token_exchange_response(response: httpx.Response) -> OAuthTokenData:
    """Validate and process token exchange response."""
    if response.status_code != 200:
        logger.error(f"Token exchange failed: {response.text}")
        raise HTTPException(status_code=400, detail="OAuth token exchange failed")
    return response.json()


def handle_token_exchange_timeout() -> None:
    """Handle token exchange timeout errors."""
    logger.error("Token exchange request timed out")
    raise HTTPException(status_code=503, detail="OAuth service temporarily unavailable")


def create_exchange_timeout() -> httpx.Timeout:
    """Create timeout for token exchange requests."""
    return httpx.Timeout(10.0, connect=5.0)


async def perform_token_exchange_request(url: str, data: Dict[str, str]) -> OAuthTokenData:
    """Perform HTTP request for token exchange with timeout and security."""
    timeout = create_exchange_timeout()
    async with httpx.AsyncClient(timeout=timeout) as client:
        return await _execute_token_exchange(client, url, data)

async def _execute_token_exchange(client: httpx.AsyncClient, url: str, data: Dict[str, str]) -> OAuthTokenData:
    """Execute token exchange request with error handling."""
    try:
        response = await client.post(url, data=data)
        return validate_token_exchange_response(response)
    except httpx.TimeoutException:
        handle_token_exchange_timeout()


def build_user_info_request_config(access_token: str) -> Tuple[str, Dict[str, str], httpx.Timeout]:
    """Build user info request configuration."""
    user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    timeout = httpx.Timeout(10.0, connect=5.0)
    return user_info_url, headers, timeout


def handle_user_info_response(response: httpx.Response) -> UserInfo:
    """Handle and validate user info response."""
    if response.status_code != 200:
        logger.error(f"Failed to get user info: {response.text}")
        raise HTTPException(status_code=400, detail="Failed to retrieve user information")
    return response.json()


def handle_user_info_timeout() -> None:
    """Handle user info request timeout."""
    logger.error("User info request timed out")
    raise HTTPException(status_code=503, detail="User info service temporarily unavailable")


async def get_user_info_from_google(access_token: str) -> UserInfo:
    """Get user information from Google API with timeout and security."""
    url, headers, timeout = build_user_info_request_config(access_token)
    async with httpx.AsyncClient(timeout=timeout) as client:
        return await _execute_user_info_request(client, url, headers)

async def _execute_user_info_request(client: httpx.AsyncClient, url: str, headers: Dict[str, str]) -> UserInfo:
    """Execute user info request with error handling."""
    try:
        response = await client.get(url, headers=headers)
        return handle_user_info_response(response)
    except httpx.TimeoutException:
        handle_user_info_timeout()