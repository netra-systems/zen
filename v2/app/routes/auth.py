
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
async def get_auth_config(request: Request, user: User = Depends(get_current_user)):
    base_url = str(request.base_url)
    return AuthConfigResponse(
        google_client_id=settings.oauth_config.client_id,
        endpoints=AuthEndpoints(
            login=f"{base_url}api/auth/login/google",
            logout=f"{base_url}api/auth/logout",
            token=f"{base_url}api/auth/token",
            user=f"{base_url}api/auth/user",
            dev_login=f"{base_url}api/auth/dev-login"
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


@auth_router.get("/api/auth/dev-login")
async def dev_login(
    request: Request,
    db_session: AsyncSession = Depends(get_db_session),
    security_service: SecurityService = Depends(get_security_service),
):
    if settings.environment != "development":
        return RedirectResponse(url="/login?error=not_in_development")

    user_info = {
        "email": "dev@example.com",
        "given_name": "Dev",
        "family_name": "User",
        "picture": "https://example.com/avatar.png",
    }
    user = await security_service.get_or_create_user_from_oauth(db_session, user_info)
    request.session['user'] = user.model_dump_json()

    return RedirectResponse(url="/")

@auth_router.get("/api/auth/user", response_model=User)
async def get_user(user: User = Depends(get_current_user)):
    return user
