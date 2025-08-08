from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from typing import Annotated

from app.auth.auth_dependencies import get_current_user
from app.auth.oauth import oauth
from app.config import settings
from app import schemas

router = APIRouter(prefix="/api/v3/auth", tags=["auth"])


@router.get("/endpoints", response_model=schemas.AuthConfigResponse)
async def get_auth_endpoints(request: Request, user: schemas.User | None = Depends(get_current_user)):
    return {
        "google_client_id": settings.oauth_config.client_id,
        "endpoints": {
            "login": f"{settings.api_base_url}/api/v3/auth/login",
            "logout": f"{settings.api_base_url}/api/v3/auth/logout",
            "token": f"{settings.api_base_url}/api/v3/auth/callback",
            "user": f"{settings.api_base_url}/api/v3/auth/user",
            "dev_login": f"{settings.api_base_url}/api/v3/auth/dev_login",
        },
        "development_mode": settings.environment == "development",
        "user": user,
    }


@router.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for("auth_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def auth_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get("userinfo")
    if user_info:
        request.session["user"] = dict(user_info)
    return RedirectResponse(url=settings.frontend_url)


@router.get("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url=settings.frontend_url)


@router.get("/user", response_model=schemas.User)
async def get_user(user: Annotated[schemas.User, Depends(get_current_user)]):
    return user


@router.post("/dev_login", response_model=schemas.User)
async def dev_login():
    """
    Logs in a developer user. This is only available in the development environment.
    """
    if settings.environment != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available in the development environment.",
        )
    user = schemas.User(
        id=uuid.uuid4(),
        email=settings.dev_user_email,
        full_name="Dev User",
        is_active=True,
        is_superuser=True,
    )
    return user
