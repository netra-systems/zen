
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.auth.auth import google
from app.config import settings
from app.dependencies import get_db
from app.models.user import User
from app.schemas import UserCreate, User as UserSchema
from app.services.user_service import user_service

router = APIRouter()


@router.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for('auth')
    return await google.authorize_redirect(request, redirect_uri)


@router.get("/auth")
async def auth(request: Request, db: Session = Depends(get_db)):
    token = await google.authorize_access_token(request)
    user_info = await google.parse_id_token(request, token)
    user = user_service.get_by_email(db, email=user_info['email'])
    if not user:
        user_in = UserCreate(
            email=user_info['email'],
            full_name=user_info.get('name'),
            picture=user_info.get('picture'),
            password="",  # Not used for OAuth
        )
        user = user_service.create(db, obj_in=user_in)

    request.session["user"] = user_info

    return RedirectResponse(url=settings.frontend_url)


@router.get("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url=settings.frontend_url)


@router.get("/me", response_model=UserSchema)
async def get_me(request: Request, db: Session = Depends(get_db)):
    user_info = request.session.get("user")
    if not user_info:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user = user_service.get_by_email(db, email=user_info['email'])
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
