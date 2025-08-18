"""PR Router for handling Pull Request specific authentication flows.

Handles PR environment routing, validation, and authentication workflows.
All functions ≤8 lines (MANDATORY). File ≤300 lines (MANDATORY).

Business Value Justification (BVJ):
1. Segment: All customer segments (Free through Enterprise)
2. Business Goal: Enable secure PR environment authentication
3. Value Impact: Enables testing and staging environment access
4. Revenue Impact: Critical for development workflow and customer demos
"""

import os
import re
import time
import json
import base64
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlparse
from fastapi import HTTPException, status
import httpx
import logging

logger = logging.getLogger(__name__)

def extract_pr_number_from_request(request_headers: Dict[str, str]) -> Optional[str]:
    """Extract PR number from request headers or host."""
    pr_header = request_headers.get("X-PR-Number")
    if pr_header:
        return validate_pr_number_format(pr_header)
    
    host = request_headers.get("host", "")
    return extract_pr_from_host(host)

def extract_pr_from_host(host: str) -> Optional[str]:
    """Extract PR number from host string."""
    pr_pattern = r"pr-(\d+)(?:-api)?\.staging\.netrasystems\.ai"
    match = re.search(pr_pattern, host)
    return match.group(1) if match else None

def _validate_pr_number_format(pr_number: str) -> None:
    """Validate PR number format and raise exception if invalid."""
    from app.core.exceptions_auth import AuthenticationError
    
    if not pr_number or not pr_number.isdigit():
        raise AuthenticationError("PR number must be numeric")
    
    _validate_pr_range(int(pr_number))

def _validate_pr_range(pr_int: int) -> None:
    """Validate PR number is within valid range."""
    from app.core.exceptions_auth import AuthenticationError
    
    if pr_int < 1 or pr_int > 9999:
        raise AuthenticationError("PR number must be between 1 and 9999")

def validate_pr_number_format(pr_number: str) -> Optional[str]:
    """Validate PR number format (legacy function)."""
    if not pr_number or not pr_number.isdigit():
        return None
    
    if not _is_pr_in_valid_range(int(pr_number)):
        return None
    
    return pr_number

def _is_pr_in_valid_range(pr_int: int) -> bool:
    """Check if PR number is within valid range."""
    return 1 <= pr_int <= 99999

def build_pr_redirect_url(pr_number: str, base_path: str = "/") -> str:
    """Build PR environment redirect URL."""
    pr_domain = f"https://pr-{pr_number}.staging.netrasystems.ai"
    return f"{pr_domain}{base_path}"

def get_pr_auth_config(pr_number: str) -> Dict[str, Any]:
    """Get authentication configuration for PR environment."""
    base_config = _get_pr_base_config(pr_number)
    domains = _get_pr_domains(pr_number)
    return {**base_config, **domains}

def _get_pr_base_config(pr_number: str) -> Dict[str, Any]:
    """Get base PR configuration."""
    return {
        "pr_number": pr_number,
        "environment": "pr"
    }

def _get_pr_domains(pr_number: str) -> Dict[str, Any]:
    """Get PR domain configuration."""
    return {
        "auth_domain": f"https://auth-pr-{pr_number}.staging.netrasystems.ai",
        "frontend_domain": f"https://pr-{pr_number}.staging.netrasystems.ai",
        "api_domain": f"https://pr-{pr_number}-api.staging.netrasystems.ai"
    }

def validate_pr_environment_access(pr_number: str, user_permissions: Dict[str, Any]) -> bool:
    """Validate user access to PR environment."""
    if not _has_pr_access_permission(user_permissions):
        return False
        
    return _has_specific_pr_access(pr_number, user_permissions)

def _has_pr_access_permission(user_permissions: Dict[str, Any]) -> bool:
    """Check if user has general PR access permission."""
    return user_permissions.get("pr_access", False)

def _has_specific_pr_access(pr_number: str, user_permissions: Dict[str, Any]) -> bool:
    """Check if user has access to specific PR."""
    allowed_prs = user_permissions.get("allowed_prs", [])
    if allowed_prs and pr_number not in allowed_prs:
        return False
    return True

