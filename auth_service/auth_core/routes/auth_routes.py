"""
Auth Service API Routes
FastAPI endpoints for authentication operations
"""
from fastapi import APIRouter, Request, Header, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Optional
import logging
import os

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

# Initialize service
auth_service = AuthService()

def get_client_info(request: Request) -> dict:
    """Extract client information from request"""
    return {
        "ip": request.client.host,
        "user_agent": request.headers.get("user-agent")
    }

def _detect_environment() -> str:
    """Detect the current environment"""
    env = os.getenv("ENVIRONMENT", "development").lower()
    if env in ["staging", "production", "development"]:
        return env
    return "development"

def _determine_urls() -> tuple[str, str]:
    """Determine auth service and frontend URLs based on environment"""
    env = _detect_environment()
    if env == 'staging':
        return 'https://auth.staging.netrasystems.ai', 'https://staging.netrasystems.ai'
    elif env == 'production':
        return 'https://auth.netrasystems.ai', 'https://netrasystems.ai'
    return os.getenv('AUTH_SERVICE_URL', 'http://localhost:8081'), 'http://localhost:3000'

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
            google_client_id=os.getenv('GOOGLE_CLIENT_ID', ''),
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
        google_client_id = os.getenv('GOOGLE_CLIENT_ID')
        if not google_client_id:
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
    session_data = auth_service.session_manager.get_session(
        user_id=response.user_id
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
    session_data = auth_service.session_manager.get_session(
        user_id=response.user_id
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
    """Development mode login endpoint - bypasses authentication"""
    env = _detect_environment()
    if env != "development":
        raise HTTPException(status_code=403, detail="Dev login only available in development mode")
    
    try:
        # Create a dev user for testing
        dev_user = {
            "id": "dev-user-123",
            "email": "dev@example.com",
            "name": "Development User",
            "permissions": ["read", "write", "admin"]
        }
        
        # Generate tokens
        access_token = auth_service.jwt_handler.create_access_token(
            user_id=dev_user["id"],
            email=dev_user["email"],
            permissions=dev_user.get("permissions", [])
        )
        
        refresh_token = auth_service.jwt_handler.create_refresh_token(
            user_id=dev_user["id"]
        )
        
        # Create session
        session_id = auth_service.session_manager.create_session(
            user_id=dev_user["id"],
            user_data={
                "email": dev_user["email"],
                "ip_address": client_info.get("ip"),
                "user_agent": client_info.get("user_agent")
            }
        )
        
        logger.info(f"Dev login successful for {dev_user['email']}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": 900,  # 15 minutes
            "user": {
                "id": dev_user["id"],
                "email": dev_user["email"],
                "name": dev_user["name"],
                "session_id": session_id
            }
        }
        
    except Exception as e:
        logger.error(f"Dev login error: {e}")
        raise HTTPException(status_code=500, detail=f"Dev login failed: {str(e)}")

@router.get("/callback")
async def oauth_callback(
    code: str,
    state: str,
    return_url: Optional[str] = None
):
    """Handle OAuth callback from Google"""
    from fastapi.responses import RedirectResponse
    try:
        # Exchange code for tokens
        google_client_id = os.getenv('GOOGLE_CLIENT_ID')
        google_client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
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
        
        # Create session and tokens
        access_token = auth_service.jwt_handler.create_access_token(
            user_id=user_info["id"],
            email=user_info["email"],
            permissions=[]
        )
        
        refresh_token = auth_service.jwt_handler.create_refresh_token(
            user_id=user_info["id"]
        )
        
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