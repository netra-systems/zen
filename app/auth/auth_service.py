"""Auth subdomain service - Main FastAPI application for OAuth flows.

Implements the auth subdomain architecture for handling OAuth flows across
all environments with dedicated endpoints for login, callback, token exchange,
logout, status, and configuration. Supports PR environment routing and 
secure token management.

All functions ≤8 lines (MANDATORY). File ≤300 lines (MANDATORY).
"""

import os
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.logging_config import central_logger
from app.redis_manager import RedisManager
from app.auth.environment_config import auth_env_config
from app.auth.auth_token_service import AuthTokenService
from app.auth.oauth_session_manager import OAuthSessionManager
from app.auth.oauth_utils import exchange_code_for_tokens, get_user_info_from_google, build_google_oauth_url
from app.auth.url_validators import validate_and_get_return_url, get_auth_service_url
from app.auth.auth_response_builders import (
    build_oauth_callback_response, build_token_response, clear_auth_cookies,
    build_service_status, add_auth_urls
)

logger = central_logger.get_logger(__name__)
redis_service = RedisManager()

# Create FastAPI app
app = FastAPI(
    title="Netra Auth Service",
    description="OAuth authentication service for all environments",
    version="1.0.0"
)

# Configure CORS
allowed_origins = os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"]
)


# Service startup handlers
def handle_redis_connection_error(error: ConnectionError) -> None:
    """Handle Redis connection errors during startup."""
    logger.error(f"Failed to connect to Redis during startup: {str(error)}")


def handle_critical_startup_error(error: Exception) -> None:
    """Handle critical startup errors."""
    logger.critical(f"Critical startup failure: {str(error)}")
    raise  # Re-raise critical startup errors


@app.on_event("startup")
async def startup_event():
    """Initialize auth service dependencies with error handling."""
    try:
        await redis_service.connect()
        logger.info("Auth service started successfully")
    except ConnectionError as e:
        handle_redis_connection_error(e)
    except Exception as e:
        handle_critical_startup_error(e)


# Initialize services
auth_token_service = AuthTokenService()
auth_session_manager = OAuthSessionManager()


@app.get("/auth/login")
async def initiate_oauth_login(request: Request, pr: Optional[str] = None, return_url: Optional[str] = None):
    """Initiate OAuth flow with Google."""
    validated_return_url = validate_and_get_return_url(return_url)
    state_id = await auth_session_manager.create_oauth_state(pr, validated_return_url)
    oauth_config = auth_env_config.get_oauth_config()
    auth_url = build_google_oauth_url(oauth_config, state_id)
    logger.info(f"Initiating OAuth login for {'PR ' + pr if pr else 'environment'}")
    return RedirectResponse(url=auth_url)


@app.get("/auth/callback")
async def handle_oauth_callback(request: Request, code: str, state: str):
    """Handle OAuth callback from Google."""
    state_data = await auth_session_manager.validate_and_consume_state(state)
    oauth_config = auth_env_config.get_oauth_config()
    token_data = await exchange_code_for_tokens(code, oauth_config)
    user_info = await get_user_info_from_google(token_data["access_token"])
    jwt_token = auth_token_service.generate_jwt(user_info)
    return build_oauth_callback_response(state_data, jwt_token, user_info)


def validate_exchange_request(code: Optional[str]) -> None:
    """Validate token exchange request."""
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code required")


@app.post("/auth/token")
async def exchange_token(request: Request):
    """Exchange OAuth code for JWT token (alternative flow)."""
    body = await request.json()
    code = body.get("code")
    validate_exchange_request(code)
    oauth_config = auth_env_config.get_oauth_config()
    token_data = await exchange_code_for_tokens(code, oauth_config)
    user_info = await get_user_info_from_google(token_data["access_token"])
    jwt_token = auth_token_service.generate_jwt(user_info)
    return build_token_response(jwt_token, user_info)


async def process_logout_token(auth_header: Optional[str]) -> None:
    """Process logout token if present."""
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        claims = auth_token_service.validate_jwt(token)
        if claims:
            await revoke_user_sessions(claims.get("sub"))
            logger.info(f"User {claims.get('email')} logged out successfully")


@app.post("/auth/logout")
async def logout_user(request: Request):
    """Revoke authentication tokens and logout."""
    auth_header = request.headers.get("Authorization")
    await process_logout_token(auth_header)
    response = JSONResponse({"message": "Logout successful"})
    clear_auth_cookies(response)
    return response


async def revoke_user_sessions(user_id: Optional[str]) -> None:
    """Revoke all active sessions for user."""
    if user_id:
        session_pattern = f"user_session:{user_id}:*"
        keys = await redis_service.keys(session_pattern)
        if keys:
            await redis_service.delete(*keys)


async def check_redis_connection() -> bool:
    """Check Redis connection status."""
    try:
        await redis_service.ping()
        return True
    except Exception:
        return False


@app.get("/auth/status")
async def get_auth_service_status():
    """Get authentication service health status."""
    redis_status = await check_redis_connection()
    return build_service_status(redis_status)


@app.get("/auth/config")
async def get_frontend_auth_config():
    """Get frontend authentication configuration."""
    config = auth_env_config.get_frontend_config()
    auth_service_url = get_auth_service_url()
    add_auth_urls(config, auth_service_url)
    return config


# Health check endpoint
@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok", "service": "netra-auth-service"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("AUTH_SERVICE_PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)