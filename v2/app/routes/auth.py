# /v2.1/routes/auth.py
import logging
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from .. import models
from ..dependencies import get_current_active_user, DbDep, ActiveUserDep
from ..config import settings
from ..database import get_db
from ..services.security_service import create_access_token, get_password_hash, verify_password

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication"])

OAuthFormDep = Annotated[OAuth2PasswordRequestForm, Depends()]

@router.post("/token", response_model=models.Token)
def login_for_access_token(form_data: OAuthFormDep, db: DbDep):
    """
    Provides a JWT access token for a valid user.
    """
    user = db.get(models.User, form_data.username) # Get user by email (PK)
    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Failed login attempt for email: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not user.is_active:
        logger.warning(f"Inactive user login attempt: {form_data.username}")
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    logger.info(f"User '{user.email}' logged in successfully.")
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/users", response_model=models.UserPublic, status_code=status.HTTP_201_CREATED)
def create_user(user: models.UserCreate, db: DbDep):
    """
    Creates a new user in the database.
    """
    db_user = db.get(models.User, user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    # Use .model_dump() to create a dict from the Pydantic model
    user_data = user.model_dump()
    # Create the SQLModel User instance
    user_to_add = models.User(**user_data, hashed_password=hashed_password)
    
    db.add(user_to_add)
    db.commit()
    db.refresh(user_to_add)
    logger.info(f"New user created: {user.email}")
    return user_to_add


@router.get("/users/me", response_model=models.UserPublic)
def read_users_me(current_user: ActiveUserDep):
    """
    Returns the public information for the currently authenticated and active user.
    """
    return current_user
