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

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    redis_ok = auth_service.session_manager.health_check()
    
    return HealthResponse(
        status="healthy" if redis_ok else "degraded",
        redis_connected=redis_ok,
        database_connected=True  # Placeholder
    )