"""
Auth Routes Router - Main route definitions
"""
from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.auth_client import auth_client
from app.auth_dependencies import get_db_session, get_security_service
from app.schemas.Auth import AuthConfigResponse, DevLoginRequest
from app.services.security_service import SecurityService

from .config_handler import build_auth_config_response
from .login_flow import handle_login_request
from .callback_processor import handle_callback_request
from .dev_login import handle_dev_login
from .token_management import validate_user_auth, create_token_response

router = APIRouter()


@router.post("/token")
async def token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: AsyncSession = Depends(get_db_session), 
    security_service: SecurityService = Depends(get_security_service)
):
    """Authenticate user and return access token."""
    user = await security_service.authenticate_user(db, form_data.username, form_data.password)
    validate_user_auth(user)
    return create_token_response(security_service, user)


@router.get("/config", response_model=AuthConfigResponse)
async def get_auth_config(request: Request):
    """Returns authentication configuration for frontend integration."""
    return build_auth_config_response(request)


@router.get("/login")
async def login(request: Request):
    """Initiate OAuth login with comprehensive security validation."""
    return await handle_login_request(request)


@router.get("/callback")
async def callback(
    request: Request, 
    db: AsyncSession = Depends(get_db_session), 
    security_service: SecurityService = Depends(get_security_service)
):
    """Handle OAuth callback from Google with comprehensive security validation."""
    return await handle_callback_request(request, db, security_service)


@router.post("/logout")
async def logout(request: Request):
    """Handle logout - returns success response"""
    return {"message": "Successfully logged out", "success": True}


@router.post("/dev_login")
async def dev_login(
    request: Request, 
    dev_login_request: DevLoginRequest, 
    db: AsyncSession = Depends(get_db_session), 
    security_service: SecurityService = Depends(get_security_service)
):
    """Handle development login for testing environments."""
    oauth_config = auth_client.get_oauth_config()
    return await handle_dev_login(dev_login_request, oauth_config, db, security_service)