
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from app import schemas
from app.config import settings
from app.auth.oauth import oauth
from app.auth.services import security_service
from app.dependencies import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

router = APIRouter(prefix="/api/v3/auth", tags=["auth"])

@router.get("/endpoints", response_model=schemas.AuthConfigResponse)
async def get_auth_endpoints(request: Request):
    user = request.session.get('user')
    return schemas.AuthConfigResponse(
        google_client_id=settings.oauth_config.client_id,
        endpoints=schemas.AuthEndpoints(
            login=f"{settings.api_base_url}/api/v3/auth/login/google",
            logout=f"{settings.api_base_url}/api/v3/auth/logout",
            token=f"{settings.api_base_url}/api/v3/auth/callback/google",
            user=f"{settings.api_base_url}/api/v3/auth/user",
            dev_login=f"{settings.api_base_url}/api/v3/auth/dev-login"
        ),
        development_mode=settings.environment == "development",
        user=user,
        authorized_javascript_origins=settings.oauth_config.authorized_javascript_origins,
        authorized_redirect_uris=settings.oauth_config.authorized_redirect_uris,
    )

@router.post("/dev-login", response_model=schemas.User)
async def dev_login(
    login_request: schemas.DevLoginRequest,
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
):
    if settings.environment != "development":
        return {"error": "Development login is not enabled"}
    user = await security_service.get_user(db_session, login_request.email)
    if not user:
        user = await security_service.get_or_create_user_from_oauth(
            db_session,
            {
                "email": settings.dev_user_email,
                "name": "Dev User",
                "picture": "",
            },
        )
    return schemas.User.model_validate(user)


@router.get("/login/google")
async def login_google(request: Request):
    redirect_uri = request.url_for("callback_google")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback/google")
async def callback_google(request: Request, db_session: Annotated[AsyncSession, Depends(get_db_session)]):
    token = await oauth.google.authorize_access_token(request)
    user_info = await oauth.google.parse_id_token(request, token)
    user = await security_service.get_or_create_user_from_oauth(db_session, user_info)
    request.session["user"] = schemas.User.model_validate(user).model_dump()
    return RedirectResponse(url=settings.frontend_url)


@router.get("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url=settings.frontend_url)


@router.get("/user", response_model=schemas.User)
async def get_user(request: Request):
    user = request.session.get("user")
    if not user:
        return None
    return schemas.User(**user)
