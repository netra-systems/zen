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

from ..services.security_service import get_password_hash, verify_password


@router.post("/token", response_model=schema.Token, openapi_extra={
    "requestBody": {
        "content": {
            "application/x-www-form-urlencoded": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "username": {"type": "string", "example": "jdoe@example.com"},
                        "password": {"type": "string", "example": "secret"}
                    },
                    "required": ["username", "password"]
                }
            }
        }
    }
})
async def login_for_access_token(request: Request, form_data: OAuthFormDep, db: DbDep):
    """
    Provides a JWT access token for a valid user.
    """
    security_service = request.app.state.security_service
    statement = select(models_postgres.User).where(models_postgres.User.email == form_data.username)
    result = await db.execute(statement)
    user = result.scalar_one_or_none()

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

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = security_service.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    logger.info(f"User '{user.email}' logged in successfully.")
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/dev-login", response_model=schema.Token, include_in_schema=False)
async def dev_login(request: Request, db: DbDep):
    """
    Provides a JWT access token for a default user in development environments.
    """
    if settings.environment != "development":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    security_service = request.app.state.security_service
    statement = select(models_postgres.User)
    result = await db.execute(statement)
    user = result.scalars().first()

    if not user:
        logger.error("No users found in the database for dev login.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No users found in the database. Please create a user first.",
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = security_service.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    logger.info(f"Dev login successful for user: {user.email}")
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/users", response_model=schema.UserPublic, status_code=status.HTTP_201_CREATED)
async def create_user(request: Request, user: schema.UserCreate, db: DbDep):
    """
    Creates a new user in the database.
    """
    security_service = request.app.state.security_service
    statement = select(models_postgres.User).where(models_postgres.User.email == user.email)
    result = await db.execute(statement)
    db_user = result.scalar_one_or_none()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    user_data = user.model_dump()
    user_data.pop("password", None)
    user_to_add = models_postgres.User(**user_data, hashed_password=hashed_password)
    
    db.add(user_to_add)
    await db.commit()
    await db.refresh(user_to_add)
    logger.info(f"New user created: {user.email}")
    return user_to_add


@router.get("/users/me", response_model=schema.UserPublicWithPicture)
async def read_users_me(current_user: ActiveUserDep):
    """
    Returns the public information for the currently authenticated user.
    """
    return current_user


@router.put("/users/me", response_model=schema.UserPublic)
async def update_user_me(
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
    await db.commit()
    await db.refresh(current_user)
    logger.info(f"User '{current_user.email}' updated successfully.")
    return current_user


@router.delete("/users/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_me(current_user: ActiveUserDep, db: DbDep):
    """
    Deletes the current user's account.
    """
    await db.delete(current_user)
    await db.commit()
    logger.info(f"User '{current_user.email}' deleted successfully.")
    return None
