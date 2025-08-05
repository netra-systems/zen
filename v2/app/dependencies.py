from typing import Annotated
from fastapi import Depends, HTTPException, status, Request
from sqlmodel import Session

from app.db.postgres import get_async_db
from app.db import models_postgres
from app import schema
from app.services.security_service import oauth2_scheme
from app.llm.llm_manager import LLMManager

DbDep = Annotated[Session, Depends(get_async_db)]
TokenDep = Annotated[str, Depends(oauth2_scheme)]

def get_llm_manager(request: Request) -> LLMManager:
    return request.app.state.llm_manager

def get_current_user(
    token: TokenDep, db: DbDep, request: Request
) -> models_postgres.User:
    security_service = request.app.state.security_service
    email = security_service.get_user_email_from_token(token)
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = security_service.get_user(db, email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

ActiveUserDep = Annotated[models_postgres.User, Depends(get_current_user)]
LLMManagerDep = Annotated[LLMManager, Depends(get_llm_manager)]
