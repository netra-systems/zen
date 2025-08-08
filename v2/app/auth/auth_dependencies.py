from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status, Request, WebSocket
from app.config import settings
from app.auth import schemas as auth_schemas
import uuid
from datetime import datetime
from app.db.postgres import AsyncSession
from app.dependencies import get_db_session, get_security_service
from app.auth.services import SecurityService
import json

async def get_dev_user() -> auth_schemas.User:
    """Provides a default user for development environments."""
    return auth_schemas.User(
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

import logging

async def get_current_user_ws(
    websocket: WebSocket,
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    security_service: Annotated[SecurityService, Depends(get_security_service)],
) -> auth_schemas.User:
    """
    Handles user authentication for WebSocket connections, supporting both production
    and development environments.
    """
    logger = logging.getLogger(__name__)
    user_json = websocket.session.get('user')

    if settings.environment == "development" and not user_json:
        logger.info("Development mode: No user info in session, providing dev user.")
        return await get_dev_user()

    if not user_json:
        logger.warning(f"WebSocket authentication failed: No user info in session. Closing connection.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Not authenticated")
        raise ConnectionAbortedError("Authentication failed")

    user_info = json.loads(user_json)
    email = user_info.get('email')
    if not email:
        logger.warning(f"WebSocket authentication failed: Invalid session data: email missing. Closing connection.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid session data")
        raise ConnectionAbortedError("Authentication failed")

    user = await security_service.get_user(db_session, email)
    if user is None:
        logger.warning(f"WebSocket authentication failed: User {email} not found. Closing connection.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")
        raise ConnectionAbortedError("User not found")

    return auth_schemas.User.model_validate(user)


CurrentUser = Annotated[auth_schemas.User, Depends(get_current_user)]
ActiveUserWsDep = Annotated[auth_schemas.User, Depends(get_current_user_ws)]
ActiveUserDep = CurrentUser