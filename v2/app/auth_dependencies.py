from typing import Annotated
from fastapi import Depends, HTTPException, status, WebSocket, Query, Request
from app.db import models_postgres
from app.config import settings

async def get_current_user_ws(
    websocket: WebSocket,
    token: str = Query(None),
) -> models_postgres.User:
    print(f"DEBUG: get_current_user_ws called. app_env = {settings.app_env}, token = {token}")

    if settings.app_env == "development":
        print("DEBUG: APP_ENV is development. Bypassing authentication.")
        return models_postgres.User(email=settings.dev_user_email, hashed_password="dev")

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

async def get_current_active_user(request: Request) -> models_postgres.User:
    if settings.app_env == "development":
        return models_postgres.User(email=settings.dev_user_email, hashed_password="dev")

    token = request.headers.get("Authorization")
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    security_service = request.app.state.security_service
    email = security_service.get_user_email_from_token(token)
    if email is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    async with request.app.state.db_session_factory() as session:
        user = await security_service.get_user(session, email)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        return user

ActiveUserWsDep = Annotated[models_postgres.User, Depends(get_current_user_ws)]
ActiveUserDep = Annotated[models_postgres.User, Depends(get_current_active_user)]