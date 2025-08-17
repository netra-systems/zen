"""
Middleware configuration module.
Handles CORS, session, and other middleware setup for FastAPI.
"""
import os
import re
from typing import Any, Callable, Optional, List
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


def get_cors_origins() -> list[str]:
    """Get CORS origins based on environment."""
    if settings.environment == "production":
        return _get_production_cors_origins()
    elif settings.environment == "staging":
        return _get_staging_cors_origins()
    return _get_development_cors_origins()


def _get_production_cors_origins() -> list[str]:
    """Get CORS origins for production environment."""
    cors_origins_env = os.environ.get("CORS_ORIGINS", "")
    return cors_origins_env.split(",") if cors_origins_env else ["https://netrasystems.ai"]


def _get_staging_cors_origins() -> list[str]:
    """Get CORS origins for staging environment."""
    cors_origins_env = os.environ.get("CORS_ORIGINS", "")
    if cors_origins_env:
        return cors_origins_env.split(",")
    # Staging origins - will be handled by custom middleware for wildcards
    return [
        "https://staging.netrasystems.ai",
        "https://app.staging.netrasystems.ai",
        "https://auth.staging.netrasystems.ai",
        "https://backend.staging.netrasystems.ai",
        "https://netra-frontend-701982941522.us-central1.run.app",
        "https://netra-backend-701982941522.us-central1.run.app",
        "http://localhost:3000",
        "http://localhost:3001",
        "*"  # Will use pattern matching in is_origin_allowed
    ]


def _get_development_cors_origins() -> list[str]:
    """Get CORS origins for development environment."""
    cors_origins_env = os.environ.get("CORS_ORIGINS", "")
    if cors_origins_env:
        # Handle wildcard separately - don't try to split it
        if cors_origins_env == "*":
            return ["*"]
        return cors_origins_env.split(",")
    # Allow all localhost origins in development (any port)
    return ["http://localhost:3000", "http://localhost:8000", "*"]


def setup_cors_middleware(app: FastAPI) -> None:
    """Configure CORS middleware."""
    if settings.environment in ["staging", "development"]:
        # Use custom middleware for staging and development to support wildcards
        app.add_middleware(CustomCORSMiddleware)
    else:
        # Use standard CORS middleware for production
        allowed_origins = get_cors_origins()
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Trace-ID"],
            expose_headers=["X-Trace-ID", "X-Request-ID"],
        )


def should_add_cors_headers(response: Any) -> bool:
    """Check if CORS headers should be added to response."""
    return isinstance(response, RedirectResponse) and settings.environment in ["development", "staging"]


def add_cors_headers_to_response(response: Any, origin: str) -> None:
    """Add CORS headers to response."""
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Request-ID, X-Trace-ID"


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


def is_origin_allowed(origin: str, allowed_origins: List[str]) -> bool:
    """Check if origin matches allowed patterns including wildcards."""
    if not origin:
        return False
    
    # Direct match first
    if origin in allowed_origins:
        return True
    
    # Allow all origins if wildcard is specified
    if "*" in allowed_origins:
        # In development, allow everything
        if settings.environment == "development":
            return True
        # In staging, check patterns below instead of allowing all
        if settings.environment == "staging":
            pass  # Continue to pattern matching below
        else:
            return True
    
    # Check wildcard patterns for staging and development
    if settings.environment in ["staging", "development"]:
        # Allow any subdomain of staging.netrasystems.ai
        staging_pattern = r'^https://[a-zA-Z0-9\-]+\.staging\.netrasystems\.ai$'
        if re.match(staging_pattern, origin):
            return True
        
        # Allow Google Cloud Run URLs (backend services)
        # Pattern matches: https://service-name-hash-region.a.run.app
        cloud_run_pattern = r'^https://[a-zA-Z0-9\-]+(-[a-zA-Z0-9]+)*-[a-z]{2}\.a\.run\.app$'
        if re.match(cloud_run_pattern, origin):
            return True
        
        # Allow localhost for local development - any port
        localhost_pattern = r'^https?://(localhost|127\.0\.0\.1)(:\d+)?$'
        if re.match(localhost_pattern, origin):
            return True
        
        # Allow Cloud Run URLs
        cloud_run_pattern = r'^https://netra-(frontend|backend)-[a-zA-Z0-9\-]+\.(us-central1|europe-west1|asia-northeast1)\.run\.app$'
        if re.match(cloud_run_pattern, origin):
            return True
    
    return False


class CustomCORSMiddleware(BaseHTTPMiddleware):
    """Custom CORS middleware with wildcard subdomain support."""
    
    async def dispatch(self, request: Request, call_next):
        """Handle CORS with wildcard support."""
        origin = request.headers.get("origin")
        
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response(status_code=200)
        else:
            response = await call_next(request)
        
        # Add CORS headers if origin is allowed
        allowed_origins = get_cors_origins()
        if origin and is_origin_allowed(origin, allowed_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Request-ID, X-Trace-ID"
            response.headers["Access-Control-Expose-Headers"] = "X-Trace-ID, X-Request-ID"
        elif origin:
            # Log for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"CORS: Origin {origin} not allowed. Allowed: {allowed_origins}")
        
        return response


def setup_session_middleware(app: FastAPI) -> None:
    """Setup session middleware."""
    # Import auth config to get actual environment
    from app.auth.environment_config import auth_env_config
    
    # Determine if we're actually in production/staging (deployed)
    is_deployed = auth_env_config.environment.value in ["production", "staging"]
    is_localhost = any([
        "localhost" in os.getenv("FRONTEND_URL", ""),
        "localhost" in os.getenv("API_URL", ""),
        os.getenv("PORT", "8000") in ["8000", "3000", "3010"],
    ])
    
    # For OAuth to work properly:
    # - localhost needs same_site="lax" and https_only=False
    # - deployed needs same_site="none" and https_only=True
    if is_localhost or os.getenv("DISABLE_HTTPS_ONLY") == "true":
        same_site = "lax"
        https_only = False
    else:
        same_site = "none" if is_deployed else "lax"
        https_only = is_deployed
    
    # Log session configuration for debugging
    import logging
    logger = logging.getLogger(__name__)
    logger.info(
        f"Session middleware config: same_site={same_site}, "
        f"https_only={https_only}, environment={auth_env_config.environment.value}"
    )
    
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        same_site=same_site,
        https_only=https_only,
        max_age=3600,  # 1 hour session
    )