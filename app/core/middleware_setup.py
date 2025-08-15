"""
Middleware configuration module.
Handles CORS, session, and other middleware setup for FastAPI.
"""
import os
from typing import Any, Callable, Optional
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse

from app.config import settings


def get_cors_origins() -> list[str]:
    """Get CORS origins based on environment."""
    if settings.environment == "production":
        return _get_production_cors_origins()
    return _get_development_cors_origins()


def _get_production_cors_origins() -> list[str]:
    """Get CORS origins for production environment."""
    cors_origins_env = os.environ.get("CORS_ORIGINS", "")
    return cors_origins_env.split(",") if cors_origins_env else ["https://netra.ai"]


def _get_development_cors_origins() -> list[str]:
    """Get CORS origins for development environment."""
    #cors_origins_env = os.environ.get("CORS_ORIGINS", "")
    #if cors_origins_env:
    #    return cors_origins_env.split(",")
    return ["*"]


def setup_cors_middleware(app: FastAPI) -> None:
    """Configure CORS middleware."""
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
    return isinstance(response, RedirectResponse) and settings.environment != "production"


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


def setup_session_middleware(app: FastAPI) -> None:
    """Setup session middleware."""
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        same_site="lax",
        https_only=(settings.environment == "production"),
    )