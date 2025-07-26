# /v2/app/routes/auth.py
import logging
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from ..db import models_postgres
from .. import schema
from ..dependencies import DbDep, ActiveUserDep
from ..config import settings
from ..services.security_service import create_access_token, get_password_hash, verify_password

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

OAuthFormDep = Annotated[OAuth2PasswordRequestForm, Depends()]

@router.post("/token", response_model=schema.Token)
def login_for_access_token(form_data: OAuthFormDep, db: DbDep):
    """
    Provides a JWT access token for a valid user.
    """
    statement = select(models_postgres.User).where(models_postgres.User.email == form_data.username)
    user = db.exec(statement).first()

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


@router.post("/users", response_model=schema.UserPublic, status_code=status.HTTP_201_CREATED)
def create_user(user: schema.UserCreate, db: DbDep):
    """
    Creates a new user in the database.
    """
    statement = select(models_postgres.User).where(models_postgres.User.email == user.email)
    db_user = db.exec(statement).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    user_data = user.model_dump()
    user_to_add = models_postgres.User(**user_data, hashed_password=hashed_password)
    
    db.add(user_to_add)
    db.commit()
    db.refresh(user_to_add)
    logger.info(f"New user created: {user.email}")
    return user_to_add


@router.get("/users/me", response_model=schema.UserPublic)
def read_users_me(current_user: ActiveUserDep):
    """
    Returns the public information for the currently authenticated user.
    """
    return current_user
