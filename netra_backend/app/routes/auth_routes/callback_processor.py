"""
OAuth Callback Processing Logic - Forwards to Auth Service
"""
from fastapi import Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from netra_backend.app.clients.auth_client import auth_client
from netra_backend.app.services.security_service import SecurityService
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


def _determine_callback_auth_service_url(environment) -> str:
    """Determine auth service URL for callback."""
    import os
    if environment.value == 'staging':
        return 'https://auth.staging.netrasystems.ai'
    elif environment.value == 'production':
        return 'https://auth.netrasystems.ai'
    return os.getenv('AUTH_SERVICE_URL', 'http://localhost:8081')

def _build_callback_url_with_params(auth_service_url: str, query_string: str) -> str:
    """Build callback URL with query parameters."""
    callback_url = f"{auth_service_url}/auth/callback"
    if query_string:
        callback_url += f"?{query_string}"
    return callback_url

def _build_callback_redirect_response(request: Request) -> RedirectResponse:
    """Build callback redirect response."""
    environment = auth_client.detect_environment()
    auth_service_url = _determine_callback_auth_service_url(environment)
    query_string = str(request.url.query)
    callback_url = _build_callback_url_with_params(auth_service_url, query_string)
    logger.info(f"Forwarding OAuth callback to auth service: {callback_url}")
    return RedirectResponse(url=callback_url, status_code=302)

async def handle_callback_request(
    request: Request, db: AsyncSession, security_service: SecurityService
) -> RedirectResponse:
    """Forward OAuth callback to auth service."""
    return _build_callback_redirect_response(request)