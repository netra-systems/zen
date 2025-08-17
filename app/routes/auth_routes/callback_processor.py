"""
OAuth Callback Processing Logic
"""
from fastapi import HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.clients.auth_client import auth_client
from app.services.security_service import SecurityService
from app.services.user_service import user_service
from app.schemas.registry import UserCreateOAuth
from app.schemas.Token import TokenPayload
from app.logging_config import central_logger
from .token_management import build_callback_redirect, build_error_redirect

logger = central_logger.get_logger(__name__)


def log_callback_initiation(request: Request) -> None:
    """Log OAuth callback initiation for security auditing."""
    logger.info(f"OAuth callback received")
    logger.info(f"Query params: {dict(request.query_params)}")
    logger.info(f"Environment: {auth_client.detect_environment().value}")


def validate_callback_params(request: Request) -> None:
    """Validate callback parameters for errors."""
    if error := request.query_params.get("error"):
        error_desc = request.query_params.get("error_description", "OAuth error")
        logger.error(f"OAuth error: {error} - {error_desc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"{error}: {error_desc}"
        )


async def exchange_oauth_tokens(request: Request) -> tuple:
    """Exchange OAuth authorization code for tokens and user info."""
    token = await oauth_client.google.authorize_access_token(request)
    user_info = await oauth_client.google.parse_id_token(request, token)
    if not user_info or 'email' not in user_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid user info from provider"
        )
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
    user = await user_service.get_by_email(db, email=user_info['email'])
    if not user:
        user_in = build_oauth_user_data(user_info)
        user = await user_service.create(db, obj_in=user_in)
    return user


async def process_oauth_callback(
    request: Request, db: AsyncSession, security_service: SecurityService
) -> RedirectResponse:
    """Process OAuth callback and create user session."""
    log_callback_initiation(request)
    validate_callback_params(request)
    token, user_info = await exchange_oauth_tokens(request)
    user = await get_or_create_user(db, user_info)
    access_token = security_service.create_access_token(data=TokenPayload(sub=str(user.id)))
    return build_callback_redirect(access_token)


async def handle_callback_request(
    request: Request, db: AsyncSession, security_service: SecurityService
):
    """Forward OAuth callback to auth service."""
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
    
    # Forward all query params to auth service
    query_string = str(request.url.query)
    callback_url = f"{auth_service_url}/auth/callback"
    if query_string:
        callback_url += f"?{query_string}"
    
    return RedirectResponse(url=callback_url, status_code=302)