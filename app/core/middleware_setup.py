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
    # Staging origins - will be handled by custom middleware
    return [
        "https://staging.netrasystems.ai",
        "https://app.staging.netrasystems.ai",
        "https://auth.staging.netrasystems.ai",
        "https://backend.staging.netrasystems.ai",
        "https://netra-frontend-701982941522.us-central1.run.app",
        "https://netra-backend-701982941522.us-central1.run.app",
        "http://localhost:3000",
        "http://localhost:3001"
    ]


def _get_development_cors_origins() -> list[str]:
    """Get CORS origins for development environment."""
    cors_origins_env = os.environ.get("CORS_ORIGINS", "")
    if cors_origins_env:
        return cors_origins_env.split(",")
    # Restrict to localhost origins only in development
    return [
        "http://localhost:3000",
        "http://localhost:3001", 
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]


def setup_cors_middleware(app: FastAPI) -> None:
    """Configure CORS middleware."""
    if settings.environment == "staging":
        # Use custom middleware for staging to support wildcard subdomains
        app.add_middleware(CustomCORSMiddleware)
    else:
        # Use standard CORS middleware for other environments
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
    
    # Direct match
    if origin in allowed_origins:
        return True
    
    # Check wildcard patterns for staging
    if settings.environment == "staging":
        # Allow any subdomain of staging.netrasystems.ai
        pattern = r'^https://[a-zA-Z0-9\-]+\.staging\.netrasystems\.ai$'
        if re.match(pattern, origin):
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
        if origin and (origin == "*" in allowed_origins or 
                      is_origin_allowed(origin, allowed_origins)):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Request-ID, X-Trace-ID"
            response.headers["Access-Control-Expose-Headers"] = "X-Trace-ID, X-Request-ID"
        
        return response


def setup_session_middleware(app: FastAPI) -> None:
    """Setup session middleware."""
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        same_site="lax",
        https_only=(settings.environment == "production"),
    )