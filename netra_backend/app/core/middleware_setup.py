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
from netra_backend.app.core.websocket_cors import configure_websocket_cors
from shared.cors_config import get_fastapi_cors_config

logger = logging.getLogger(__name__)


# Legacy CORS functions removed - now using unified shared.cors_config


# Legacy CORS origin functions removed - unified config handles this


def setup_cors_middleware(app: FastAPI) -> None:
    """Configure CORS middleware using unified configuration.
    
    Note: This excludes WebSocket upgrade requests which are handled by WebSocketCORSMiddleware.
    """
    config = get_configuration()
    cors_config = get_fastapi_cors_config(config.environment)
    
    # Add custom CORS middleware that excludes WebSocket upgrades
    app.add_middleware(
        WebSocketAwareCORSMiddleware, 
        **cors_config
    )
    logger.info(f"WebSocket-aware CORS middleware configured for environment: {config.environment}")


class WebSocketAwareCORSMiddleware(CORSMiddleware):
    """CORS middleware that excludes WebSocket upgrade requests."""
    
    async def __call__(self, scope, receive, send) -> None:
        """Process requests, excluding WebSocket upgrades."""
        # Check if this is a WebSocket upgrade request
        if self._is_websocket_upgrade_request(scope):
            # Skip CORS processing for WebSocket upgrades - let WebSocketCORSMiddleware handle it
            await self.app(scope, receive, send)
            return
        
        # Process regular HTTP requests with CORS
        await super().__call__(scope, receive, send)
    
    def _is_websocket_upgrade_request(self, scope) -> bool:
        """Check if the request is a WebSocket upgrade."""
        if scope.get("type") != "http":
            return False
        
        # Check for WebSocket upgrade headers
        headers = dict(scope.get("headers", []))
        
        upgrade_header = headers.get(b"upgrade", b"").decode("latin1").lower()
        connection_header = headers.get(b"connection", b"").decode("latin1").lower()
        
        is_websocket = (
            upgrade_header == "websocket" and 
            "upgrade" in connection_header
        )
        
        # Debug logging to understand what's happening
        if is_websocket:
            logger.info(f"WebSocket upgrade detected - skipping CORS: upgrade={upgrade_header}, connection={connection_header}")
        
        return is_websocket


def should_add_cors_headers(response: Any) -> bool:
    """Check if CORS headers should be added to response."""
    config = get_configuration()
    return isinstance(response, RedirectResponse) and config.environment in ["development", "staging"]


def add_cors_headers_to_response(response: Any, origin: str) -> None:
    """Add CORS headers to response."""
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD"
    response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Request-ID, X-Trace-ID, Accept, Origin, Referer, X-Requested-With"


def process_cors_if_needed(request: Request, response: Any) -> None:
    """Process CORS headers if needed."""
    if should_add_cors_headers(response):
        origin = request.headers.get("origin")
        if origin:
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
    
    # Add authentication middleware to the app
    app.add_middleware(
        FastAPIAuthMiddleware,
        excluded_paths=["/health", "/metrics", "/", "/docs", "/openapi.json", "/redoc"]
    )
    logger.info("Authentication middleware configured")


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
    logger.info(
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