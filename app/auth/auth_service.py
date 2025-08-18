"""Auth Service - Standalone FastAPI microservice for authentication.

This is the STANDALONE auth service that runs separately from main backend.
Handles OAuth flows, token management, and session handling.
All functions ≤8 lines (MANDATORY). File ≤300 lines (MANDATORY).

Business Value Justification (BVJ):
1. Segment: All customer segments (Free through Enterprise)
2. Business Goal: Secure authentication infrastructure
3. Value Impact: Enables secure user access and session management
4. Revenue Impact: Critical for platform security and user retention
"""

import os
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .oauth_session_manager import OAuthSessionManager
from .auth_token_service import AuthTokenService
from .environment_config import EnvironmentAuthConfig
from .oauth_utils import build_google_oauth_url, exchange_code_for_tokens, get_user_info_from_google
from .url_validators import validate_and_get_return_url, get_auth_service_url
from .auth_response_builders import (
    build_oauth_callback_response, 
    build_service_status,
    add_auth_urls,
    clear_auth_cookies
)

logger = logging.getLogger(__name__)

# Service components
auth_session_manager = OAuthSessionManager()
auth_token_service = AuthTokenService()
auth_env_config = EnvironmentAuthConfig()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    await startup_event()
    yield

# FastAPI app instance
app = FastAPI(
    title="Netra Auth Service",
    description="Standalone authentication microservice",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
def setup_cors():
    """Setup CORS middleware."""
    origins = os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    origins = [origin.strip() for origin in origins if origin.strip()]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins if origins else ["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

setup_cors()

@app.get("/auth/login")
async def initiate_oauth_login(
    request: Request, 
    pr: Optional[str] = None,
    return_url: Optional[str] = None
) -> RedirectResponse:
    """Initiate OAuth login flow."""
    validated_return_url = validate_and_get_return_url(return_url)
    state_id = await auth_session_manager.create_oauth_state(pr, validated_return_url)
    oauth_config = auth_env_config.get_oauth_config()
    oauth_url = build_google_oauth_url(oauth_config, state_id)
    return RedirectResponse(url=oauth_url)

@app.get("/auth/callback")
async def handle_oauth_callback(
    request: Request,
    code: str,
    state: str
) -> RedirectResponse:
    """Handle OAuth callback."""
    state_data = await auth_session_manager.validate_and_consume_state(state)
    token_data = exchange_code_for_tokens(code, auth_env_config.get_oauth_config())
    user_info = get_user_info_from_google(token_data["access_token"])
    jwt_token = auth_token_service.generate_jwt(user_info)
    return build_oauth_callback_response(jwt_token, user_info, state_data)

@app.post("/auth/token")
async def exchange_token(request: Request) -> Dict[str, Any]:
    """Exchange authorization code for JWT token."""
    data = await request.json()
    code = data.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code required")
    
    oauth_config = auth_env_config.get_oauth_config()
    token_data = exchange_code_for_tokens(code, oauth_config)
    user_info = get_user_info_from_google(token_data["access_token"])
    jwt_token = auth_token_service.generate_jwt(user_info)
    return {"access_token": jwt_token, "user_info": user_info, "token_type": "bearer"}

@app.post("/auth/logout")
async def logout_user(request: Request) -> JSONResponse:
    """Logout user and revoke sessions."""
    auth_header = request.headers.get("Authorization")
    token = auth_header.replace("Bearer ", "") if auth_header else None
    
    if token:
        claims = auth_token_service.validate_jwt(token)
        if claims:
            user_id = claims.get("sub")
            await revoke_user_sessions(user_id)
    
    response = JSONResponse({"message": "Logged out successfully"})
    clear_auth_cookies(response)
    return response

@app.get("/auth/status")
async def get_auth_service_status() -> Dict[str, Any]:
    """Get auth service status."""
    redis_connected = await check_redis_connection()
    return build_service_status(redis_connected)

@app.get("/auth/config")
async def get_frontend_auth_config() -> Dict[str, Any]:
    """Get frontend auth configuration."""
    config = auth_env_config.get_frontend_config()
    auth_service_url = get_auth_service_url()
    config["auth_service_url"] = auth_service_url
    add_auth_urls(config, auth_service_url)
    return config

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "netra-auth-service"}

async def startup_event():
    """Startup event handler."""
    from ..services.redis_service import redis_service
    try:
        await redis_service.connect()
        logger.info("Auth service started successfully")
    except Exception as e:
        logger.error(f"Auth service startup failed: {e}")
        raise

async def check_redis_connection() -> bool:
    """Check Redis connection status."""
    from ..services.redis_service import redis_service
    try:
        await redis_service.ping()
        return True
    except Exception:
        return False

async def revoke_user_sessions(user_id: Optional[str]):
    """Revoke all user sessions."""
    if not user_id:
        return
    
    from ..services.redis_service import redis_service
    session_keys = await redis_service.keys(f"user_session:{user_id}:*")
    if session_keys:
        await redis_service.delete(*session_keys)

def handle_redis_connection_error(error: Exception):
    """Handle Redis connection errors."""
    logger.warning(f"Redis connection error: {error}")

def validate_exchange_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate token exchange request data."""
    if not data.get("code"):
        raise HTTPException(status_code=400, detail="Missing authorization code")
    return data

def process_logout_token(token: Optional[str]) -> Optional[str]:
    """Process logout token and extract user ID."""
    if not token:
        return None
    claims = auth_token_service.validate_jwt(token)
    return claims.get("sub") if claims else None

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)