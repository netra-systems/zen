
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from app.auth.auth_dependencies import get_current_user
from app.auth.schemas import AuthConfigResponse, AuthEndpoints, User
from app.config import settings
from app.auth.oauth import oauth
from app.dependencies import get_db_session, get_security_service
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.services import SecurityService

auth_router = APIRouter()

@auth_router.get("/api/auth/config", response_model=AuthConfigResponse)
async def get_auth_config(user: User = Depends(get_current_user)):
    return AuthConfigResponse(
        google_client_id=settings.oauth_config.client_id,
        endpoints=AuthEndpoints(
            login="/api/auth/login/google",
            logout="/api/auth/logout",
            token="/api/auth/token",  # Placeholder
            user="/api/auth/user",  # Placeholder
            dev_login="/api/auth/dev-login" #Placeholder
        ),
        development_mode=settings.environment == "development",
        user=user,
        authorized_javascript_origins=settings.oauth_config.authorized_javascript_origins,
        authorized_redirect_uris=settings.oauth_config.authorized_redirect_uris,
    )

@auth_router.get("/api/auth/login/google")
async def login_google(request: Request):
    redirect_uri = request.url_for('callback_google')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@auth_router.get("/api/auth/callback/google", name="callback_google")
async def callback_google(
    request: Request,
    db_session: AsyncSession = Depends(get_db_session),
    security_service: SecurityService = Depends(get_security_service),
):
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get('userinfo')
    if not user_info:
        return RedirectResponse(url="/login?error=true")

    user = await security_service.get_or_create_user_from_oauth(db_session, user_info)
    request.session['user'] = user.model_dump_json()

    return RedirectResponse(url="/")

@auth_router.get("/api/auth/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")
