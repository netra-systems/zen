
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.auth.auth import google
from app.config import settings
from app.dependencies import get_db_session
from app.db.models_postgres import User
from app.schemas import UserCreate, User as UserSchema, AuthConfigResponse
from app.schemas.Auth import AuthEndpoints
from app.services.user_service import user_service
from app.auth.auth_dependencies import get_current_user_ws

router = APIRouter()

class AuthRoutes:
    
    @router.get("/config", response_model=AuthConfigResponse)
    async def get_auth_config(request: Request):
        """
        Returns the authentication configuration.
        This endpoint is used by the frontend to determine how to behave.
        """
        return AuthConfigResponse(
            development_mode=settings.environment == "development",
            google_client_id=settings.oauth_config.client_id,
            endpoints=AuthEndpoints(
                login=f"{settings.api_base_url}/login",
                logout=f"{settings.api_base_url}/logout",
                token=f"{settings.api_base_url}/auth",
                user=f"{settings.api_base_url}/me",
                dev_login=f"{settings.api_base_url}/dev_login",
            ),
            authorized_javascript_origins=settings.oauth_config.authorized_javascript_origins,
            authorized_redirect_uris=settings.oauth_config.authorized_redirect_uris,
        )

    @router.get("/login")
    async def login(request: Request):
        redirect_uri = request.url_for('auth')
        return await google.authorize_redirect(request, redirect_uri)


    @router.get("/auth")
    async def auth(request: Request, db: Session = Depends(get_db_session)):
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
    async def get_me(request: Request, db: Session = Depends(get_db_session)):
        user_info = request.session.get("user")
        if not user_info:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        user = user_service.get_by_email(db, email=user_info['email'])
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user
