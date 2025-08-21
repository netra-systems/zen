"""
OAuth Callback Processing Logic
"""
from fastapi import HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from netra_backend.app.clients.auth_client import auth_client
from netra_backend.app.services.security_service import SecurityService
from netra_backend.app.services.user_service import user_service
from netra_backend.app.schemas.registry import UserCreateOAuth
from netra_backend.app.schemas.Token import TokenPayload
from netra_backend.app.logging_config import central_logger
from netra_backend.app.token_management import build_callback_redirect, build_error_redirect

logger = central_logger.get_logger(__name__)


def log_callback_initiation(request: Request) -> None:
    """Log OAuth callback initiation for security auditing."""
    logger.info(f"OAuth callback received")
    logger.info(f"Query params: {dict(request.query_params)}")
    logger.info(f"Environment: {auth_client.detect_environment().value}")


def _create_oauth_error_exception(error: str, error_desc: str) -> HTTPException:
    """Create OAuth error exception."""
    logger.error(f"OAuth error: {error} - {error_desc}")
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, 
        detail=f"{error}: {error_desc}"
    )

def validate_callback_params(request: Request) -> None:
    """Validate callback parameters for errors."""
    if error := request.query_params.get("error"):
        error_desc = request.query_params.get("error_description", "OAuth error")
        raise _create_oauth_error_exception(error, error_desc)


def _validate_user_info(user_info: dict) -> None:
    """Validate user info from OAuth provider."""
    if not user_info or 'email' not in user_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid user info from provider"
        )

async def exchange_oauth_tokens(request: Request) -> tuple:
    """Exchange OAuth authorization code for tokens and user info."""
    token = await oauth_client.google.authorize_access_token(request)
    user_info = await oauth_client.google.parse_id_token(request, token)
    _validate_user_info(user_info)
    return token, user_info


def build_oauth_user_data(user_info: dict) -> UserCreateOAuth:
    """Build OAuth user creation data."""
    return UserCreateOAuth(
        email=user_info['email'], 
        full_name=user_info.get('name'), 
        picture=user_info.get('picture')
    )


async def get_or_create_user(db: AsyncSession, user_info: dict):
    """Get existing user or create new user from OAuth info."""
    user_in = build_oauth_user_data(user_info)
    user = await user_service.get_or_create(db, obj_in=user_in)
    return user


async def _create_user_access_token(user) -> str:
    """Create access token for user through auth service."""
    from netra_backend.app.clients.auth_client import auth_client
    token_data = {"user_id": str(user.id)}
    result = await auth_client.create_token(token_data)
    if not result or "access_token" not in result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create access token"
        )
    return result["access_token"]

async def _execute_oauth_flow(request: Request, db: AsyncSession) -> object:
    """Execute OAuth token exchange and user creation flow."""
    log_callback_initiation(request)
    validate_callback_params(request)
    token, user_info = await exchange_oauth_tokens(request)
    user = await get_or_create_user(db, user_info)
    return user

async def process_oauth_callback(
    request: Request, db: AsyncSession, security_service: SecurityService
) -> RedirectResponse:
    """Process OAuth callback and create user session."""
    user = await _execute_oauth_flow(request, db)
    access_token = await _create_user_access_token(user)
    return build_callback_redirect(access_token)


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

def _build_callback_redirect_response(request: Request) -> 'RedirectResponse':
    """Build callback redirect response."""
    from fastapi.responses import RedirectResponse
    environment = auth_client.detect_environment()
    auth_service_url = _determine_callback_auth_service_url(environment)
    query_string = str(request.url.query)
    callback_url = _build_callback_url_with_params(auth_service_url, query_string)
    return RedirectResponse(url=callback_url, status_code=302)

async def handle_callback_request(
    request: Request, db: AsyncSession, security_service: SecurityService
):
    """Forward OAuth callback to auth service."""
    return _build_callback_redirect_response(request)