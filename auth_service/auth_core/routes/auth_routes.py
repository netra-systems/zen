"""
Auth Service API Routes
FastAPI endpoints for authentication operations
"""
from fastapi import APIRouter, Request, Header, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Optional
import logging
import os

from ..config import AuthConfig
from ..services.auth_service import AuthService
from ..models.auth_models import (
    LoginRequest, LoginResponse,
    TokenRequest, TokenResponse,
    RefreshRequest, ServiceTokenRequest,
    ServiceTokenResponse, HealthResponse,
    AuthEndpoints, AuthConfigResponse
)
import httpx
import secrets

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])

# Initialize auth service singleton
auth_service = AuthService()

def get_client_info(request: Request) -> dict:
    """Extract client information from request"""
    return {
        "ip": request.client.host,
        "user_agent": request.headers.get("user-agent")
    }

def _detect_environment() -> str:
    """Detect the current environment"""
    return AuthConfig.get_environment()

def _determine_urls() -> tuple[str, str]:
    """Determine auth service and frontend URLs based on environment"""
    return AuthConfig.get_auth_service_url(), AuthConfig.get_frontend_url()

async def _sync_user_to_main_db(auth_user):
    """Sync user from auth database to main app database"""
    from ..database.main_db_sync import main_db_sync
    return await main_db_sync.sync_user(auth_user)

@router.get("/config", response_model=AuthConfigResponse)
async def get_auth_config(request: Request):
    """Returns authentication configuration for frontend integration"""
    try:
        auth_url, frontend_url = _determine_urls()
        env = _detect_environment()
        dev_mode = env == "development"
        
        # Build endpoints
        endpoints = AuthEndpoints(
            login=f"{auth_url}/auth/login",
            logout=f"{auth_url}/auth/logout",
            callback=f"{frontend_url}/auth/callback",
            token=f"{auth_url}/auth/token",
            user=f"{auth_url}/auth/verify",
            dev_login=f"{auth_url}/auth/dev/login" if dev_mode else None,
            validate_token=f"{auth_url}/auth/validate",
            refresh=f"{auth_url}/auth/refresh",
            health=f"{auth_url}/auth/health"
        )
        
        # Build response
        return AuthConfigResponse(
            google_client_id=AuthConfig.get_google_client_id(),
            endpoints=endpoints,
            development_mode=dev_mode,
            authorized_javascript_origins=[frontend_url],
            authorized_redirect_uris=[f"{frontend_url}/auth/callback"],
            pr_number=os.getenv("PR_NUMBER"),
            use_proxy=False,
            proxy_url=None
        )
    except Exception as e:
        logger.error(f"Auth config endpoint failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve auth configuration: {str(e)}")

@router.get("/login")
async def initiate_oauth_login(
    provider: str = "google",
    return_url: Optional[str] = None
):
    """Initiate OAuth login flow"""
    from fastapi.responses import RedirectResponse
    try:
        # Get OAuth configuration
        google_client_id = AuthConfig.get_google_client_id()
        if not google_client_id:
            logger.error("OAuth not configured - GOOGLE_CLIENT_ID is not set")
            raise HTTPException(status_code=500, detail="OAuth not configured")
        
        # Build OAuth URL
        redirect_uri = _determine_urls()[1] + "/auth/callback"
        state = secrets.token_urlsafe(32)  # Generate random state
        
        oauth_url = (
            "https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={google_client_id}&"
            f"redirect_uri={redirect_uri}&"
            "response_type=code&"
            "scope=openid%20email%20profile&"
            f"state={state}"
        )
        
        if return_url:
            oauth_url += f"&return_url={return_url}"
        
        return RedirectResponse(url=oauth_url, status_code=302)
    except Exception as e:
        logger.error(f"OAuth initiation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    client_info: dict = Depends(get_client_info)
):
    """User login endpoint"""
    try:
        response = await auth_service.login(request, client_info)
        return response
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=401, detail=str(e))

@router.post("/logout")
async def logout(
    authorization: Optional[str] = Header(None),
    session_id: Optional[str] = None
):
    """User logout endpoint"""
    if not authorization:
        raise HTTPException(status_code=401, detail="No token provided")
    
    token = authorization.replace("Bearer ", "")
    success = await auth_service.logout(token, session_id)
    
    return {"success": success}

