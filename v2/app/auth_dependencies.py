from typing import Annotated
from fastapi import Depends, WebSocket, status
from app.config import settings
from app import schemas
import uuid
from datetime import datetime
from app.auth.active_user import CurrentUser

async def get_current_user_ws(
    websocket: WebSocket,
) -> schemas.User:
    if settings.environment == "development" and 'user' not in websocket.session:
        return schemas.User(
            id=str(uuid.uuid4()),
            email=settings.dev_user_email,
            created_at=datetime.utcnow(),
            full_name="Dev User",
            picture=None
        )

    user_info = websocket.session.get('user')
    if not user_info:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise ConnectionAbortedError("User not authenticated")

    email = user_info.get('email')
    if not email:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise ConnectionAbortedError("User email not found in session")

    security_service = websocket.app.state.security_service
    async with websocket.app.state.db_session_factory() as session:
        user = await security_service.get_user(session, email)
        if user is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            raise ConnectionAbortedError("User not found in database")
        return schemas.User.model_validate(user)

ActiveUserWsDep = Annotated[schemas.User, Depends(get_current_user_ws)]
ActiveUserDep = CurrentUser