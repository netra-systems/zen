# /v2/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlmodel import Session, select

from . import models
from .database import get_db
from .config import settings
from .services.security_service import get_password_hash, verify_password

# This scheme will require a token to be sent in the Authorization header.
# tokenUrl should point to the endpoint that provides the token.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    """
    Decodes the JWT token to get the current user.
    
    Args:
        token: The OAuth2 token provided by the client.
        db: The database session dependency.

    Returns:
        The authenticated User object from the database.
        
    Raises:
        HTTPException: If the token is invalid or the user is not found.
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
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.exec(select(models.User).where(models.User.email == email)).first()
    if user is None:
        raise credentials_exception
    return user
