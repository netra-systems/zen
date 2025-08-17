"""
OAuth Login Flow Logic
"""
from fastapi import Request
from fastapi.responses import RedirectResponse
from app.clients.auth_client import auth_client
from .oauth_validation import (
    validate_oauth_credentials, handle_pr_proxy_redirect, 
    build_redirect_uri, validate_redirect_uri, log_oauth_initiation
)
from .token_management import execute_oauth_redirect


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


async def handle_login_request(request: Request):
    """Redirect to auth service for OAuth login."""
    import os
    from fastapi.responses import RedirectResponse
    
    # Determine auth service URL based on environment
    environment = auth_client.detect_environment()
    
    if environment.value == 'staging':
        auth_service_url = 'https://auth.staging.netrasystems.ai'
    elif environment.value == 'production':
        auth_service_url = 'https://auth.netrasystems.ai'
    else:
        auth_service_url = os.getenv('AUTH_SERVICE_URL', 'http://localhost:8081')
    
    # Get provider from query params (default to google)
    provider = request.query_params.get('provider', 'google')
    
    # Build redirect URL to auth service
    redirect_url = f"{auth_service_url}/auth/login?provider={provider}"
    
    # Add return_url if provided
    return_url = request.query_params.get('return_url')
    if return_url:
        redirect_url += f"&return_url={return_url}"
    
    return RedirectResponse(url=redirect_url, status_code=302)