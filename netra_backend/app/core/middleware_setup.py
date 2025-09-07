"""
Middleware configuration module.
Handles CORS, session, and other middleware setup for FastAPI.
"""
import logging
import os
from typing import Any, Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse, Response

from netra_backend.app.core.configuration import get_configuration
from shared.cors_config_builder import CORSConfigurationBuilder

logger = logging.getLogger(__name__)


# Legacy CORS functions removed - now using unified shared.cors_config


# Legacy CORS origin functions removed - unified config handles this


def setup_cors_middleware(app: FastAPI) -> None:
    """Configure CORS middleware using CORSConfigurationBuilder."""
    config = get_configuration()
    
    # Initialize CORS configuration builder
    cors = CORSConfigurationBuilder()
    cors_config = cors.fastapi.get_middleware_config()
    
    # Debug logging to understand CORS configuration
    logger.debug(f"CORS Configuration for {cors.environment}:")
    logger.debug(f"  Origins count: {len(cors_config.get('allow_origins', []))}")
    logger.debug(f"  Allow credentials: {cors_config.get('allow_credentials')}")
    logger.debug(f"  First 3 origins: {cors_config.get('allow_origins', [])[:3]}")
    
    # Use standard FastAPI CORSMiddleware
    # WebSocket CORS is handled separately by WebSocketCORSMiddleware at the ASGI level
    app.add_middleware(
        CORSMiddleware, 
        **cors_config
    )
    logger.debug(f"CORS middleware configured for environment: {cors.environment}")


# WebSocketAwareCORSMiddleware removed - using standard CORSMiddleware
# WebSocket CORS is handled separately at the ASGI level by WebSocketCORSMiddleware


def should_add_cors_headers(response: Any) -> bool:
    """Check if CORS headers should be added to response."""
    config = get_configuration()
    return isinstance(response, RedirectResponse) and config.environment in ["development", "staging"]


def add_cors_headers_to_response(response: Any, origin: str) -> None:
    """Add CORS headers to response with security enhancements."""
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD"
    response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Request-ID, X-Trace-ID, Accept, Origin, Referer, X-Requested-With, X-Service-Name"
    # CORS-005: Add Vary: Origin header to prevent CDN cache poisoning
    response.headers["Vary"] = "Origin"
    # CORS-006: Add Access-Control-Max-Age for preflight caching
    response.headers["Access-Control-Max-Age"] = "3600"


def process_cors_if_needed(request: Request, response: Any) -> None:
    """Process CORS headers if needed with security logging."""
    if should_add_cors_headers(response):
        origin = request.headers.get("origin")
        if origin:
            # Log CORS redirect handling for security monitoring
            config = get_configuration()
            request_id = request.headers.get("x-request-id", "unknown")
            
            # Use CORSConfigurationBuilder for security event logging
            cors = CORSConfigurationBuilder()
            cors.security.log_security_event(
                event_type="cors_redirect_handling",
                origin=origin,
                path=request.url.path,
                request_id=request_id
            )
            add_cors_headers_to_response(response, origin)


def create_cors_redirect_middleware() -> Callable:
    """Create CORS redirect middleware."""
    async def cors_redirect_middleware(request: Request, call_next: Callable) -> Any:
        """Handle CORS for redirects (e.g., trailing slash redirects)."""
        response = await call_next(request)
        process_cors_if_needed(request, response)
        return response
    return cors_redirect_middleware


# Legacy pattern matching functions removed - unified config handles origin validation


# CustomCORSMiddleware removed - now using FastAPI's built-in CORSMiddleware with unified config


def setup_auth_middleware(app: FastAPI) -> None:
    """Setup authentication middleware."""
    from netra_backend.app.middleware.fastapi_auth_middleware import FastAPIAuthMiddleware
    
    # Add authentication middleware to the app - CRITICAL: exclude WebSocket paths
    # WebSocket connections handle authentication differently and must not be processed
    # by HTTP authentication middleware as it will block the upgrade process
    app.add_middleware(
        FastAPIAuthMiddleware,
        excluded_paths=[
            "/health", "/metrics", "/", "/docs", "/openapi.json", "/redoc",
            "/ws", "/websocket", "/ws/test", "/ws/config", "/ws/health", "/ws/stats",
            "/api/v1/auth",  # Auth service integration endpoints
            "/api/auth",  # Direct auth endpoints (login, register, etc.)
            "/auth"  # OAuth callbacks and public auth endpoints
        ]
    )
    logger.debug("Authentication middleware configured with WebSocket exclusions")


def setup_session_middleware(app: FastAPI) -> None:
    """Setup session middleware."""
    from netra_backend.app.clients.auth_client_core import AuthServiceClient
    auth_client = AuthServiceClient()
    current_environment = auth_client.detect_environment()
    session_config = _determine_session_config(current_environment)
    _log_session_config(session_config, current_environment)
    _add_session_middleware(app, session_config)

def _determine_session_config(current_environment) -> dict:
    """Determine session configuration based on environment."""
    is_deployed = current_environment.value in ["production", "staging"]
    is_localhost = _check_localhost_environment()
    return _create_session_config(is_localhost, is_deployed)

def _check_localhost_environment() -> bool:
    """Check if running in localhost environment."""
    config = get_configuration()
    return any([
        "localhost" in config.frontend_url,
        "localhost" in config.api_base_url,
        config.environment == "development",
    ])

def _create_session_config(is_localhost: bool, is_deployed: bool) -> dict:
    """Create session configuration dictionary."""
    config = get_configuration()
    disable_https = getattr(config, 'disable_https_only', False)
    if is_localhost or disable_https:
        return {"same_site": "lax", "https_only": False}
    return {
        "same_site": "none" if is_deployed else "lax",
        "https_only": is_deployed
    }

def _log_session_config(session_config: dict, current_environment) -> None:
    """Log session configuration for debugging."""
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(
        f"Session middleware config: same_site={session_config['same_site']}, "
        f"https_only={session_config['https_only']}, environment={current_environment.value}"
    )

def _add_session_middleware(app: FastAPI, session_config: dict) -> None:
    """Add session middleware to app."""
    config = get_configuration()
    app.add_middleware(
        SessionMiddleware,
        secret_key=config.secret_key,
        same_site=session_config["same_site"],
        https_only=session_config["https_only"],
        max_age=3600,  # 1 hour session
    )