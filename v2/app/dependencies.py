# /v2.1/dependencies.py
import logging
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlmodel import Session

from . import models
from .database import get_db
from .config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# This scheme will require a token to be sent in the Authorization header.
# tokenUrl should point to the endpoint that provides the token.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# Create type annotations for dependencies to simplify signatures
TokenDep = Annotated[str, Depends(oauth2_scheme)]
DbDep = Annotated[Session, Depends(get_db)]


def get_current_user(token: TokenDep, db: DbDep) -> models.User:
    """
    Decodes the JWT token to get the current user.

    Raises:
        HTTPException: 401 Unauthorized if the token is invalid, expired, or the user doesn't exist.
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
            logger.warning("Token decoding failed: 'sub' claim missing.")
            raise credentials_exception
    except JWTError as e:
        logger.error(f"JWT Error: {e}")
        raise credentials_exception

    user = db.get(models.User, email) # Efficiently get user by primary key
    if user is None:
        logger.warning(f"User '{email}' from token not found in database.")
        raise credentials_exception
    return user


CurrentUserDep = Annotated[models.User, Depends(get_current_user)]

def get_current_active_user(current_user: CurrentUserDep) -> models.User:
    """
    Dependency that checks if the user retrieved from the token is active.
    
    Raises:
        HTTPException: 400 Bad Request if the user is inactive.
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

ActiveUserDep = Annotated[models.User, Depends(get_current_active_user)]


# Placeholder for future Admin-only endpoints
def get_admin_user(current_user: ActiveUserDep) -> models.User:
    """
    Placeholder dependency to secure admin-only routes.
    (This would be expanded to check a role or scope).
    """
    # In a real app, you would check a user role, e.g., if not current_user.is_admin:
    # raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user
    
AdminUserDep = Annotated[models.User, Depends(get_admin_user)]