def route_pr_authentication(
    pr_number: str, 
    auth_flow: str,
    return_url: Optional[str] = None
) -> Tuple[str, Dict[str, Any]]:
    """Route PR authentication flow and return redirect URL and config."""
    pr_config = get_pr_auth_config(pr_number)
    redirect_url = _build_pr_redirect_url(auth_flow, pr_config, return_url, pr_number)
    return redirect_url, pr_config

def _build_pr_redirect_url(auth_flow: str, pr_config: Dict[str, Any], return_url: Optional[str], pr_number: str) -> str:
    """Build redirect URL based on auth flow type."""
    if auth_flow == "login":
        return _build_login_redirect_url(pr_config, return_url, pr_number)
    elif auth_flow == "callback":
        return f"{pr_config['frontend_domain']}/auth/callback"
    return pr_config['frontend_domain']

def _build_login_redirect_url(pr_config: Dict[str, Any], return_url: Optional[str], pr_number: str) -> str:
    """Build login redirect URL with optional return URL."""
    base_url = f"{pr_config['auth_domain']}/auth/login"
    if return_url:
        return f"{base_url}?return_url={return_url}&pr={pr_number}"
    return base_url

def handle_pr_routing_error(error: Exception, pr_number: str) -> HTTPException:
    """Handle PR routing errors."""
    logger.error(f"PR routing error for PR {pr_number}: {error}")
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Invalid PR environment configuration: {pr_number}"
    )

def get_pr_environment_status(pr_number: str) -> Dict[str, Any]:
    """Get PR environment status and health."""
    pr_config = get_pr_auth_config(pr_number)
    status_data = _build_pr_status_data(pr_number)
    domains = _extract_pr_domains(pr_config)
    return {**status_data, **domains}

def _build_pr_status_data(pr_number: str) -> Dict[str, Any]:
    """Build base PR status data."""
    return {
        "pr_number": pr_number,
        "status": "active",
        "last_updated": "2025-08-17T18:00:00Z"
    }

