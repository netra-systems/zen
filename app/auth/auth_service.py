"""Auth subdomain service - Main FastAPI application for OAuth flows.

Implements the auth subdomain architecture for handling OAuth flows across
all environments with dedicated endpoints for login, callback, token exchange,
logout, status, and configuration. Supports PR environment routing and 
secure token management.

All functions ≤8 lines (MANDATORY). File ≤300 lines (MANDATORY).
"""

import os
import json
import time
import secrets
from typing import Dict, Any, Optional
from urllib.parse import urlencode, quote, unquote

from fastapi import FastAPI, Request, HTTPException, Response, status
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import jwt
from datetime import datetime, timedelta, timezone

from app.logging_config import central_logger
from app.redis_manager import RedisManager
from app.auth.environment_config import auth_env_config
from app.auth.oauth_proxy import oauth_proxy

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


# Service startup
@app.on_event("startup")
async def startup_event():
    """Initialize auth service dependencies."""
    await redis_service.connect()
    logger.info("Auth service started successfully")


class AuthTokenService:
    """JWT token generation and management service."""
    
    def __init__(self):
        """Initialize token service."""
        self.jwt_secret = self._get_secure_jwt_secret()
        self.token_expiry = 3600  # 1 hour
        
    def _get_secure_jwt_secret(self) -> str:
        """Get JWT secret with security validation."""
        secret = os.getenv("JWT_SECRET_KEY")
        if not secret:
            raise HTTPException(
                status_code=500, 
                detail="JWT_SECRET_KEY environment variable must be set"
            )
        if len(secret) < 32:
            raise HTTPException(
                status_code=500,
                detail="JWT_SECRET_KEY must be at least 32 characters long"
            )
        return secret
        
    def generate_jwt(self, user_info: Dict[str, Any]) -> str:
        """Generate JWT token with user claims."""
        now = datetime.now(timezone.utc)
        payload = self._build_jwt_payload(user_info, now)
        return jwt.encode(payload, self.jwt_secret, algorithm="HS256")
    
    def _build_jwt_payload(self, user_info: Dict[str, Any], now: datetime) -> Dict[str, Any]:
        """Build JWT payload with standard claims."""
        return {
            "sub": user_info.get("id"), "email": user_info.get("email"),
            "name": user_info.get("name"), "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=self.token_expiry)).timestamp()),
            "iss": "netra-auth-service", "aud": "netra-api"
        }
    
    def validate_jwt(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate JWT token and return claims."""
        try:
            return jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.error(f"JWT validation failed: {e}")
            return None


class AuthSessionManager:
    """Manages OAuth sessions and state for security."""
    
    def __init__(self):
        """Initialize session manager."""
        self.session_ttl = 300  # 5 minutes
        
    async def create_oauth_state(self, pr_number: Optional[str], return_url: str) -> str:
        """Create secure OAuth state parameter."""
        csrf_token = secrets.token_urlsafe(32)
        state_data = self._build_state_data(pr_number, return_url, csrf_token)
        state_id = await self._store_state_data(state_data)
        return state_id
    
    def _build_state_data(self, pr_number: Optional[str], return_url: str, csrf_token: str) -> Dict[str, Any]:
        """Build OAuth state data."""
        data = {"csrf_token": csrf_token, "return_url": return_url, "timestamp": int(time.time())}
        if pr_number:
            data["pr_number"] = pr_number
        return data
    
    async def _store_state_data(self, state_data: Dict[str, Any]) -> str:
        """Store state data in Redis and return state ID."""
        state_id = secrets.token_urlsafe(16)
        await redis_service.setex(f"oauth_state:{state_id}", self.session_ttl, json.dumps(state_data))
        return state_id
    
    async def validate_and_consume_state(self, state_id: str) -> Dict[str, Any]:
        """Validate OAuth state and consume it."""
        state_json = await redis_service.get(f"oauth_state:{state_id}")
        if not state_json:
            raise HTTPException(status_code=400, detail="Invalid or expired state")
        await redis_service.delete(f"oauth_state:{state_id}")
        return self._validate_state_data(json.loads(state_json))
    
    def _validate_state_data(self, state_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate state data timestamp and structure."""
        current_time = int(time.time())
        if current_time - state_data.get("timestamp", 0) > self.session_ttl:
            raise HTTPException(status_code=400, detail="OAuth state expired")
        return state_data


# Initialize services
auth_token_service = AuthTokenService()
auth_session_manager = AuthSessionManager()


@app.get("/auth/login")
async def initiate_oauth_login(request: Request, pr: Optional[str] = None, return_url: Optional[str] = None):
    """Initiate OAuth flow with Google."""
    validated_return_url = _validate_and_get_return_url(return_url)
    state_id = await auth_session_manager.create_oauth_state(pr, validated_return_url)
    oauth_config = auth_env_config.get_oauth_config()
    auth_url = _build_google_oauth_url(oauth_config, state_id)
    logger.info(f"Initiating OAuth login for {'PR ' + pr if pr else 'environment'}")
    return RedirectResponse(url=auth_url)


def _validate_and_get_return_url(return_url: Optional[str]) -> str:
    """Validate and sanitize return URL."""
    if not return_url:
        return _get_default_return_url()
    decoded_url = unquote(return_url)
    _validate_return_url_security(decoded_url)
    return decoded_url


def _get_default_return_url() -> str:
    """Get default return URL based on environment."""
    config = auth_env_config.get_frontend_config()
    if auth_env_config.is_pr_environment:
        return f"https://pr-{auth_env_config.pr_number}.staging.netrasystems.ai"
    return config["javascript_origins"][0]


def _validate_return_url_security(url: str) -> None:
    """Validate return URL for security."""
    config = auth_env_config.get_oauth_config()
    allowed_origins = config.javascript_origins
    if not any(url.startswith(origin) for origin in allowed_origins):
        raise HTTPException(status_code=400, detail="Invalid return URL")


def _build_google_oauth_url(oauth_config, state_id: str) -> str:
    """Build Google OAuth authorization URL."""
    redirect_uri = _get_oauth_redirect_uri()
    params = {
        "client_id": oauth_config.client_id, "redirect_uri": redirect_uri,
        "response_type": "code", "scope": "openid email profile",
        "state": state_id, "access_type": "online"
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


def _get_oauth_redirect_uri() -> str:
    """Get OAuth redirect URI based on environment."""
    if auth_env_config.environment.value == "development":
        return "http://localhost:8001/auth/callback"
    elif auth_env_config.environment.value == "staging":
        return "https://auth.staging.netrasystems.ai/auth/callback"
    elif auth_env_config.environment.value == "production":
        return "https://auth.netrasystems.ai/auth/callback"
    return "http://localhost:8001/auth/callback"


@app.get("/auth/callback")
async def handle_oauth_callback(request: Request, code: str, state: str):
    """Handle OAuth callback from Google."""
    state_data = await auth_session_manager.validate_and_consume_state(state)
    oauth_config = auth_env_config.get_oauth_config()
    token_data = await _exchange_code_for_tokens(code, oauth_config)
    user_info = await _get_user_info_from_google(token_data["access_token"])
    jwt_token = auth_token_service.generate_jwt(user_info)
    return _build_oauth_callback_response(state_data, jwt_token, user_info)


async def _exchange_code_for_tokens(code: str, oauth_config) -> Dict[str, Any]:
    """Exchange authorization code for access tokens."""
    token_url = "https://oauth2.googleapis.com/token"
    redirect_uri = _get_oauth_redirect_uri()
    data = {
        "code": code, "client_id": oauth_config.client_id,
        "client_secret": oauth_config.client_secret, "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    return await _perform_token_exchange_request(token_url, data)


async def _perform_token_exchange_request(url: str, data: Dict[str, str]) -> Dict[str, Any]:
    """Perform HTTP request for token exchange with timeout and security."""
    timeout = httpx.Timeout(10.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(url, data=data)
            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.text}")
                raise HTTPException(status_code=400, detail="OAuth token exchange failed")
            return response.json()
        except httpx.TimeoutException:
            logger.error("Token exchange request timed out")
            raise HTTPException(status_code=503, detail="OAuth service temporarily unavailable")


async def _get_user_info_from_google(access_token: str) -> Dict[str, Any]:
    """Get user information from Google API with timeout and security."""
    user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    timeout = httpx.Timeout(10.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.get(user_info_url, headers=headers)
            if response.status_code != 200:
                logger.error(f"Failed to get user info: {response.text}")
                raise HTTPException(status_code=400, detail="Failed to retrieve user information")
            return response.json()
        except httpx.TimeoutException:
            logger.error("User info request timed out")
            raise HTTPException(status_code=503, detail="User info service temporarily unavailable")


def _build_oauth_callback_response(state_data: Dict[str, Any], jwt_token: str, user_info: Dict[str, Any]):
    """Build OAuth callback response with redirect."""
    return_url = state_data["return_url"]
    if "pr_number" in state_data:
        return _build_pr_environment_response(return_url, jwt_token, user_info, state_data["pr_number"])
    redirect_url = f"{return_url}/auth/complete"
    response = RedirectResponse(url=redirect_url)
    _set_auth_cookies(response, jwt_token)
    return response


def _build_pr_environment_response(return_url: str, jwt_token: str, user_info: Dict[str, Any], pr_number: str):
    """Build response for PR environment with token transfer."""
    redirect_url = f"{return_url}/auth/complete?token={jwt_token}"
    response = RedirectResponse(url=redirect_url)
    _set_pr_auth_cookies(response, jwt_token, pr_number)
    return response


def _set_auth_cookies(response: Response, jwt_token: str) -> None:
    """Set secure authentication cookies."""
    response.set_cookie(
        key="netra_auth_token", value=jwt_token, max_age=3600,
        secure=True, httponly=True, samesite="strict"
    )


def _set_pr_auth_cookies(response: Response, jwt_token: str, pr_number: str) -> None:
    """Set authentication cookies for PR environment."""
    response.set_cookie(
        key="netra_auth_token", value=jwt_token, max_age=3600,
        secure=True, httponly=True, samesite="none",
        domain=".staging.netrasystems.ai"
    )


@app.post("/auth/token")
async def exchange_token(request: Request):
    """Exchange OAuth code for JWT token (alternative flow)."""
    body = await request.json()
    code = body.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code required")
    oauth_config = auth_env_config.get_oauth_config()
    token_data = await _exchange_code_for_tokens(code, oauth_config)
    user_info = await _get_user_info_from_google(token_data["access_token"])
    jwt_token = auth_token_service.generate_jwt(user_info)
    return {"access_token": jwt_token, "token_type": "Bearer", "expires_in": 3600, "user_info": user_info}


@app.post("/auth/logout")
async def logout_user(request: Request):
    """Revoke authentication tokens and logout."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        claims = auth_token_service.validate_jwt(token)
        if claims:
            await _revoke_user_sessions(claims.get("sub"))
            logger.info(f"User {claims.get('email')} logged out successfully")
    response = JSONResponse({"message": "Logout successful"})
    _clear_auth_cookies(response)
    return response


async def _revoke_user_sessions(user_id: Optional[str]) -> None:
    """Revoke all active sessions for user."""
    if user_id:
        session_pattern = f"user_session:{user_id}:*"
        keys = await redis_service.keys(session_pattern)
        if keys:
            await redis_service.delete(*keys)


def _clear_auth_cookies(response: Response) -> None:
    """Clear authentication cookies."""
    response.delete_cookie("netra_auth_token")
    response.delete_cookie("netra_auth_token", domain=".staging.netrasystems.ai")


@app.get("/auth/status")
async def get_auth_service_status():
    """Get authentication service health status."""
    redis_status = await _check_redis_connection()
    return {
        "status": "healthy", "environment": auth_env_config.environment.value,
        "is_pr_environment": auth_env_config.is_pr_environment,
        "pr_number": auth_env_config.pr_number, "redis_connected": redis_status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


async def _check_redis_connection() -> bool:
    """Check Redis connection status."""
    try:
        await redis_service.ping()
        return True
    except Exception:
        return False


@app.get("/auth/config")
async def get_frontend_auth_config():
    """Get frontend authentication configuration."""
    config = auth_env_config.get_frontend_config()
    auth_service_url = _get_auth_service_url()
    config.update({
        "auth_service_url": auth_service_url,
        "login_url": f"{auth_service_url}/auth/login",
        "logout_url": f"{auth_service_url}/auth/logout"
    })
    return config


def _get_auth_service_url() -> str:
    """Get auth service URL based on environment."""
    if auth_env_config.environment.value == "development":
        return "http://localhost:8001"
    elif auth_env_config.environment.value == "staging":
        return "https://auth.staging.netrasystems.ai"
    elif auth_env_config.environment.value == "production":
        return "https://auth.netrasystems.ai"
    return "http://localhost:8001"


# Health check endpoint
@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok", "service": "netra-auth-service"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("AUTH_SERVICE_PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)