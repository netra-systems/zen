"""PR-specific OAuth routing for staging environments."""

import base64
import json
import secrets
import time
from typing import Dict, Optional, Any, Tuple
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import HTTPException
from fastapi.responses import RedirectResponse

from app.logging_config import central_logger as logger
from app.redis_manager import RedisManager
from app.core.exceptions_auth import AuthenticationError, NetraSecurityException
from app.schemas.Auth import AuthConfigResponse


# Constants for security configuration
PR_STATE_TTL = 300  # 5 minutes in seconds
CSRF_TOKEN_LENGTH = 32
MAX_PR_NUMBER = 9999
MIN_PR_NUMBER = 1


class PRAuthRouter:
    """Handles PR-specific OAuth routing for dynamic staging environments."""
    
    def __init__(self, redis_manager: RedisManager) -> None:
        self.redis = redis_manager
        self.state_ttl = PR_STATE_TTL
        self.github_client = self._init_github_client()
    
    def _init_github_client(self) -> Optional[httpx.AsyncClient]:
        """Initialize GitHub client for PR validation."""
        try:
            return httpx.AsyncClient(base_url="https://api.github.com")
        except Exception as e:
            logger.warning(f"GitHub client initialization failed: {e}")
            return None


async def route_pr_auth(pr_number: str, return_url: str, 
                       router: PRAuthRouter) -> RedirectResponse:
    """Route PR-specific OAuth authentication requests."""
    await _validate_pr_inputs(pr_number, return_url)
    await validate_pr_environment(pr_number, router)
    csrf_token = _generate_secure_csrf_token()
    state = await encode_pr_state(pr_number, return_url, csrf_token, router)
    auth_url = _build_oauth_authorization_url(state)
    await _log_pr_auth_initiation(pr_number, return_url)
    return RedirectResponse(url=auth_url)


async def validate_pr_environment(pr_number: str, router: PRAuthRouter) -> None:
    """Validate that PR environment exists and is active."""
    _validate_pr_number_format(pr_number)
    if router.github_client:
        await _validate_pr_with_github(pr_number, router.github_client)
    await _validate_pr_in_cache(pr_number, router.redis)
    logger.info(f"PR #{pr_number} validation successful")


async def encode_pr_state(pr_number: str, return_url: str, csrf_token: str,
                         router: PRAuthRouter) -> str:
    """Encode PR information in OAuth state parameter."""
    state_data = _build_pr_state_data(pr_number, return_url, csrf_token)
    encoded_state = _encode_state_to_base64(state_data)
    await _store_csrf_token_in_redis(pr_number, csrf_token, router.redis)
    return encoded_state


async def decode_pr_state(state: str, router: PRAuthRouter) -> Dict[str, Any]:
    """Decode and validate PR information from OAuth state."""
    try:
        state_data = _decode_state_from_base64(state)
        _validate_state_timestamp(state_data, router.state_ttl)
        await _validate_and_consume_csrf_token(state_data, router.redis)
        return state_data
    except Exception as e:
        logger.error(f"State decode failed: {e}")
        raise NetraSecurityException(f"Invalid OAuth state: {e}")


def get_pr_redirect_url(pr_number: str) -> str:
    """Get the redirect URL for a PR environment."""
    _validate_pr_number_format(pr_number)
    base_domain = "staging.netrasystems.ai"
    pr_subdomain = f"pr-{pr_number}"
    redirect_url = f"https://{pr_subdomain}.{base_domain}"
    return redirect_url


# Helper functions (each ≤8 lines)

async def _validate_pr_inputs(pr_number: str, return_url: str) -> None:
    """Validate PR authentication input parameters."""
    if not pr_number or not pr_number.isdigit():
        raise AuthenticationError("Invalid PR number format")
    if not return_url or not _is_valid_url(return_url):
        raise AuthenticationError("Invalid return URL")
    if not _is_allowed_return_domain(return_url):
        raise NetraSecurityException("Return URL not in allowed domains")


def _validate_pr_number_format(pr_number: str) -> None:
    """Validate PR number is in correct format and range."""
    if not pr_number or not pr_number.isdigit():
        raise AuthenticationError("PR number must be numeric")
    pr_num = int(pr_number)
    if not (MIN_PR_NUMBER <= pr_num <= MAX_PR_NUMBER):
        raise AuthenticationError(f"PR number must be between {MIN_PR_NUMBER}-{MAX_PR_NUMBER}")


async def _validate_pr_with_github(pr_number: str, github_client: httpx.AsyncClient) -> None:
    """Validate PR exists and is open via GitHub API."""
    try:
        repo_path = "netra-systems/netra-apex"  # Update with actual repo
        response = await github_client.get(f"/repos/{repo_path}/pulls/{pr_number}")
        if response.status_code == 404:
            raise AuthenticationError(f"PR #{pr_number} not found")
        pr_data = response.json()
        if pr_data.get("state") != "open":
            raise AuthenticationError(f"PR #{pr_number} is not open")
    except httpx.RequestError as e:
        logger.warning(f"GitHub validation failed: {e}")