@router.post("/validate", response_model=TokenResponse)
async def validate_token(request: TokenRequest):
    """Validate access token"""
    response = await auth_service.validate_token(request.token)
    
    if not response.valid:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return response

@router.post("/refresh")
async def refresh_tokens(request: RefreshRequest):
    """Refresh access and refresh tokens"""
    result = await auth_service.refresh_tokens(request.refresh_token)
    
    if not result:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    access_token, refresh_token = result
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": 900  # 15 minutes
    }

@router.post("/service-token", response_model=ServiceTokenResponse)
async def create_service_token(request: ServiceTokenRequest):
    """Create token for service-to-service auth"""
    try:
        response = await auth_service.create_service_token(request)
        return response
    except Exception as e:
        logger.error(f"Service token error: {e}")
        raise HTTPException(status_code=401, detail=str(e))

@router.get("/verify")
async def verify_auth(authorization: Optional[str] = Header(None)):
    """Quick endpoint to verify if token is valid"""
    if not authorization:
        raise HTTPException(status_code=401, detail="No token provided")
    
    token = authorization.replace("Bearer ", "")
    response = await auth_service.validate_token(token)
    
    if not response.valid:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return {
        "valid": True,
        "user_id": response.user_id,
        "email": response.email
    }

@router.get("/me")
async def get_current_user(authorization: Optional[str] = Header(None)):
    """Get current user information from token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="No token provided")
    
    token = authorization.replace("Bearer ", "")
    response = await auth_service.validate_token(token)
    
    if not response.valid:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Get session data if available
    session_data = auth_service.session_manager.get_user_session(
        response.user_id
    ) if hasattr(auth_service, 'session_manager') else None
    
    return {
        "id": response.user_id,
        "email": response.email,
        "permissions": response.permissions if hasattr(response, 'permissions') else [],
        "session": session_data
    }

@router.get("/session")
async def get_session(authorization: Optional[str] = Header(None)):
    """Get current session information"""
    if not authorization:
        raise HTTPException(status_code=401, detail="No token provided")
    
    token = authorization.replace("Bearer ", "")
    response = await auth_service.validate_token(token)
    
    if not response.valid:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Get session data
    session_data = auth_service.session_manager.get_user_session(
        response.user_id
    )
    
    if not session_data:
        return {
            "active": False,
            "user_id": response.user_id
        }
    
    return {
        "active": True,
        "user_id": response.user_id,
        "email": response.email,
        "created_at": session_data.get("created_at"),
        "last_activity": session_data.get("last_activity")
    }

@router.post("/dev/login")
async def dev_login(
    request: Request,
    client_info: dict = Depends(get_client_info)
):
    """Development mode login endpoint - creates/uses real database user"""
    env = _detect_environment()
    if env != "development":
        raise HTTPException(status_code=403, detail="Dev login only available in development mode")
    
    from ..database.connection import auth_db
    from ..database.repository import AuthUserRepository
    import uuid
    
    try:
        # Sync to main database first to get/create the user
        from ..database.models import AuthUser
        
        # Create temporary auth user for sync
        temp_user = AuthUser(
            id=f"dev-temp-{uuid.uuid4().hex[:8]}",
            email="dev@example.com",
            full_name="Development User",
            auth_provider="dev",
            is_active=True,
            is_verified=True
        )
        
        # Sync to main database and get the actual ID
        actual_user_id = await _sync_user_to_main_db(temp_user)
        
        if not actual_user_id:
            raise HTTPException(status_code=500, detail="Failed to sync user to main database")
        
        # Now create or update auth user with correct ID
        async with auth_db.get_session() as session:
            repo = AuthUserRepository(session)
            
            # Check if dev user exists in auth DB
            dev_user = await repo.get_by_email("dev@example.com")
            
            if dev_user:
                # Update existing auth user if ID changed
                if dev_user.id != actual_user_id:
                    from sqlalchemy import text
                    # Delete old record
                    await session.execute(
                        text("DELETE FROM auth_users WHERE id = :old_id"),
                        {"old_id": dev_user.id}
                    )
                    # Create new record with correct ID
                    new_user = AuthUser(
                        id=actual_user_id,
                        email=dev_user.email,
                        full_name=dev_user.full_name,
                        auth_provider=dev_user.auth_provider,
                        is_active=dev_user.is_active,
                        is_verified=dev_user.is_verified
                    )
                    session.add(new_user)
                    await session.flush()
                    dev_user = new_user
                    logger.info(f"Recreated auth user with ID {actual_user_id}")
            else:
                # Create new auth user with correct ID
                dev_user = AuthUser(
                    id=actual_user_id,
                    email="dev@example.com",
                    full_name="Development User",
                    auth_provider="dev",
                    is_active=True,
                    is_verified=True
                )
                session.add(dev_user)
                await session.flush()
                logger.info(f"Created auth user with ID {actual_user_id}")
            
            # Use the synced user ID
            user_id = actual_user_id
            user_email = dev_user.email
            user_name = dev_user.full_name
        
        # Generate tokens with real user ID
        access_token = auth_service.jwt_handler.create_access_token(
            user_id=user_id,
            email=user_email,
            permissions=["read", "write", "admin"]
        )
        
        refresh_token = auth_service.jwt_handler.create_refresh_token(
            user_id=user_id
        )
        
        # Create session
        session_id = auth_service.session_manager.create_session(
            user_id=user_id,
            user_data={
                "email": user_email,
                "ip_address": client_info.get("ip"),
                "user_agent": client_info.get("user_agent")
            }
        )
        
        logger.info(f"Dev login successful for {user_email} with user ID {user_id}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": 900,  # 15 minutes
            "user": {
                "id": user_id,
                "email": user_email,
                "name": user_name,
                "session_id": session_id
            }
        }
        
    except Exception as e:
        logger.error(f"Dev login error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Dev login failed: {str(e)}")

@router.get("/callback")
async def oauth_callback(
    code: str,
    state: str,
    return_url: Optional[str] = None
):
    """Handle OAuth callback from Google"""
    from fastapi.responses import RedirectResponse
    from ..database.connection import auth_db
    from ..database.repository import AuthUserRepository
    import uuid
    
    try:
        # Exchange code for tokens
        google_client_id = AuthConfig.get_google_client_id()
        google_client_secret = AuthConfig.get_google_client_secret()
        redirect_uri = _determine_urls()[1] + "/auth/callback"
        
        async with httpx.AsyncClient() as client:
            # Exchange code for tokens
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": google_client_id,
                    "client_secret": google_client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code"
                }
            )
            
            if token_response.status_code != 200:
                raise HTTPException(status_code=401, detail="Failed to exchange code")
            
            tokens = token_response.json()
            
            # Get user info
            user_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {tokens['access_token']}"}
            )
            
            if user_response.status_code != 200:
                raise HTTPException(status_code=401, detail="Failed to get user info")
            
            user_info = user_response.json()
        
        # Create or update user in main database
        async with auth_db.get_session() as session:
            repo = AuthUserRepository(session)
            
            # Prepare user data with consistent ID
            user_data = {
                "id": user_info.get("id", str(uuid.uuid4())),
                "email": user_info["email"],
                "name": user_info.get("name", ""),
                "provider": "google",
                **user_info
            }
            
            # Create or update OAuth user in auth database
            auth_user = await repo.create_oauth_user(user_data)
            
            # Also sync to main app database
            await _sync_user_to_main_db(auth_user)
            
            # Use the database user ID for tokens
            user_id = auth_user.id
        
        # Create session and tokens with real user ID
        access_token = auth_service.jwt_handler.create_access_token(
            user_id=user_id,
            email=user_info["email"],
            permissions=[]
        )
        
        refresh_token = auth_service.jwt_handler.create_refresh_token(
            user_id=user_id
        )
        
        # Create session
        session_id = auth_service.session_manager.create_session(
            user_id=user_id,
            user_data={
                "email": user_info["email"],
                "ip_address": None,
                "user_agent": None
            }
        )
        
        logger.info(f"OAuth login successful for {user_info['email']} with user ID {user_id}")
        
        # Redirect to frontend with tokens
        frontend_url = _determine_urls()[1]
        redirect_url = return_url or f"{frontend_url}/chat"
        redirect_url += f"?token={access_token}&refresh={refresh_token}"
        
        return RedirectResponse(url=redirect_url, status_code=302)
        
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    redis_ok = auth_service.session_manager.health_check()
    
    return HealthResponse(
        status="healthy" if redis_ok else "degraded",
        redis_connected=redis_ok,
        database_connected=True  # Placeholder
    )