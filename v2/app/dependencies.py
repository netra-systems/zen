# /v2/app/dependencies.py
import logging
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlmodel import Session

from .db import models_postgres
from .database import get_db
from .config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

TokenDep = Annotated[str, Depends(oauth2_scheme)]
DbDep = Annotated[Session, Depends(get_db)]

def get_current_user(token: TokenDep, db: DbDep) -> models_postgres.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            logger.warning("Token decoding failed: 'sub' claim missing.")
            raise credentials_exception
    except JWTError as e:
        logger.error(f"JWT Error: {e}")
        raise credentials_exception

    user = db.query(models_postgres.User).filter(models_postgres.User.email == email).first()
    if user is None:
        logger.warning(f"User '{email}' from token not found in database.")
        raise credentials_exception
    return user

CurrentUserDep = Annotated[models_postgres.User, Depends(get_current_user)]

def get_current_active_user(current_user: CurrentUserDep) -> models_postgres.User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

ActiveUserDep = Annotated[models_postgres.User, Depends(get_current_active_user)]
