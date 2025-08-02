# /v2/app/routes/auth.py
import logging
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from ..db import models_postgres
from .. import schema
from ..dependencies import DbDep, ActiveUserDep
from ..config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

OAuthFormDep = Annotated[OAuth2PasswordRequestForm, Depends()]

@router.post("/token", response_model=schema.Token)
def login_for_access_token(request: Request, form_data: OAuthFormDep, db: DbDep):
    """
    Provides a JWT access token for a valid user.
    """
    security_service = request.app.state.security_service
    statement = select(models_postgres.User).where(models_postgres.User.email == form_data.username)
    user = db.exec(statement).first()

    if not user or not security_service.verify_password(form_data.password, user.hashed_password):
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
    access_token = security_service.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    logger.info(f"User '{user.email}' logged in successfully.")
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/users", response_model=schema.UserPublic, status_code=status.HTTP_201_CREATED)
def create_user(request: Request, user: schema.UserCreate, db: DbDep):
    """
    Creates a new user in the database.
    """
    security_service = request.app.state.security_service
    statement = select(models_postgres.User).where(models_postgres.User.email == user.email)
    db_user = db.exec(statement).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = security_service.get_password_hash(user.password)
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


@router.put("/users/me", response_model=schema.UserPublic)
def update_user_me(
    user_update: schema.UserUpdate,
    current_user: ActiveUserDep,
    db: DbDep,
):
    """
    Updates the current user's information.
    """
    user_data = user_update.model_dump(exclude_unset=True)
    if "password" in user_data:
        user_data["hashed_password"] = get_password_hash(user_data.pop("password"))

    for key, value in user_data.items():
        setattr(current_user, key, value)

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    logger.info(f"User '{current_user.email}' updated successfully.")
    return current_user


@router.delete("/users/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_me(current_user: ActiveUserDep, db: DbDep):
    """
    Deletes the current user's account.
    """
    db.delete(current_user)
    db.commit()
    logger.info(f"User '{current_user.email}' deleted successfully.")
    return None
