"""
Token Management Logic
"""
from fastapi import HTTPException, status
from fastapi.responses import RedirectResponse

from netra_backend.app.routes.auth_routes.utils import get_frontend_url_for_environment
from netra_backend.app.schemas.auth_types import TokenPayload
from netra_backend.app.services.security_service import SecurityService


def validate_user_auth(user) -> None:
    """Validate user authentication and raise exception if invalid."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def create_token_response(security_service: SecurityService, user) -> dict:
    """Create access token response for authenticated user through auth service."""
    from netra_backend.app.clients.auth_client_core import auth_client
    token_data = {"user_id": str(user.id)}
    result = await auth_client.create_token(token_data)
    if not result or "access_token" not in result:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=500,
            detail="Failed to create access token"
        )
    return {"access_token": result["access_token"], "token_type": "bearer"}


def _handle_oauth_redirect_error(e: Exception) -> RedirectResponse:
    """Handle OAuth redirect error."""
    from netra_backend.app.logging_config import central_logger
    logger = central_logger.get_logger(__name__)
    logger.error(f"OAuth redirect failed: {str(e)}")
    frontend_url = get_frontend_url_for_environment()
    return RedirectResponse(url=f"{frontend_url}/auth/error?message={str(e)}")

async def execute_oauth_redirect(request, redirect_uri: str) -> RedirectResponse:
    """Execute OAuth redirect with error handling."""
    try:
        from netra_backend.app.clients.auth_client_core import (
            oauth_client,  # Import here to avoid circular imports
        )
        return await oauth_client.google.authorize_redirect(request, redirect_uri)
    except Exception as e:
        return _handle_oauth_redirect_error(e)


def build_callback_redirect(access_token: str) -> RedirectResponse:
    """Build successful callback redirect with token."""
    frontend_url = get_frontend_url_for_environment()
    frontend_callback_url = f"{frontend_url}/auth/callback?token={access_token}"
    return RedirectResponse(url=frontend_callback_url)


def build_error_redirect(error: Exception) -> RedirectResponse:
    """Build error redirect for callback failures."""
    frontend_url = get_frontend_url_for_environment()
    error_url = f"{frontend_url}/auth/error?message={str(error)}"
    return RedirectResponse(url=error_url)