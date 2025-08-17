"""
Auth Service API Routes
FastAPI endpoints for authentication operations
"""
from fastapi import APIRouter, Request, Header, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Optional
import logging

from ..services.auth_service import AuthService
from ..models.auth_models import (
    LoginRequest, LoginResponse,
    TokenRequest, TokenResponse,
    RefreshRequest, ServiceTokenRequest,
    ServiceTokenResponse, HealthResponse
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

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    redis_ok = auth_service.session_manager.health_check()
    
    return HealthResponse(
        status="healthy" if redis_ok else "degraded",
        redis_connected=redis_ok,
        database_connected=True  # Placeholder
    )