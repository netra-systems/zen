from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from app.auth.oauth import oauth
from app.config import settings
from app.schemas import User, GoogleUser, AuthConfigResponse, AuthEndpoints, DevUser
from app.auth.auth_dependencies import get_current_user
from app.dependencies import get_db_session
from sqlalchemy.orm import Session
from app.db.models_postgres import User as UserModel

router = APIRouter()

@router.get('/login')
async def login(request: Request):
    if settings.environment == 'development':
        user = DevUser()
        request.session['user'] = user.dict()
        return RedirectResponse(url=settings.frontend_url)
    redirect_uri = request.url_for('auth')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get('/auth')
async def auth(request: Request, db: Session = Depends(get_db_session)):
    token = await oauth.google.authorize_access_token(request)
    user_data = await oauth.google.parse_id_token(request, token)
    google_user = GoogleUser(**user_data)

    user = db.query(UserModel).filter(UserModel.email == google_user.email).first()
    if not user:
        user = UserModel(
            email=google_user.email,
            full_name=google_user.name,
            picture=google_user.picture
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    request.session['user'] = {
        'id': str(user.id),
        'email': user.email,
        'full_name': user.full_name,
        'picture': user.picture
    }
    return RedirectResponse(url=settings.frontend_url)

@router.get('/logout')
async def logout(request: Request):
    request.session.pop('user', None)
    return RedirectResponse(url=settings.frontend_url)

@router.get("/config", response_model=AuthConfigResponse)
def get_auth_config():
    endpoints = AuthEndpoints(
        login_url=f"{settings.api_base_url}/api/v3/auth/login",
        logout_url=f"{settings.api_base_url}/api/v3/auth/logout",
        auth_callback_url=f"{settings.api_base_url}/api/v3/auth/auth",
        user_info_url=f"{settings.api_base_url}/api/v3/auth/user",
        token_url=f"{settings.api_base_url}/api/v3/auth/token",
    )
    return AuthConfigResponse(
        development_mode=settings.environment == "development",
        dev_user=DevUser() if settings.environment == "development" else None,
        endpoints=endpoints,
        google_client_id=settings.oauth_config.client_id,
        google_redirect_uri=settings.oauth_config.web['authorized_redirect_uris'][2] # Assuming the first one is for production
    )

@router.get("/user", response_model=User)
async def get_user(user: User = Depends(get_current_user)):
    return user

@router.post("/token")
async def token(request: Request):
    # This is a placeholder for a token refresh endpoint if needed
    return {"message": "Token endpoint not implemented"}