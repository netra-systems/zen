"""URL validation utilities for secure OAuth redirects.

Security-focused URL validation to prevent attacks.
All functions ≤8 lines (MANDATORY). File ≤300 lines (MANDATORY).
"""

from typing import Dict, List
from urllib.parse import unquote
from fastapi import HTTPException

from app.auth.environment_config import auth_env_config


def validate_and_get_return_url(return_url: str) -> str:
    """Validate and sanitize return URL."""
    if not return_url:
        return get_default_return_url()
    decoded_url = unquote(return_url)
    validate_return_url_security(decoded_url)
    return decoded_url


def get_default_return_url() -> str:
    """Get default return URL based on environment."""
    config = auth_env_config.get_frontend_config()
    if auth_env_config.is_pr_environment:
        return f"https://pr-{auth_env_config.pr_number}.staging.netrasystems.ai"
    return config["javascript_origins"][0]


def check_malicious_url_patterns(url: str) -> None:
    """Check for malicious URL patterns."""
    malicious_patterns = ["javascript:", "data:", "vbscript:", "file:", "ftp:"]
    if any(url.lower().startswith(pattern) for pattern in malicious_patterns):
        raise HTTPException(status_code=400, detail="Malicious URL scheme detected")


def validate_url_length(url: str) -> None:
    """Validate URL length to prevent DoS attacks."""
    if len(url) > 2048:
        raise HTTPException(status_code=400, detail="URL too long")


def validate_allowed_origins(url: str) -> None:
    """Validate URL against allowed origins."""
    config = auth_env_config.get_oauth_config()
    allowed_origins = config.javascript_origins
    if not any(url.startswith(origin) for origin in allowed_origins):
        raise HTTPException(status_code=400, detail="Invalid return URL origin")


def validate_return_url_security(url: str) -> None:
    """Validate return URL for security with enhanced checks."""
    check_malicious_url_patterns(url)
    validate_url_length(url)
    validate_allowed_origins(url)


def get_environment_redirect_map() -> Dict[str, str]:
    """Get environment to redirect URI mapping."""
    return {
        "development": "http://localhost:8001/auth/callback",
        "staging": "https://auth.staging.netrasystems.ai/auth/callback",
        "production": "https://auth.netrasystems.ai/auth/callback"
    }


def get_oauth_redirect_uri() -> str:
    """Get OAuth redirect URI based on environment."""
    redirect_map = get_environment_redirect_map()
    env_value = auth_env_config.environment.value
    return redirect_map.get(env_value, "http://localhost:8001/auth/callback")


def get_auth_service_url_map() -> Dict[str, str]:
    """Get auth service URL mapping."""
    return {
        "development": "http://localhost:8001",
        "staging": "https://auth.staging.netrasystems.ai",
        "production": "https://auth.netrasystems.ai"
    }


def get_auth_service_url() -> str:
    """Get auth service URL based on environment."""
    url_map = get_auth_service_url_map()
    env_value = auth_env_config.environment.value
    return url_map.get(env_value, "http://localhost:8001")