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
    """Initiate OAuth login with comprehensive security validation."""
    oauth_config = auth_client.get_oauth_config()
    if early_response := perform_login_validations(oauth_config, request):
        return early_response
    return await complete_oauth_login(request, oauth_config)