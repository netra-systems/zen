"""
Development Login Logic
"""
import os

import httpx
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.schemas.auth_types import DevLoginRequest
from netra_backend.app.schemas.registry import UserCreate
from netra_backend.app.services.security_service import SecurityService
from netra_backend.app.services.user_service import user_service


def validate_dev_login_allowed(oauth_config) -> None:
    """Validate that dev login is allowed in current environment."""
    if not oauth_config.allow_dev_login:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dev login is not available in this environment"
        )


async def get_or_create_dev_user(db: AsyncSession, email: str):
    """Get existing dev user or create new one."""
    user = await user_service.get_or_create_dev_user(db, email=email)
    return user


async def handle_dev_login(dev_login_request: DevLoginRequest, oauth_config, db: AsyncSession, security_service: SecurityService):
    """Handle development login request."""
    validate_dev_login_allowed(oauth_config)
    user = await get_or_create_dev_user(db, dev_login_request.email)
    
    # Use auth client's configured base URL
    from netra_backend.app.clients.auth_client_core import auth_client
    auth_service_url = auth_client.settings.base_url
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{auth_service_url}/auth/dev/login",
                json={},
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "access_token": data["access_token"],
                    "token_type": data.get("token_type", "bearer")
                }
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Auth service dev login failed"
                )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Auth service unavailable: {str(e)}"
            )