# /v2/app/dependencies.py
import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlmodel import Session, select

from .config import settings
from .db.models_postgres import User
from .logging_config_custom.logger import logger
from .llm.llm_manager import LLMManager

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

TokenDep = Annotated[str, Depends(oauth2_scheme)]

from .db.postgres import get_async_db

DbDep = Annotated[Session, Depends(get_async_db)]

async def get_current_user(request: Request, token: TokenDep, db: DbDep) -> User:
    """
    Decodes the JWT token to get the current user.
    Raises HTTPException if the token is invalid or the user doesn't exist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # The token is expected to be in the format "Bearer <token>"
        # The OAuth2PasswordBearer dependency already handles extracting the token
        payload = jwt.decode(token, request.app.state.security_service.key_manager.jwt_secret_key, algorithms=[settings.algorithm])
        email: str = payload.get("sub")
        if email is None:
            logger.warning("Token payload missing 'sub' (email).")
            raise credentials_exception
    except JWTError as e:
        logger.error(f"JWT Error: {e}")
        raise credentials_exception from e

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        logger.warning(f"User with email '{email}' from token not found in DB.")
        raise credentials_exception
    return user

CurrentUserDep = Annotated[User, Depends(get_current_user)]

def get_current_active_user(current_user: CurrentUserDep) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

ActiveUserDep = Annotated[User, Depends(get_current_active_user)]




def get_llm_manager(request: Request) -> LLMManager:
    return request.app.state.llm_manager

LLMManagerDep = Annotated[LLMManager, Depends(get_llm_manager)]



