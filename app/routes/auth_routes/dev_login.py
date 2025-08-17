"""
Development Login Logic
"""
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.user_service import user_service
from app.services.security_service import SecurityService
from app.schemas.registry import UserCreate
from app.schemas.Auth import DevLoginRequest
from .token_management import create_token_response


def validate_dev_login_allowed(oauth_config) -> None:
    """Validate that dev login is allowed in current environment."""
    if not oauth_config.allow_dev_login:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dev login is not available in this environment"
        )


async def get_or_create_dev_user(db: AsyncSession, email: str):
    """Get existing dev user or create new one."""
    user = await user_service.get_by_email(db, email=email)
    if not user:
        user_in = UserCreate(email=email, full_name="Dev User", picture=None, password="")
        user = await user_service.create(db, obj_in=user_in)
    return user


async def handle_dev_login(
    dev_login_request: DevLoginRequest, 
    oauth_config,
    db: AsyncSession, 
    security_service: SecurityService
):
    """Handle development login request."""
    validate_dev_login_allowed(oauth_config)
    user = await get_or_create_dev_user(db, dev_login_request.email)
    return create_token_response(security_service, user)