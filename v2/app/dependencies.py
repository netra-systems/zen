from typing import Annotated
from fastapi import Depends, HTTPException, status, Request
from sqlmodel import Session

from app.db.postgres import get_async_db
from app.db import models_postgres
from app import schemas
from app.llm.llm_manager import LLMManager
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings

DbDep = Annotated[Session, Depends(get_async_db)]

def get_llm_manager(request: Request) -> LLMManager:
    return request.app.state.llm_manager

async def get_db_session(request: Request) -> AsyncSession:
    async with request.app.state.db_session_factory() as session:
        yield session

async def get_current_user(
    db: DbDep, request: Request
) -> models_postgres.User:
    user_info = request.session.get('user')
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    email = user_info.get('email')
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    security_service = request.app.state.security_service
    user = await security_service.get_user(db, email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

ActiveUserDep = Annotated[models_postgres.User, Depends(get_current_user)]
LLMManagerDep = Annotated[LLMManager, Depends(get_llm_manager)]