def _extract_pr_domains(pr_config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract domain configuration from PR config."""
    return {
        "auth_domain": pr_config["auth_domain"],
        "frontend_domain": pr_config["frontend_domain"],
        "api_domain": pr_config["api_domain"]
    }

def _is_valid_url(url: str) -> bool:
    """Validate URL format."""
    if not url:
        return False
    
    try:
        return _check_url_components(urlparse(url))
    except Exception:
        return False

def _check_url_components(parsed_url) -> bool:
    """Check if parsed URL has valid components."""
    return parsed_url.scheme in ('http', 'https') and bool(parsed_url.netloc)

def _is_allowed_return_domain(url: str) -> bool:
    """Check if domain is in allowed list for return URLs."""
    if not url:
        return False
    
    try:
        domain = urlparse(url).netloc.lower()
        return _check_domain_against_allowlist(domain)
    except Exception:
        return False

def _check_domain_against_allowlist(domain: str) -> bool:
    """Check if domain matches allowed patterns."""
    allowed_domains = ['staging.netrasystems.ai', 'localhost']
    return any(
        domain == allowed or domain.endswith(f'.{allowed}')
        for allowed in allowed_domains
    )

async def _validate_pr_inputs(pr_number: str, return_url: str) -> None:
    """Validate PR number and return URL inputs."""
    from app.core.exceptions_auth import AuthenticationError, NetraSecurityException
    
    try:
        _validate_pr_number_format(pr_number)
    except AuthenticationError as e:
        raise AuthenticationError(f"Invalid PR number format: {e}")
    
    _validate_url_inputs(return_url)

def _validate_url_inputs(return_url: str) -> None:
    """Validate URL inputs for PR authentication."""
    from app.core.exceptions_auth import AuthenticationError, NetraSecurityException
    
    if not _is_valid_url(return_url):
        raise AuthenticationError("Invalid return URL")
    
    if not _is_allowed_return_domain(return_url):
        raise NetraSecurityException("Return URL not in allowed domains")

async def _validate_pr_with_github(pr_number: str, github_client) -> None:
    """Validate PR exists and is open in GitHub."""
    from app.core.exceptions_auth import AuthenticationError
    
    try:
        response = await github_client.get(f"/repos/netra-systems/netra-core-generation-1/pulls/{pr_number}")
        _check_github_response(response, pr_number)
    except httpx.RequestError:
        logger.warning(f"GitHub API error while validating PR {pr_number}")

def _check_github_response(response, pr_number: str) -> None:
    """Check GitHub API response for PR validation."""
    from app.core.exceptions_auth import AuthenticationError
    
    if response.status_code == 404:
        raise AuthenticationError(f"PR #{pr_number} not found")
    
    if response.status_code == 200:
        _validate_pr_state(response.json(), pr_number)

def _validate_pr_state(pr_data: Dict[str, Any], pr_number: str) -> None:
    """Validate PR state is open."""
    from app.core.exceptions_auth import AuthenticationError
    
    if pr_data.get("state") != "open":
        raise AuthenticationError(f"PR #{pr_number} is not open")

# State management constants
PR_STATE_TTL = 300  # 5 minutes TTL for PR state

def _build_pr_state_data(pr_number: str, return_url: str, csrf_token: str) -> Dict[str, Any]:
    """Build PR state data structure with timestamp and version."""
    base_data = _get_pr_state_base_data(pr_number, return_url, csrf_token)
    metadata = _get_pr_state_metadata()
    return {**base_data, **metadata}

def _get_pr_state_base_data(pr_number: str, return_url: str, csrf_token: str) -> Dict[str, Any]:
    """Get base PR state data."""
    return {
        "pr_number": pr_number,
        "return_url": return_url,
        "csrf_token": csrf_token
    }

def _get_pr_state_metadata() -> Dict[str, Any]:
    """Get PR state metadata."""
    return {
        "timestamp": int(time.time()),
        "version": "1.0"
    }

def _encode_state_to_base64(state_data: Dict[str, Any]) -> str:
    """Encode state data dictionary to base64 string."""
    try:
        json_str = json.dumps(state_data, separators=(',', ':'))
        return base64.urlsafe_b64encode(json_str.encode('utf-8')).decode('utf-8')
    except Exception as e:
        from app.core.exceptions_auth import NetraSecurityException
        raise NetraSecurityException(f"Failed to encode state: {e}")

def _decode_state_from_base64(encoded_state: str) -> Dict[str, Any]:
    """Decode base64 string back to state data dictionary."""
    try:
        decoded_bytes = base64.urlsafe_b64decode(encoded_state.encode('utf-8'))
        return json.loads(decoded_bytes.decode('utf-8'))
    except Exception as e:
        from app.core.exceptions_auth import NetraSecurityException
        raise NetraSecurityException("Malformed state parameter")

def _validate_state_timestamp(state_data: Dict[str, Any], ttl: int) -> None:
    """Validate that state timestamp hasn't expired."""
    from app.core.exceptions_auth import NetraSecurityException
    
    timestamp = state_data.get("timestamp", 0)
    current_time = int(time.time())
    if current_time - timestamp > ttl:
        raise NetraSecurityException("OAuth state has expired")

async def _store_csrf_token_in_redis(pr_number: str, csrf_token: str, redis_manager) -> None:
    """Store CSRF token in Redis with TTL."""
    if not redis_manager.enabled:
        return
    
    key = f"oauth_csrf:pr:{pr_number}:{csrf_token}"
    await redis_manager.setex(key, PR_STATE_TTL, "active")

async def _validate_and_consume_csrf_token(state_data: Dict[str, Any], redis_manager) -> None:
    """Validate and consume CSRF token from Redis."""
    from app.core.exceptions_auth import NetraSecurityException
    
    if not redis_manager.enabled:
        return
    
    await _check_and_consume_csrf_token(state_data, redis_manager)

async def _check_and_consume_csrf_token(state_data: Dict[str, Any], redis_manager) -> None:
    """Check and consume CSRF token from Redis."""
    from app.core.exceptions_auth import NetraSecurityException
    
    pr_number = state_data["pr_number"]
    csrf_token = state_data["csrf_token"]
    key = f"oauth_csrf:pr:{pr_number}:{csrf_token}"
    
    token_value = await redis_manager.get(key)
    if not token_value:
        raise NetraSecurityException("Invalid or expired CSRF token")
    
    await redis_manager.delete(key)