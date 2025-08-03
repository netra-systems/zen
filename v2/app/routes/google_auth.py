# /v2/app/routes/google_auth.py
import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from sqlmodel import Session, select

from ..db import models_postgres
from .. import schema
from ..dependencies import DbDep
from ..config import settings

router = APIRouter()

oauth = OAuth()
oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    client_kwargs={
        'scope': 'openid email profile'
    }
)

@router.get("/login/google")
async def login_via_google(request: Request):
    redirect_uri = "http://localhost:8000/auth/google"
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
            full_name=user_info['name'],
            is_active=True,
            hashed_password=""
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    access_token = request.app.state.security_service.create_access_token(data={"sub": user.email})
    response = RedirectResponse(url="/")
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response

@router.get("/logout/google")
async def logout_via_google(request: Request):
    response = RedirectResponse(url="/")
    response.delete_cookie(key="access_token")
    return response
