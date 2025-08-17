"""
Auth Configuration Handler
"""
import os
from typing import Optional
from fastapi import Request
from app.clients.auth_client import auth_client
from app.schemas.Auth import AuthConfigResponse, AuthEndpoints


def normalize_base_url(request: Request) -> str:
    """Normalize base URL for HTTPS in production environments."""
    base_url = str(request.base_url).rstrip('/')
    if auth_client.detect_environment().value in ["staging", "production"]:
        base_url = base_url.replace("http://", "https://")
    return base_url


def build_auth_endpoints(base_url: str, oauth_config) -> AuthEndpoints:
    """Build authentication endpoints configuration."""
    base_endpoints = get_base_endpoints(base_url)
    dev_login_endpoint = get_dev_login_endpoint(base_url, oauth_config)
    return AuthEndpoints(**base_endpoints, dev_login=dev_login_endpoint)


def get_base_endpoints(base_url: str) -> dict:
    """Get base authentication endpoints."""
    return {
        "login": f"{base_url}/api/auth/login",
        "logout": f"{base_url}/api/auth/logout",
        "callback": f"{base_url}/api/auth/callback",
        "token": f"{base_url}/api/auth/token",
        "user": f"{base_url}/api/users/me"
    }


def get_dev_login_endpoint(base_url: str, oauth_config) -> Optional[str]:
    """Get dev login endpoint if allowed."""
    if oauth_config.allow_dev_login:
        return f"{base_url}/api/auth/dev_login"
    return None


def build_base_auth_response(oauth_config, endpoints: AuthEndpoints) -> AuthConfigResponse:
    """Build base authentication configuration response."""
    return AuthConfigResponse(
        development_mode=auth_client.detect_environment().value == "development",
        google_client_id=oauth_config.client_id,
        endpoints=endpoints,
        authorized_javascript_origins=oauth_config.javascript_origins,
        authorized_redirect_uris=oauth_config.redirect_uris
    )


def add_pr_configuration(response: AuthConfigResponse, oauth_config) -> None:
    """Add PR-specific configuration to auth response."""
    is_pr_environment = bool(os.getenv("PR_NUMBER"))
    if is_pr_environment:
        response.pr_number = os.getenv("PR_NUMBER")
        response.use_proxy = oauth_config.use_proxy
        response.proxy_url = oauth_config.proxy_url


def build_auth_config_response(request: Request) -> AuthConfigResponse:
    """Build complete authentication configuration response."""
    base_url = normalize_base_url(request)
    oauth_config = auth_client.get_oauth_config()
    endpoints = build_auth_endpoints(base_url, oauth_config)
    response = build_base_auth_response(oauth_config, endpoints)
    add_pr_configuration(response, oauth_config)
    return response