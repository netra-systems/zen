from fastapi.security import OAuth2PasswordRequestForm
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.auth.auth import oauth_client
from app.auth.environment_config import auth_env_config
from app.config import settings
from app.dependencies import get_db_session, get_security_service
from app.db.models_postgres import User
from app.schemas.registry import UserCreate, UserCreateOAuth, User as UserSchema
from app.schemas.Auth import AuthConfigResponse, AuthEndpoints, DevLoginRequest
from app.schemas.Token import TokenPayload
from app.services.user_service import user_service
from app.services.security_service import SecurityService
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)



router = APIRouter()

class AuthRoutes:
    
    
    @router.post("/token")
    async def token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db_session), security_service: SecurityService = Depends(get_security_service)):
        user = await security_service.authenticate_user(db, form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token = security_service.create_access_token(data=TokenPayload(sub=str(user.id)))
        return {"access_token": access_token, "token_type": "bearer"}


    @router.get("/config", response_model=AuthConfigResponse)
    async def get_auth_config(request: Request):
        """
        Returns the authentication configuration.
        This endpoint is used by the frontend to determine how to behave.
        """
        # Use the actual request URL to build endpoints (handles dynamic ports)
        base_url = str(request.base_url).rstrip('/')
        
        # Get environment-specific OAuth configuration
        oauth_config = auth_env_config.get_oauth_config()
        frontend_config = auth_env_config.get_frontend_config()
        
        response = AuthConfigResponse(
            development_mode=auth_env_config.environment.value == "development",
            google_client_id=oauth_config.client_id,
            endpoints=AuthEndpoints(
                login=f"{base_url}/api/auth/login",
                logout=f"{base_url}/api/auth/logout",
                callback=f"{base_url}/api/auth/callback",
                token=f"{base_url}/api/auth/token",
                user=f"{base_url}/api/users/me",
                dev_login=f"{base_url}/api/auth/dev_login" if oauth_config.allow_dev_login else None,
            ),
            authorized_javascript_origins=oauth_config.javascript_origins,
            authorized_redirect_uris=oauth_config.redirect_uris,
        )
        
        # Add PR-specific configuration if applicable
        if auth_env_config.is_pr_environment:
            response.pr_number = auth_env_config.pr_number
            response.use_proxy = oauth_config.use_proxy
            response.proxy_url = oauth_config.proxy_url
        
        return response

    @router.get("/login")
    async def login(request: Request):
        oauth_config = auth_env_config.get_oauth_config()
        
        # For PR environments using proxy, redirect to proxy
        if oauth_config.use_proxy and oauth_config.proxy_url:
            import urllib.parse
            pr_number = auth_env_config.pr_number
            return_url = str(request.base_url).rstrip('/')
            proxy_url = f"{oauth_config.proxy_url}/initiate?pr_number={pr_number}&return_url={urllib.parse.quote(return_url)}"
            logger.info(f"PR #{pr_number} OAuth login via proxy: {proxy_url}")
            return RedirectResponse(url=proxy_url)
        
        # Standard OAuth flow
        base_url = str(request.base_url).rstrip('/')
        redirect_uri = f"{base_url}/api/auth/callback"
        logger.info(f"OAuth login initiated with redirect URI: {redirect_uri}")
        return await oauth_client.google.authorize_redirect(request, redirect_uri)


    @router.get("/callback")
    async def callback(request: Request, db: AsyncSession = Depends(get_db_session), security_service: SecurityService = Depends(get_security_service)):
        """Handle OAuth callback from Google"""
        try:
            # Log the callback request for debugging
            logger.info(f"OAuth callback received with params: {dict(request.query_params)}")
            
            token = await oauth_client.google.authorize_access_token(request)
            user_info = await oauth_client.google.parse_id_token(request, token)
            if not user_info or 'email' not in user_info:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user info from provider")

            user = await user_service.get_by_email(db, email=user_info['email'])
            if not user:
                user_in = UserCreateOAuth(
                    email=user_info['email'],
                    full_name=user_info.get('name'),
                    picture=user_info.get('picture'),
                )
                user = await user_service.create(db, obj_in=user_in)

            access_token = security_service.create_access_token(data=TokenPayload(sub=str(user.id)))
            
            # Redirect to frontend with token
            frontend_callback_url = f"{settings.frontend_url}/auth/callback?token={access_token}"
            return RedirectResponse(url=frontend_callback_url)
        except Exception as e:
            # Redirect to frontend with error
            error_url = f"{settings.frontend_url}/auth/error?message={str(e)}"
            return RedirectResponse(url=error_url)


    @router.post("/logout")
    async def logout(request: Request):
        """Handle logout - returns success response"""
        return {"message": "Successfully logged out", "success": True}

    @router.post("/dev_login")
    async def dev_login(request: Request, dev_login_request: DevLoginRequest, db: AsyncSession = Depends(get_db_session), security_service: SecurityService = Depends(get_security_service)):
        oauth_config = auth_env_config.get_oauth_config()
        if not oauth_config.allow_dev_login:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dev login is not available in this environment")

        user = await user_service.get_by_email(db, email=dev_login_request.email)
        if not user:
            # Create a new dev user if not exists
            user_in = UserCreate(
                email=dev_login_request.email,
                full_name="Dev User",
                picture=None,
                password="",
            )
            user = await user_service.create(db, obj_in=user_in)

        access_token = security_service.create_access_token(data=TokenPayload(sub=str(user.id)))
        return {"access_token": access_token, "token_type": "bearer"}