async def _validate_pr_in_cache(pr_number: str, redis: RedisManager) -> None:
    """Check if PR is in active PR cache."""
    if not redis.enabled:
        return
    cache_key = f"active_pr:{pr_number}"
    is_active = await redis.get(cache_key)
    if not is_active:
        await redis.setex(cache_key, 3600, "active")  # Cache for 1 hour


def _generate_secure_csrf_token() -> str:
    """Generate cryptographically secure CSRF token."""
    return secrets.token_urlsafe(CSRF_TOKEN_LENGTH)


def _build_pr_state_data(pr_number: str, return_url: str, csrf_token: str) -> Dict[str, Any]:
    """Build state data dictionary for PR OAuth flow."""
    return {
        "pr_number": pr_number,
        "return_url": return_url,
        "csrf_token": csrf_token,
        "timestamp": int(time.time()),
        "version": "1.0"
    }


def _encode_state_to_base64(state_data: Dict[str, Any]) -> str:
    """Encode state data to URL-safe base64."""
    state_json = json.dumps(state_data, separators=(',', ':'))
    state_bytes = state_json.encode('utf-8')
    return base64.urlsafe_b64encode(state_bytes).decode('utf-8')


async def _store_csrf_token_in_redis(pr_number: str, csrf_token: str, 
                                   redis: RedisManager) -> None:
    """Store CSRF token in Redis with TTL for validation."""
    if not redis.enabled:
        logger.warning("Redis disabled - CSRF validation will fail")
        return
    csrf_key = f"oauth_csrf:pr:{pr_number}:{csrf_token}"
    await redis.setex(csrf_key, PR_STATE_TTL, "valid")


def _decode_state_from_base64(state: str) -> Dict[str, Any]:
    """Decode state data from URL-safe base64."""
    try:
        state_bytes = base64.urlsafe_b64decode(state.encode('utf-8'))
        state_json = state_bytes.decode('utf-8')
        return json.loads(state_json)
    except (ValueError, json.JSONDecodeError) as e:
        raise NetraSecurityException(f"Malformed state parameter: {e}")


def _validate_state_timestamp(state_data: Dict[str, Any], ttl: int) -> None:
    """Validate that state timestamp is within TTL."""
    timestamp = state_data.get("timestamp", 0)
    current_time = int(time.time())
    if current_time - timestamp > ttl:
        raise NetraSecurityException("OAuth state has expired")


async def _validate_and_consume_csrf_token(state_data: Dict[str, Any], 
                                         redis: RedisManager) -> None:
    """Validate CSRF token and mark as consumed."""
    if not redis.enabled:
        logger.warning("Redis disabled - skipping CSRF validation")
        return
    pr_number = state_data.get("pr_number")
    csrf_token = state_data.get("csrf_token")
    csrf_key = f"oauth_csrf:pr:{pr_number}:{csrf_token}"
    is_valid = await redis.get(csrf_key)
    if not is_valid:
        raise NetraSecurityException("Invalid or expired CSRF token")
    await redis.delete(csrf_key)  # Single-use token


def _build_oauth_authorization_url(state: str) -> str:
    """Build Google OAuth authorization URL with state."""
    params = {
        "client_id": _get_oauth_client_id(),
        "redirect_uri": "https://auth.staging.netrasystems.ai/auth/callback",
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online"
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


async def _log_pr_auth_initiation(pr_number: str, return_url: str) -> None:
    """Log PR OAuth authentication initiation."""
    logger.info(
        f"PR OAuth initiated",
        extra={
            "pr_number": pr_number,
            "return_url": return_url,
            "event": "pr_auth_initiated"
        }
    )


def _is_valid_url(url: str) -> bool:
    """Check if URL has valid format."""
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except Exception:
        return False


def _is_allowed_return_domain(url: str) -> bool:
    """Check if return URL domain is in allowed list."""
    allowed_domains = [
        "staging.netrasystems.ai",
        "localhost"
    ]
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Handle PR subdomains
        if domain.endswith(".staging.netrasystems.ai"):
            return True
        return any(domain == allowed or domain.endswith(f".{allowed}") 
                  for allowed in allowed_domains)
    except Exception:
        return False


def _get_oauth_client_id() -> str:
    """Get OAuth client ID for current environment."""
    import os
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID_STAGING", "")
    if not client_id:
        raise AuthenticationError("OAuth client ID not configured")
    return client_id


# Public interface for integration with existing oauth_proxy
def create_pr_auth_router(redis_manager: RedisManager) -> PRAuthRouter:
    """Factory function to create PR auth router instance."""
    return PRAuthRouter(redis_manager)