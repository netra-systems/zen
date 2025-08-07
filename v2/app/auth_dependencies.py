from typing import Annotated
from fastapi import Depends, HTTPException, status, WebSocket, Query
from app.db import models_postgres
from app.config import settings
from app import schemas
import uuid
from datetime import datetime

async def get_current_user_ws(
    websocket: WebSocket,
) -> schemas.User:
    if settings.environment == "development":
        return schemas.User(
            id=str(uuid.uuid4()),
            email=settings.dev_user_email,
            created_at=datetime.utcnow()
        )

    user_info = websocket.session.get('user')
    if not user_info:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    email = user_info.get('email')
    if not email:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    security_service = websocket.app.state.security_service
    async with websocket.app.state.db_session_factory() as session:
        user = await security_service.get_user(session, email)
        if user is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        return schemas.User.model_validate(user)

from app.auth.active_user import get_active_user_dependency

ActiveUserWsDep = Annotated[schemas.User, Depends(get_current_user_ws)]
ActiveUserDep = Annotated[schemas.User, Depends(get_active_user_dependency)]
