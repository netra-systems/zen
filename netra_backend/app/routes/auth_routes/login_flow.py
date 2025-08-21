"""
OAuth Login Flow Logic
"""
from fastapi import Request
from fastapi.responses import RedirectResponse
from netra_backend.app.clients.auth_client import auth_client
from netra_backend.app.oauth_validation import (
    validate_oauth_credentials, handle_pr_proxy_redirect, 
    build_redirect_uri, validate_redirect_uri, log_oauth_initiation
)
from netra_backend.app.token_management import execute_oauth_redirect


def perform_login_validations(oauth_config, request: Request):
    """Perform all OAuth login validations and return any errors."""
    if error_response := validate_oauth_credentials(oauth_config):
        return error_response
    if proxy_response := handle_pr_proxy_redirect(oauth_config, request):
        return proxy_response
    return None


async def complete_oauth_login(request: Request, oauth_config) -> RedirectResponse:
    """Complete OAuth login after validations pass."""
    redirect_uri = build_redirect_uri(request)
    if error_response := validate_redirect_uri(redirect_uri, oauth_config):
        return error_response
    log_oauth_initiation(oauth_config, redirect_uri)
    return await execute_oauth_redirect(request, redirect_uri)


def _determine_auth_service_url(environment) -> str:
    """Determine auth service URL based on environment."""
    import os
    if environment.value == 'staging':
        return 'https://auth.staging.netrasystems.ai'
    elif environment.value == 'production':
        return 'https://auth.netrasystems.ai'
    return os.getenv('AUTH_SERVICE_URL', 'http://localhost:8081')

def _build_auth_redirect_url(auth_service_url: str, provider: str) -> str:
    """Build base redirect URL to auth service."""
    return f"{auth_service_url}/auth/login?provider={provider}"

def _add_return_url_param(redirect_url: str, return_url: str) -> str:
    """Add return_url parameter if provided."""
    if return_url:
        return redirect_url + f"&return_url={return_url}"
    return redirect_url

def _build_complete_redirect_url(request: Request) -> str:
    """Build complete redirect URL with all parameters."""
    environment = auth_client.detect_environment()
    auth_service_url = _determine_auth_service_url(environment)
    provider = request.query_params.get('provider', 'google')
    redirect_url = _build_auth_redirect_url(auth_service_url, provider)
    return_url = request.query_params.get('return_url')
    return _add_return_url_param(redirect_url, return_url)

async def handle_login_request(request: Request):
    """Redirect to auth service for OAuth login."""
    from fastapi.responses import RedirectResponse
    redirect_url = _build_complete_redirect_url(request)
    return RedirectResponse(url=redirect_url, status_code=302)