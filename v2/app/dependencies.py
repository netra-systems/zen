# /v2/app/dependencies.py
import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlmodel import Session, select

from .config import settings
from .db.postgres import SessionLocal
from .db.models_postgres import User
from .logging_config_custom.logger import logger

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

TokenDep = Annotated[str, Depends(oauth2_scheme)]

def get_db():
    """Provides a database session to a dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

DbDep = Annotated[Session, Depends(get_db)]

def get_current_user(token: TokenDep, db: DbDep) -> User:
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
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            logger.warning("Token payload missing 'sub' (email).")
            raise credentials_exception
    except JWTError as e:
        logger.error(f"JWT Error: {e}")
        raise credentials_exception from e

    user = db.exec(select(User).where(User.email == email)).first()
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

