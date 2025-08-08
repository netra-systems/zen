from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from app.auth.oauth import oauth
from app.auth.auth_dependencies import get_current_user
from app.auth import schemas as auth_schemas
from app.config import settings
import uuid
from datetime import datetime

router = APIRouter()

@router.get("/api/v3/auth/endpoints", response_model=auth_schemas.AuthConfigResponse)
async def get_auth_endpoints(request: Request, user: auth_schemas.User = Depends(get_current_user)):
    return {
        "google_client_id": settings.oauth_config.client_id,
        "endpoints": {
            "login": str(request.url_for('login_google')),
            "logout": str(request.url_for('logout')),
            "token": str(request.url_for('callback_google')),
            "user": "/api/v3/auth/user", # This should be a separate endpoint
            "dev_login": str(request.url_for('dev_login_route')),
        },
        "development_mode": settings.environment == "development",
        "user": user,
        "authorized_javascript_origins": settings.oauth_config.authorized_javascript_origins,
        "authorized_redirect_uris": settings.oauth_config.authorized_redirect_uris,
    }

@router.get('/api/v3/auth/login/google', name='login_google')
async def login_google(request: Request):
    redirect_uri = str(request.url_for('callback_google'))
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get('/api/v3/auth/callback/google', name='callback_google')
async def callback_google(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user_info = await oauth.google.parse_id_token(request, token)
    
    # In a real app, you'd find or create a user in your database here
    user = auth_schemas.User(
        id=user_info.get("sub"),
        email=user_info.get("email"),
        full_name=user_info.get("name"),
        picture=user_info.get("picture"),
    )
    
    request.session['user'] = user.model_dump_json()
    return RedirectResponse(url=settings.frontend_url)

@router.get('/api/v3/auth/logout', name='logout')
async def logout(request: Request):
    request.session.pop('user', None)
    return RedirectResponse(url=settings.frontend_url)

@router.post("/api/v3/auth/dev-login", response_model=auth_schemas.User, name='dev_login_route')
async def dev_login(request: Request, dev_login_request: auth_schemas.DevLoginRequest):
    if settings.environment != "development":
        raise HTTPException(status_code=404, detail="Not Found")
    
    user = auth_schemas.User(
        email=dev_login_request.email,
        full_name="Dev User",
    )
    request.session['user'] = user.model_dump_json()
    return user

@router.get("/api/v3/auth/user", response_model=auth_schemas.User)
async def get_user(user: auth_schemas.User = Depends(get_current_user)):
    return user