"""Auth subdomain service - Main FastAPI application for OAuth flows.

Implements the auth subdomain architecture for handling OAuth flows across
all environments with dedicated endpoints for login, callback, token exchange,
logout, status, and configuration. Supports PR environment routing and 
secure token management.

All functions ≤8 lines (MANDATORY). File ≤300 lines (MANDATORY).
"""

import os
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.logging_config import central_logger
from app.redis_manager import RedisManager
from app.auth.environment_config import auth_env_config
from app.auth.auth_token_service import AuthTokenService, UserInfo
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


# Service startup
def _handle_redis_connection_error(error: ConnectionError) -> None:
    """Handle Redis connection errors during startup."""
    logger.error(f"Failed to connect to Redis during startup: {str(error)}")
    # Continue startup without Redis - some features may be degraded

def _handle_critical_startup_error(error: Exception) -> None:
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
        _handle_redis_connection_error(e)
    except Exception as e:
        _handle_critical_startup_error(e)


class AuthTokenService:
    """JWT token generation and management service."""
    
    def __init__(self):
        """Initialize token service."""
        self.jwt_secret = self._get_secure_jwt_secret()
        self.token_expiry = 3600  # 1 hour
        
    def _validate_jwt_secret_exists(self, secret: Optional[str]) -> None:
        """Validate JWT secret exists."""
        if not secret:
            raise HTTPException(
                status_code=500, 
                detail="JWT_SECRET_KEY environment variable must be set"
            )
    
    def _validate_jwt_secret_length(self, secret: str) -> None:
        """Validate JWT secret meets minimum length requirement."""
        if len(secret) < 32:
            raise HTTPException(
                status_code=500,
                detail="JWT_SECRET_KEY must be at least 32 characters long"
            )
    
    def _get_secure_jwt_secret(self) -> str:
        """Get JWT secret with security validation."""
        secret = os.getenv("JWT_SECRET_KEY")
        self._validate_jwt_secret_exists(secret)
        self._validate_jwt_secret_length(secret)
        return secret
        
    def generate_jwt(self, user_info: UserInfo) -> str:
        """Generate JWT token with user claims."""
        now = datetime.now(timezone.utc)
        payload = self._build_jwt_payload(user_info, now)
        return jwt.encode(payload, self.jwt_secret, algorithm="HS256")
    
    def _build_jwt_payload(self, user_info: UserInfo, now: datetime) -> Dict[str, Any]:
        """Build JWT payload with standard claims."""
        return {
            "sub": user_info.get("id"), "email": user_info.get("email"),
            "name": user_info.get("name"), "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=self.token_expiry)).timestamp()),
            "iss": "netra-auth-service", "aud": "netra-api"
        }
    
    def _handle_jwt_expired(self) -> None:
        """Handle expired JWT token."""
        logger.warning("JWT token expired")
    
    def _handle_jwt_invalid(self, error: jwt.InvalidTokenError) -> None:
        """Handle invalid JWT token."""
        logger.error(f"JWT validation failed: {error}")

    def validate_jwt(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate JWT token and return claims."""
        try:
            return jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            self._handle_jwt_expired()
            return None
        except jwt.InvalidTokenError as e:
            self._handle_jwt_invalid(e)
            return None


# Import the modular AuthSessionManager
from app.auth.enhanced_auth_sessions_modular import AuthSessionManager


class OAuthSessionManager:
    """OAuth-specific session manager for auth service."""
    
    def __init__(self):
        """Initialize OAuth session manager."""
        self.session_ttl = 300  # 5 minutes
        
    async def create_oauth_state(self, pr_number: Optional[str], return_url: str) -> str:
        """Create secure OAuth state parameter."""
        csrf_token = secrets.token_urlsafe(32)
        state_data = self._build_state_data(pr_number, return_url, csrf_token)
        state_id = await self._store_state_data(state_data)
        return state_id
    
    def _build_state_data(self, pr_number: Optional[str], return_url: str, csrf_token: str) -> StateData:
        """Build OAuth state data."""
        state_data = {
            "csrf_token": csrf_token, "return_url": return_url,
            "timestamp": int(time.time())
        }
        if pr_number is not None:
            state_data["pr_number"] = pr_number
        return state_data
    
    async def _store_state_data(self, state_data: StateData) -> str:
        """Store state data in Redis and return state ID."""
        state_id = secrets.token_urlsafe(16)
        key = f"oauth_state:{state_id}"
        await redis_service.setex(key, self.session_ttl, json.dumps(state_data))
        return state_id
    
    async def validate_and_consume_state(self, state_id: str) -> StateData:
        """Validate OAuth state and consume it."""
        state_json = await redis_service.get(f"oauth_state:{state_id}")
        if not state_json:
            raise HTTPException(status_code=400, detail="Invalid or expired state")
        await redis_service.delete(f"oauth_state:{state_id}")
        return self._validate_state_data(json.loads(state_json))
    
    def _validate_state_data(self, state_data: StateData) -> StateData:
        """Validate state data timestamp and structure."""
        current_time = int(time.time())
        if current_time - state_data.get("timestamp", 0) > self.session_ttl:
            raise HTTPException(status_code=400, detail="OAuth state expired")
        return state_data


# Initialize services
auth_token_service = AuthTokenService()
auth_session_manager = OAuthSessionManager()


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


def _check_malicious_url_patterns(url: str) -> None:
    """Check for malicious URL patterns."""
    malicious_patterns = ["javascript:", "data:", "vbscript:", "file:", "ftp:"]
    if any(url.lower().startswith(pattern) for pattern in malicious_patterns):
        raise HTTPException(status_code=400, detail="Malicious URL scheme detected")

def _validate_url_length(url: str) -> None:
    """Validate URL length to prevent DoS attacks."""
    if len(url) > 2048:
        raise HTTPException(status_code=400, detail="URL too long")

def _validate_allowed_origins(url: str) -> None:
    """Validate URL against allowed origins."""
    config = auth_env_config.get_oauth_config()
    allowed_origins = config.javascript_origins
    if not any(url.startswith(origin) for origin in allowed_origins):
        raise HTTPException(status_code=400, detail="Invalid return URL origin")

def _validate_return_url_security(url: str) -> None:
    """Validate return URL for security with enhanced checks."""
    _check_malicious_url_patterns(url)
    _validate_url_length(url)
    _validate_allowed_origins(url)


def _build_oauth_params(oauth_config, state_id: str) -> Dict[str, str]:
    """Build OAuth authorization parameters."""
    return {
        "client_id": oauth_config.client_id, "redirect_uri": _get_oauth_redirect_uri(),
        "response_type": "code", "scope": "openid email profile",
        "state": state_id, "access_type": "online"
    }

def _build_google_oauth_url(oauth_config, state_id: str) -> str:
    """Build Google OAuth authorization URL."""
    params = _build_oauth_params(oauth_config, state_id)
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


def _get_environment_redirect_map() -> Dict[str, str]:
    """Get environment to redirect URI mapping."""
    return {
        "development": "http://localhost:8001/auth/callback",
        "staging": "https://auth.staging.netrasystems.ai/auth/callback",
        "production": "https://auth.netrasystems.ai/auth/callback"
    }

def _get_oauth_redirect_uri() -> str:
    """Get OAuth redirect URI based on environment."""
    redirect_map = _get_environment_redirect_map()
    env_value = auth_env_config.environment.value
    return redirect_map.get(env_value, "http://localhost:8001/auth/callback")


@app.get("/auth/callback")
async def handle_oauth_callback(request: Request, code: str, state: str):
    """Handle OAuth callback from Google."""
    state_data = await auth_session_manager.validate_and_consume_state(state)
    oauth_config = auth_env_config.get_oauth_config()
    token_data = await _exchange_code_for_tokens(code, oauth_config)
    user_info = await _get_user_info_from_google(token_data["access_token"])
    jwt_token = auth_token_service.generate_jwt(user_info)
    return _build_oauth_callback_response(state_data, jwt_token, user_info)


def _build_token_exchange_data(code: str, oauth_config) -> Dict[str, str]:
    """Build token exchange request data."""
    return {
        "code": code, "client_id": oauth_config.client_id,
        "client_secret": oauth_config.client_secret, "redirect_uri": _get_oauth_redirect_uri(),
        "grant_type": "authorization_code"
    }

async def _exchange_code_for_tokens(code: str, oauth_config) -> OAuthTokenData:
    """Exchange authorization code for access tokens."""
    token_url = "https://oauth2.googleapis.com/token"
    data = _build_token_exchange_data(code, oauth_config)
    return await _perform_token_exchange_request(token_url, data)


def _validate_token_exchange_response(response: httpx.Response) -> OAuthTokenData:
    """Validate and process token exchange response."""
    if response.status_code != 200:
        logger.error(f"Token exchange failed: {response.text}")
        raise HTTPException(status_code=400, detail="OAuth token exchange failed")
    return response.json()

def _handle_token_exchange_timeout() -> None:
    """Handle token exchange timeout errors."""
    logger.error("Token exchange request timed out")
    raise HTTPException(status_code=503, detail="OAuth service temporarily unavailable")

def _create_exchange_timeout() -> httpx.Timeout:
    """Create timeout for token exchange requests."""
    return httpx.Timeout(10.0, connect=5.0)

async def _perform_token_exchange_request(url: str, data: Dict[str, str]) -> OAuthTokenData:
    """Perform HTTP request for token exchange with timeout and security."""
    timeout = _create_exchange_timeout()
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(url, data=data)
            return _validate_token_exchange_response(response)
        except httpx.TimeoutException:
            _handle_token_exchange_timeout()


def _build_user_info_request_config(access_token: str) -> Tuple[str, Dict[str, str], httpx.Timeout]:
    """Build user info request configuration."""
    user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    timeout = httpx.Timeout(10.0, connect=5.0)
    return user_info_url, headers, timeout

def _handle_user_info_response(response: httpx.Response) -> UserInfo:
    """Handle and validate user info response."""
    if response.status_code != 200:
        logger.error(f"Failed to get user info: {response.text}")
        raise HTTPException(status_code=400, detail="Failed to retrieve user information")
    return response.json()

def _handle_user_info_timeout() -> None:
    """Handle user info request timeout."""
    logger.error("User info request timed out")
    raise HTTPException(status_code=503, detail="User info service temporarily unavailable")

async def _get_user_info_from_google(access_token: str) -> UserInfo:
    """Get user information from Google API with timeout and security."""
    url, headers, timeout = _build_user_info_request_config(access_token)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.get(url, headers=headers)
            return _handle_user_info_response(response)
        except httpx.TimeoutException:
            _handle_user_info_timeout()


def _build_standard_callback_response(return_url: str, jwt_token: str) -> RedirectResponse:
    """Build standard callback response."""
    redirect_url = f"{return_url}/auth/complete"
    response = RedirectResponse(url=redirect_url)
    _set_auth_cookies(response, jwt_token)
    return response

def _build_oauth_callback_response(state_data: StateData, jwt_token: str, user_info: UserInfo):
    """Build OAuth callback response with redirect."""
    return_url = state_data["return_url"]
    if state_data.get("pr_number"):
        return _build_pr_environment_response(return_url, jwt_token, user_info, state_data["pr_number"])
    return _build_standard_callback_response(return_url, jwt_token)


def _build_pr_environment_response(return_url: str, jwt_token: str, user_info: UserInfo, pr_number: str):
    """Build response for PR environment with token transfer."""
    redirect_url = f"{return_url}/auth/complete?token={jwt_token}"
    response = RedirectResponse(url=redirect_url)
    _set_pr_auth_cookies(response, jwt_token, pr_number)
    return response


def _set_standard_security_headers(response: Response) -> None:
    """Set standard security headers."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

def _set_auth_cookies(response: Response, jwt_token: str) -> None:
    """Set secure authentication cookies with enhanced security."""
    response.set_cookie(
        key="netra_auth_token", value=jwt_token, max_age=3600,
        secure=True, httponly=True, samesite="strict", path="/",
        domain=None  # Restrict to exact domain for security
    )
    _set_standard_security_headers(response)


def _set_pr_security_headers(response: Response) -> None:
    """Set security headers for PR environment."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'"

def _set_pr_auth_cookies(response: Response, jwt_token: str, pr_number: str) -> None:
    """Set authentication cookies for PR environment with enhanced security."""
    response.set_cookie(
        key="netra_auth_token", value=jwt_token, max_age=3600,
        secure=True, httponly=True, samesite="none", path="/",
        domain=f"pr-{pr_number}.staging.netrasystems.ai"
    )
    _set_pr_security_headers(response)


@app.post("/auth/token")
def _validate_exchange_request(code: Optional[str]) -> None:
    """Validate token exchange request."""
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code required")

def _build_token_response(jwt_token: str, user_info: UserInfo) -> Dict[str, Any]:
    """Build token exchange response."""
    return {"access_token": jwt_token, "token_type": "Bearer", "expires_in": 3600, "user_info": user_info}

async def exchange_token(request: Request):
    """Exchange OAuth code for JWT token (alternative flow)."""
    body = await request.json()
    code = body.get("code")
    _validate_exchange_request(code)
    oauth_config = auth_env_config.get_oauth_config()
    token_data = await _exchange_code_for_tokens(code, oauth_config)
    user_info = await _get_user_info_from_google(token_data["access_token"])
    jwt_token = auth_token_service.generate_jwt(user_info)
    return _build_token_response(jwt_token, user_info)


@app.post("/auth/logout")
async def _process_logout_token(auth_header: Optional[str]) -> None:
    """Process logout token if present."""
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        claims = auth_token_service.validate_jwt(token)
        if claims:
            await _revoke_user_sessions(claims.get("sub"))
            logger.info(f"User {claims.get('email')} logged out successfully")

async def logout_user(request: Request):
    """Revoke authentication tokens and logout."""
    auth_header = request.headers.get("Authorization")
    await _process_logout_token(auth_header)
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
def _build_service_status(redis_status: bool) -> Dict[str, Any]:
    """Build service status response."""
    return {
        "status": "healthy", "environment": auth_env_config.environment.value,
        "is_pr_environment": auth_env_config.is_pr_environment,
        "pr_number": auth_env_config.pr_number, "redis_connected": redis_status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

async def get_auth_service_status():
    """Get authentication service health status."""
    redis_status = await _check_redis_connection()
    return _build_service_status(redis_status)


async def _check_redis_connection() -> bool:
    """Check Redis connection status."""
    try:
        await redis_service.ping()
        return True
    except Exception:
        return False


@app.get("/auth/config")
def _add_auth_urls(config: Dict[str, Any], auth_service_url: str) -> None:
    """Add authentication URLs to config."""
    config.update({
        "auth_service_url": auth_service_url,
        "login_url": f"{auth_service_url}/auth/login",
        "logout_url": f"{auth_service_url}/auth/logout"
    })

async def get_frontend_auth_config():
    """Get frontend authentication configuration."""
    config = auth_env_config.get_frontend_config()
    auth_service_url = _get_auth_service_url()
    _add_auth_urls(config, auth_service_url)
    return config


def _get_auth_service_url_map() -> Dict[str, str]:
    """Get auth service URL mapping."""
    return {
        "development": "http://localhost:8001",
        "staging": "https://auth.staging.netrasystems.ai",
        "production": "https://auth.netrasystems.ai"
    }

def _get_auth_service_url() -> str:
    """Get auth service URL based on environment."""
    url_map = _get_auth_service_url_map()
    env_value = auth_env_config.environment.value
    return url_map.get(env_value, "http://localhost:8001")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok", "service": "netra-auth-service"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("AUTH_SERVICE_PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)