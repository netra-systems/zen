from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status, Request
from app.config import settings
from app import schemas as auth_schemas
from app.db.postgres import AsyncSession
from app.dependencies import get_db_session, get_security_service
from app.auth.services import SecurityService
import json
import logging

async def get_dev_user() -> auth_schemas.User:
    """Provides a default user for development environments."""
    return auth_schemas.User(
        id="a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
        email=settings.dev_user_email,
        full_name="Dev User",
    )

async def get_current_user(
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    security_service: Annotated[SecurityService, Depends(get_security_service)],
) -> Optional[auth_schemas.User]:
    user_json = request.session.get('user')

    if settings.environment == "development" and not user_json:
        return await get_dev_user()

    if not user_json:
        return None

    user_info = json.loads(user_json)
    email = user_info.get('email')
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session data: email missing")

    user = await security_service.get_or_create_user_from_oauth(db_session, user_info)

    return auth_schemas.User.model_validate(user)

async def get_current_user_ws(
    user_id: str,
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    security_service: Annotated[SecurityService, Depends(get_security_service)],
) -> auth_schemas.User:
    """
    Handles user authentication for WebSocket connections, supporting both production
    and development environments.
    """
    logger = logging.getLogger(__name__)

    if settings.environment == "development":
        logger.info("Development mode: Providing dev user.")
        return await get_dev_user()

    user = await security_service.get_user_by_id(db_session, user_id)
    if user is None:
        logger.warning(f"WebSocket authentication failed: User {user_id} not found. Closing connection.")
        raise ConnectionAbortedError("User not found")

    return auth_schemas.User.model_validate(user)


CurrentUser = Annotated[auth_schemas.User, Depends(get_current_user)]
ActiveUserWsDep = Annotated[auth_schemas.User, Depends(get_current_user_ws)]
ActiveUserDep = CurrentUser
