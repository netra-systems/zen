"""
Auth Configuration Handler
"""
from typing import Optional
from fastapi import Request
from netra_backend.app.core.config import get_config
from netra_backend.app.clients.auth_client import auth_client
from netra_backend.app.schemas.auth_types import AuthConfigResponse, AuthEndpoints


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
        "login": f"{base_url}/api/auth/login", "logout": f"{base_url}/api/auth/logout",
        "callback": f"{base_url}/api/auth/callback", "token": f"{base_url}/api/auth/token",
        "user": f"{base_url}/api/users/me"
    }


def get_dev_login_endpoint(base_url: str, oauth_config) -> Optional[str]:
    """Get dev login endpoint if allowed."""
    if oauth_config.allow_dev_login:
        return f"{base_url}/api/auth/dev_login"
    return None


def _get_development_mode() -> bool:
    """Check if running in development mode."""
    return auth_client.detect_environment().value == "development"

def build_base_auth_response(oauth_config, endpoints: AuthEndpoints) -> AuthConfigResponse:
    """Build base authentication configuration response."""
    return AuthConfigResponse(
        development_mode=_get_development_mode(),
        google_client_id=oauth_config.client_id, endpoints=endpoints,
        authorized_javascript_origins=oauth_config.javascript_origins,
        authorized_redirect_uris=oauth_config.redirect_uris
    )


def add_pr_configuration(response: AuthConfigResponse, oauth_config) -> None:
    """Add PR-specific configuration to auth response."""
    config = get_config()
    is_pr_environment = bool(config.pr_number)
    if is_pr_environment:
        response.pr_number = config.pr_number
        response.use_proxy = oauth_config.use_proxy
        response.proxy_url = oauth_config.proxy_url


def determine_environment_urls() -> tuple[str, str]:
    """Determine auth service and frontend URLs based on environment."""
    environment = auth_client.detect_environment()
    if environment.value == 'staging':
        return 'https://auth.staging.netrasystems.ai', 'https://app.staging.netrasystems.ai'
    elif environment.value == 'production':
        return 'https://auth.netrasystems.ai', 'https://netrasystems.ai'
    config = get_config()
    return config.auth_service_url, 'http://localhost:3000'


def _get_dev_login_url(auth_service_url: str, oauth_config) -> Optional[str]:
    """Get dev login URL if allowed."""
    return f"{auth_service_url}/auth/dev_login" if oauth_config.allow_dev_login else None

def build_environment_endpoints(auth_service_url: str, frontend_url: str, oauth_config) -> AuthEndpoints:
    """Build authentication endpoints for the current environment."""
    dev_login = _get_dev_login_url(auth_service_url, oauth_config)
    return AuthEndpoints(
        login=f"{auth_service_url}/auth/login", logout=f"{auth_service_url}/auth/logout",
        callback=f"{frontend_url}/auth/callback", token=f"{auth_service_url}/auth/token",
        user=f"{auth_service_url}/auth/me", dev_login=dev_login
    )


def _get_google_client_id(oauth_config) -> str:
    """Get Google client ID from config or environment."""
    config = get_config()
    return oauth_config.client_id or config.google_client_id or ''

def _create_config_dict(environment, endpoints: AuthEndpoints, oauth_config) -> dict:
    """Create authentication configuration dictionary."""
    return {
        "development_mode": environment.value == "development",
        "google_client_id": _get_google_client_id(oauth_config), "endpoints": endpoints,
        "authorized_javascript_origins": oauth_config.javascript_origins,
        "authorized_redirect_uris": oauth_config.redirect_uris
    }

def _build_auth_config_params(endpoints: AuthEndpoints, oauth_config) -> dict:
    """Build authentication config parameters."""
    environment = auth_client.detect_environment()
    return _create_config_dict(environment, endpoints, oauth_config)

def create_auth_response(endpoints: AuthEndpoints, oauth_config) -> AuthConfigResponse:
    """Create authentication configuration response."""
    config_params = _build_auth_config_params(endpoints, oauth_config)
    return AuthConfigResponse(**config_params)


def _get_fallback_urls() -> tuple[str, str]:
    """Get fallback URLs for auth service and frontend."""
    return 'https://auth.staging.netrasystems.ai', 'https://app.staging.netrasystems.ai'

def build_fallback_endpoints() -> AuthEndpoints:
    """Build fallback authentication endpoints."""
    auth_service_url, frontend_url = _get_fallback_urls()
    return AuthEndpoints(
        login=f"{auth_service_url}/auth/login", logout=f"{auth_service_url}/auth/logout",
        callback=f"{frontend_url}/auth/callback", token=f"{auth_service_url}/auth/token",
        user=f"{auth_service_url}/auth/me", dev_login=None
    )


def _create_fallback_config(fallback_endpoints: AuthEndpoints, frontend_url: str) -> AuthConfigResponse:
    """Create fallback configuration with endpoints."""
    config = get_config()
    return AuthConfigResponse(
        development_mode=False, google_client_id=config.google_client_id or '',
        endpoints=fallback_endpoints, authorized_javascript_origins=[frontend_url],
        authorized_redirect_uris=[f"{frontend_url}/auth/callback"]
    )

def create_fallback_response() -> AuthConfigResponse:
    """Create fallback authentication configuration response."""
    fallback_endpoints = build_fallback_endpoints()
    frontend_url = 'https://app.staging.netrasystems.ai'
    return _create_fallback_config(fallback_endpoints, frontend_url)


def log_auth_config_error(error: Exception) -> None:
    """Log authentication configuration error."""
    from netra_backend.app.logging_config import central_logger
    logger = central_logger.get_logger(__name__)
    logger.error(f"Failed to build auth config response: {str(error)}", exc_info=True)


def _build_auth_config_with_urls(auth_service_url: str, frontend_url: str) -> AuthConfigResponse:
    """Build auth config with determined URLs."""
    oauth_config = auth_client.get_oauth_config()
    endpoints = build_environment_endpoints(auth_service_url, frontend_url, oauth_config)
    response = create_auth_response(endpoints, oauth_config)
    add_pr_configuration(response, oauth_config)
    return response

def build_auth_config_response(request: Request) -> AuthConfigResponse:
    """Build complete authentication configuration response."""
    try:
        auth_service_url, frontend_url = determine_environment_urls()
        return _build_auth_config_with_urls(auth_service_url, frontend_url)
    except Exception as e:
        log_auth_config_error(e)
        return create_fallback_response()