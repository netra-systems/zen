import os
from typing import Optional
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

def _get_frontend_url_for_environment() -> str:
    """Get the appropriate frontend URL based on environment."""
    # Check for explicit FRONTEND_URL env var first
    if frontend_url := os.getenv("FRONTEND_URL"):
        return frontend_url.rstrip('/')
    
    # Use environment-specific defaults
    env = auth_env_config.environment.value
    if env == "staging":
        return "https://staging.netrasystems.ai"
    elif env == "production":
        return "https://netrasystems.ai"
    else:
        # Development - use settings or default
        return settings.frontend_url.rstrip('/')



router = APIRouter()

class AuthRoutes:
    
    @staticmethod
    def _validate_oauth_credentials(oauth_config) -> Optional[RedirectResponse]:
        """Validate OAuth credentials are configured."""
        if not oauth_config.client_id or not oauth_config.client_secret:
            logger.error("OAuth credentials not configured!")
            frontend_url = _get_frontend_url_for_environment()
            error_msg = "OAuth not configured. Check server logs."
            return RedirectResponse(url=f"{frontend_url}/auth/error?message={error_msg}")
        return None
    
    @staticmethod
    def _handle_pr_proxy_redirect(oauth_config, request: Request) -> Optional[RedirectResponse]:
        """Handle PR environment proxy redirects."""
        if oauth_config.use_proxy and oauth_config.proxy_url:
            import urllib.parse
            pr_number = auth_env_config.pr_number
            return_url = str(request.base_url).rstrip('/')
            proxy_url = f"{oauth_config.proxy_url}/initiate?pr_number={pr_number}&return_url={urllib.parse.quote(return_url)}"
            logger.info(f"PR #{pr_number} OAuth login via proxy: {proxy_url}")
            return RedirectResponse(url=proxy_url)
        return None
    
    @staticmethod
    def _build_redirect_uri(request: Request) -> str:
        """Build redirect URI based on request and environment."""
        base_url = str(request.base_url).rstrip('/')
        if "localhost" in base_url or "127.0.0.1" in base_url:
            return f"{base_url}/api/auth/callback"
        
        if auth_env_config.environment.value in ["staging", "production"]:
            base_url = base_url.replace("http://", "https://")
        return f"{base_url}/api/auth/callback"
    
    @staticmethod
    def _validate_redirect_uri(redirect_uri: str, oauth_config) -> Optional[RedirectResponse]:
        """Validate redirect URI against allowed list."""
        if redirect_uri not in oauth_config.redirect_uris:
            logger.error(f"Redirect URI not in allowed list: {redirect_uri}")
            logger.error(f"Allowed URIs: {oauth_config.redirect_uris}")
            frontend_url = _get_frontend_url_for_environment()
            return RedirectResponse(url=f"{frontend_url}/auth/error?message=redirect_uri_mismatch")
        return None
    
    @staticmethod
    def _log_oauth_initiation(oauth_config, redirect_uri: str) -> None:
        """Log OAuth login initiation for security auditing."""
        logger.info(f"OAuth login initiated")
        logger.info(f"Environment: {auth_env_config.environment.value}")
        logger.info(f"Redirect URI: {redirect_uri}")
        logger.info(f"Client ID: {oauth_config.client_id[:20]}...")
        logger.info(f"Session configured: same_site=lax for localhost")
    
    @staticmethod
    async def _execute_oauth_redirect(request: Request, redirect_uri: str) -> RedirectResponse:
        """Execute OAuth redirect with error handling."""
        try:
            return await oauth_client.google.authorize_redirect(request, redirect_uri)
        except Exception as e:
            logger.error(f"OAuth redirect failed: {str(e)}")
            frontend_url = _get_frontend_url_for_environment()
            return RedirectResponse(url=f"{frontend_url}/auth/error?message={str(e)}")

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
        """Returns authentication configuration for frontend integration."""
        base_url = AuthRoutes._normalize_base_url(request)
        oauth_config = auth_env_config.get_oauth_config()
        
        endpoints = AuthRoutes._build_auth_endpoints(base_url, oauth_config)
        response = AuthRoutes._build_base_auth_response(oauth_config, endpoints)
        AuthRoutes._add_pr_configuration(response, oauth_config)
        
        return response

    @router.get("/login")
    async def login(request: Request):
        """Initiate OAuth login with comprehensive security validation."""
        oauth_config = auth_env_config.get_oauth_config()
        
        if error_response := AuthRoutes._validate_oauth_credentials(oauth_config):
            return error_response
        if proxy_response := AuthRoutes._handle_pr_proxy_redirect(oauth_config, request):
            return proxy_response
        
        redirect_uri = AuthRoutes._build_redirect_uri(request)
        if error_response := AuthRoutes._validate_redirect_uri(redirect_uri, oauth_config):
            return error_response
        
        AuthRoutes._log_oauth_initiation(oauth_config, redirect_uri)
        return await AuthRoutes._execute_oauth_redirect(request, redirect_uri)


    @router.get("/callback")
    async def callback(request: Request, db: AsyncSession = Depends(get_db_session), security_service: SecurityService = Depends(get_security_service)):
        """Handle OAuth callback from Google with comprehensive security validation."""
        try:
            AuthRoutes._log_callback_initiation(request)
            AuthRoutes._validate_callback_params(request)
            
            token, user_info = await AuthRoutes._exchange_oauth_tokens(request)
            user = await AuthRoutes._get_or_create_user(db, user_info)
            access_token = security_service.create_access_token(data=TokenPayload(sub=str(user.id)))
            
            return AuthRoutes._build_callback_redirect(access_token)
        except Exception as e:
            return AuthRoutes._build_error_redirect(e)


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

    @staticmethod
    def _log_callback_initiation(request: Request) -> None:
        """Log OAuth callback initiation for security auditing."""
        logger.info(f"OAuth callback received")
        logger.info(f"Query params: {dict(request.query_params)}")
        logger.info(f"Environment: {auth_env_config.environment.value}")

    @staticmethod
    def _validate_callback_params(request: Request) -> None:
        """Validate callback parameters for errors."""
        if error := request.query_params.get("error"):
            error_desc = request.query_params.get("error_description", "OAuth error")
            logger.error(f"OAuth error: {error} - {error_desc}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{error}: {error_desc}")

    @staticmethod
    async def _exchange_oauth_tokens(request: Request) -> tuple:
        """Exchange OAuth authorization code for tokens and user info."""
        token = await oauth_client.google.authorize_access_token(request)
        user_info = await oauth_client.google.parse_id_token(request, token)
        if not user_info or 'email' not in user_info:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user info from provider")
        return token, user_info

    @staticmethod
    async def _get_or_create_user(db: AsyncSession, user_info: dict):
        """Get existing user or create new user from OAuth info."""
        user = await user_service.get_by_email(db, email=user_info['email'])
        if not user:
            user_in = UserCreateOAuth(
                email=user_info['email'], full_name=user_info.get('name'), picture=user_info.get('picture')
            )
            user = await user_service.create(db, obj_in=user_in)
        return user

    @staticmethod
    def _build_callback_redirect(access_token: str) -> RedirectResponse:
        """Build successful callback redirect with token."""
        frontend_url = _get_frontend_url_for_environment()
        frontend_callback_url = f"{frontend_url}/auth/callback?token={access_token}"
        return RedirectResponse(url=frontend_callback_url)

    @staticmethod
    def _build_error_redirect(error: Exception) -> RedirectResponse:
        """Build error redirect for callback failures."""
        frontend_url = _get_frontend_url_for_environment()
        error_url = f"{frontend_url}/auth/error?message={str(error)}"
        return RedirectResponse(url=error_url)
    
    @staticmethod
    def _normalize_base_url(request: Request) -> str:
        """Normalize base URL for HTTPS in production environments."""
        base_url = str(request.base_url).rstrip('/')
        if auth_env_config.environment.value in ["staging", "production"]:
            base_url = base_url.replace("http://", "https://")
        return base_url
    
    @staticmethod
    def _build_auth_endpoints(base_url: str, oauth_config) -> AuthEndpoints:
        """Build authentication endpoints configuration."""
        return AuthEndpoints(
            login=f"{base_url}/api/auth/login",
            logout=f"{base_url}/api/auth/logout",
            callback=f"{base_url}/api/auth/callback",
            token=f"{base_url}/api/auth/token",
            user=f"{base_url}/api/users/me",
            dev_login=f"{base_url}/api/auth/dev_login" if oauth_config.allow_dev_login else None
        )
    
    @staticmethod
    def _build_base_auth_response(oauth_config, endpoints: AuthEndpoints) -> AuthConfigResponse:
        """Build base authentication configuration response."""
        return AuthConfigResponse(
            development_mode=auth_env_config.environment.value == "development",
            google_client_id=oauth_config.client_id,
            endpoints=endpoints,
            authorized_javascript_origins=oauth_config.javascript_origins,
            authorized_redirect_uris=oauth_config.redirect_uris
        )
    
    @staticmethod
    def _add_pr_configuration(response: AuthConfigResponse, oauth_config) -> None:
        """Add PR-specific configuration to auth response."""
        if auth_env_config.is_pr_environment:
            response.pr_number = auth_env_config.pr_number
            response.use_proxy = oauth_config.use_proxy
            response.proxy_url = oauth_config.proxy_url