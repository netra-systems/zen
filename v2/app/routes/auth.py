# /v2/app/routes/auth.py
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlmodel import Session, select
from authlib.integrations.starlette_client import OAuth
from fastapi.responses import RedirectResponse

from ..db import models_postgres
from .. import schemas
from ..dependencies import DbDep, ActiveUserDep
from ..config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

oauth = OAuth()
oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_id=settings.google_cloud.client_id,
    client_secret=settings.google_cloud.client_secret,
    client_kwargs={
        'scope': 'openid email profile'
    }
)

@router.get("/users/me", response_model=schemas.User)
async def read_users_me(current_user: ActiveUserDep):
    """
    Returns the public information for the currently authenticated user.
    """
    return current_user


@router.post("/logout")
async def logout(response: Response):
    """
    Logs out the user by clearing the authentication cookie.
    """
    response.delete_cookie(key="access_token")
    return {"message": "Logout successful"}

@router.get("/login/google")
async def login_via_google(request: Request):
    redirect_uri = request.url_for('auth_via_google')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/auth/google")
async def auth_via_google(request: Request, db: DbDep):
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get('userinfo')
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not fetch user info from Google"
        )

    result = await db.execute(select(models_postgres.User).where(models_postgres.User.email == user_info['email']))
    user = result.scalar_one_or_none()

    if not user:
        user = models_postgres.User(
            email=user_info['email'],
            full_name=user_info.get('name'),
            picture=user_info.get('picture'),
            is_active=True,
            hashed_password=""  # No password for OAuth users
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    request.session['user'] = user_info
    
    response = RedirectResponse(url=settings.frontend_url)
    return response
