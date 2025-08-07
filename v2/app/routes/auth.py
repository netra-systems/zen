from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from starlette.requests import Request

from app.auth.oauth import oauth
from app.config import settings
from app.schemas import User, GoogleUser
from app.auth.auth_dependencies import get_current_user

router = APIRouter()

@router.get('/login')
async def login(request: Request):
    redirect_uri = request.url_for('auth')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get('/auth')
async def auth(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user = await oauth.google.parse_id_token(request, token)
    request.session['user'] = user
    return RedirectResponse(url=settings.frontend_url)

@router.get('/logout')
async def logout(request: Request):
    request.session.pop('user', None)
    return RedirectResponse(url=settings.frontend_url)

@router.get("/endpoints")
def get_auth_endpoints():
    return {
        "login": "/api/v3/auth/login",
        "logout": "/api/v3/auth/logout",
        "auth": "/api/v3/auth/auth",
    }

@router.get("/user", response_model=User)
async def get_user(user: User = Depends(get_current_user)):
    return user
