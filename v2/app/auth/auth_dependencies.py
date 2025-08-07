from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status, Request, WebSocket
from app.config import settings
from app import schemas
import uuid
from datetime import datetime
from app.db.postgres import AsyncSession
from app.dependencies import get_db_session, get_security_service
from app.services.security_service import SecurityService

async def get_dev_user() -> schemas.User:
    """Provides a default user for development environments."""
    return schemas.User(
        id=str(uuid.uuid4()),
        email=settings.dev_user_email,
        created_at=datetime.utcnow(),
        full_name="Dev User",
        picture=None
    )

async def get_user_from_session(
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    security_service: Annotated[SecurityService, Depends(get_security_service)],
) -> Optional[schemas.User]:
    """
    Retrieves user information from the session, validates it, and returns a user object.
    Returns None if the user is not authenticated.
    """
    user_info = request.session.get('user')
    if not user_info:
        return None

    email = user_info.get('email')
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session data: email missing")

    user = await security_service.get_user(db_session, email)
    if user is None:
        # This case might happen if the user was deleted from the DB but the session persists.
        request.session.pop('user', None)
        return None
    
    return schemas.User.model_validate(user)

async def get_active_user(
    user_from_session: Optional[schemas.User] = Depends(get_user_from_session),
    dev_user: schemas.User = Depends(get_dev_user)
) -> schemas.User:
    """
    Determines the current user based on the environment.
    In production, it relies on the user from the session.
    In development, it falls back to a default dev user if no session user exists.
    """
    if settings.environment == "production":
        if user_from_session is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        return user_from_session
    
    # In development, allow fallback to a dev user
    return user_from_session or dev_user

async def get_current_user_ws(
    websocket: WebSocket,
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    security_service: Annotated[SecurityService, Depends(get_security_service)],
) -> schemas.User:
    """
    Handles user authentication for WebSocket connections, supporting both production
    and development environments.
    """
    user_info = websocket.session.get('user')

    if settings.environment == "development" and not user_info:
        return await get_dev_user()

    if not user_info or 'email' not in user_info:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Not authenticated")
        raise ConnectionAbortedError("Authentication failed")

    email = user_info['email']
    user = await security_service.get_user(db_session, email)
    if user is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")
        raise ConnectionAbortedError("User not found")

    return schemas.User.model_validate(user)


CurrentUser = Annotated[schemas.User, Depends(get_active_user)]
ActiveUserWsDep = Annotated[schemas.User, Depends(get_current_user_ws)]
ActiveUserDep = CurrentUser