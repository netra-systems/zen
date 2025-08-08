from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from app.auth.oauth import oauth
from app.auth.auth_dependencies import get_current_user
from app import schemas
from app.config import settings
import uuid
from datetime import datetime

router = APIRouter()

@router.get("/api/v3/auth/endpoints", response_model=schemas.AuthConfigResponse)
async def get_auth_endpoints(request: Request, user: schemas.User = Depends(get_current_user)):
    return {
        "google_client_id": settings.oauth_config.client_id,
        "endpoints": {
            "login": f"{settings.api_base_url}/api/v3/auth/login/google",
            "logout": f"{settings.api_base_url}/api/v3/auth/logout",
            "token": f"{settings.api_base_url}/api/v3/auth/token",
            "user": f"{settings.api_base_url}/api/v3/auth/user",
            "dev_login": f"{settings.api_base_url}/api/v3/auth/dev-login",
        },
        "development_mode": settings.environment == "development",
        "user": user,
        "authorized_javascript_origins": settings.oauth_config.authorized_javascript_origins,
        "authorized_redirect_uris": settings.oauth_config.authorized_redirect_uris,
    }

@router.get('/api/v3/auth/login/google')
async def login_google(request: Request):
    redirect_uri = request.url_for('callback_google')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get('/api/v3/auth/callback/google', name='callback_google')
async def callback_google(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user = await oauth.google.parse_id_token(request, token)
    request.session['user'] = user
    return RedirectResponse(url=settings.frontend_url)

@router.get('/api/v3/auth/logout')
async def logout(request: Request):
    request.session.pop('user', None)
    return RedirectResponse(url=settings.frontend_url)

@router.post("/api/v3/auth/dev-login", response_model=schemas.User)
async def dev_login(request: Request, dev_login_request: schemas.DevLoginRequest):
    if settings.environment != "development":
        raise HTTPException(status_code=404, detail="Not Found")
    
    user = schemas.User(
        id=str(uuid.uuid4()),
        email=dev_login_request.email,
        created_at=datetime.utcnow(),
        full_name="Dev User",
        picture=None
    )
    request.session['user'] = user.model_dump()
    return user