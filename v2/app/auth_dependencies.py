from typing import Annotated
from fastapi import Depends, HTTPException, status, WebSocket, Query
from app.db import models_postgres
from app.config import settings

async def get_current_user_ws(
    websocket: WebSocket,
    token: str = Query(None),
) -> models_postgres.User:
    print(f"DEBUG: app_env = {settings.app_env}")
    print(f"DEBUG: token = {token}")

    if settings.app_env == "development":
        return models_postgres.User(email="dev@example.com", hashed_password="dev")

    if token is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    security_service = websocket.app.state.security_service
    email = security_service.get_user_email_from_token(token)
    print(f"DEBUG: email from token = {email}")
    if email is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    async with websocket.app.state.db_session_factory() as session:
        user = await security_service.get_user(session, email)
        if user is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        return user

ActiveUserWsDep = Annotated[models_postgres.User, Depends(get_current_user_ws)]
