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
    return _get_default_staging_origins()

def _get_default_staging_origins() -> list[str]:
    """Get default staging CORS origins."""
    staging_domains = _get_staging_domains()
    cloud_run_origins = _get_cloud_run_origins()
    localhost_origins = _get_localhost_origins() 
    return staging_domains + cloud_run_origins + localhost_origins + ["*"]

def _get_staging_domains() -> list[str]:
    """Get staging domain origins."""
    return [
        "https://staging.netrasystems.ai",
        "https://app.staging.netrasystems.ai",
        "https://auth.staging.netrasystems.ai",
        "https://backend.staging.netrasystems.ai"
    ]

def _get_cloud_run_origins() -> list[str]:
    """Get Cloud Run origins."""
    return [
        "https://netra-frontend-701982941522.us-central1.run.app",
        "https://netra-backend-701982941522.us-central1.run.app"
    ]

def _get_localhost_origins() -> list[str]:
    """Get localhost origins."""
    return ["http://localhost:3000", "http://localhost:3001"]


def _get_development_cors_origins() -> list[str]:
    """Get CORS origins for development environment."""
    cors_origins_env = os.environ.get("CORS_ORIGINS", "")
    if cors_origins_env:
        return _handle_dev_env_origins(cors_origins_env)
    return _get_default_dev_origins()

def _handle_dev_env_origins(cors_origins_env: str) -> list[str]:
    """Handle development environment origins from env var."""
    if cors_origins_env == "*":
        return ["*"]
    return cors_origins_env.split(",")

def _get_default_dev_origins() -> list[str]:
    """Get default development origins."""
    return ["http://localhost:3000", "http://localhost:8000", "*"]


def setup_cors_middleware(app: FastAPI) -> None:
    """Configure CORS middleware."""
    if settings.environment in ["staging", "development"]:
        _setup_custom_cors_middleware(app)
    else:
        _setup_production_cors_middleware(app)

def _setup_custom_cors_middleware(app: FastAPI) -> None:
    """Setup custom CORS middleware for staging/development."""
    app.add_middleware(CustomCORSMiddleware)

def _setup_production_cors_middleware(app: FastAPI) -> None:
    """Setup production CORS middleware."""
    allowed_origins = get_cors_origins()
    cors_config = _get_production_cors_config(allowed_origins)
    app.add_middleware(CORSMiddleware, **cors_config)

def _get_production_cors_config(allowed_origins: list[str]) -> dict:
    """Get production CORS configuration."""
    return {
        "allow_origins": allowed_origins,
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
        "allow_headers": ["Authorization", "Content-Type", "X-Request-ID", "X-Trace-ID", "Accept", "Origin", "Referer", "X-Requested-With"],
        "expose_headers": ["X-Trace-ID", "X-Request-ID", "Content-Length", "Content-Type"]
    }


def should_add_cors_headers(response: Any) -> bool:
    """Check if CORS headers should be added to response."""
    return isinstance(response, RedirectResponse) and settings.environment in ["development", "staging"]


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


def is_origin_allowed(origin: str, allowed_origins: List[str]) -> bool:
    """Check if origin matches allowed patterns including wildcards."""
    if not origin:
        return False
    return _perform_origin_checks(origin, allowed_origins)

def _perform_origin_checks(origin: str, allowed_origins: List[str]) -> bool:
    """Perform all origin validation checks."""
    if _check_direct_origin_match(origin, allowed_origins):
        return True
    if _check_wildcard_match(allowed_origins):
        return True
    return _check_pattern_matches(origin)


def _check_direct_origin_match(origin: str, allowed_origins: List[str]) -> bool:
    """Check if origin has direct match in allowed origins."""
    return origin in allowed_origins


def _check_wildcard_match(allowed_origins: List[str]) -> bool:
    """Check if wildcard allows all origins based on environment."""
    if "*" not in allowed_origins:
        return False
    return _evaluate_wildcard_environment()

def _evaluate_wildcard_environment() -> bool:
    """Evaluate if current environment allows wildcards."""
    if settings.environment == "development":
        return True
    return settings.environment not in ["staging"]


def _check_pattern_matches(origin: str) -> bool:
    """Check if origin matches environment-specific patterns."""
    if settings.environment not in ["staging", "development"]:
        return False
    return _evaluate_pattern_matches(origin)

def _evaluate_pattern_matches(origin: str) -> bool:
    """Evaluate all pattern matches for origin."""
    return (
        _check_staging_domain_pattern(origin) or
        _check_cloud_run_patterns(origin) or
        _check_localhost_pattern(origin)
    )


def _check_staging_domain_pattern(origin: str) -> bool:
    """Check if origin matches staging domain pattern."""
    staging_pattern = r'^https://[a-zA-Z0-9\-]+\.staging\.netrasystems\.ai$'
    return bool(re.match(staging_pattern, origin))


def _check_cloud_run_patterns(origin: str) -> bool:
    """Check if origin matches any Cloud Run URL pattern."""
    patterns = _get_cloud_run_patterns()
    return any(re.match(pattern, origin) for pattern in patterns)

def _get_cloud_run_patterns() -> list[str]:
    """Get Cloud Run URL patterns."""
    return [
        r'^https://[a-zA-Z0-9\-]+(-[a-zA-Z0-9]+)*-[a-z]{2}\.a\.run\.app$',
        r'^https://netra-(frontend|backend)-[a-zA-Z0-9\-]+\.(us-central1|europe-west1|asia-northeast1)\.run\.app$',
        r'^https://netra-frontend-[0-9]+\.(us-central1|europe-west1|asia-northeast1)\.run\.app$'
    ]


def _check_localhost_pattern(origin: str) -> bool:
    """Check if origin matches localhost pattern."""
    localhost_pattern = r'^https?://(localhost|127\.0\.0\.1)(:\d+)?$'
    return bool(re.match(localhost_pattern, origin))


class CustomCORSMiddleware(BaseHTTPMiddleware):
    """Custom CORS middleware with wildcard subdomain support."""
    
    async def dispatch(self, request: Request, call_next):
        """Handle CORS with wildcard support."""
        origin = request.headers.get("origin")
        response = await self._handle_request(request, call_next)
        await self._process_cors_response(response, origin)
        return response

    async def _handle_request(self, request: Request, call_next) -> Response:
        """Handle request and return response."""
        if request.method == "OPTIONS":
            response = Response(status_code=200)
            origin = request.headers.get("origin")
            if origin:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD"
                response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Request-ID, X-Trace-ID, Accept, Origin, Referer, X-Requested-With"
                response.headers["Access-Control-Max-Age"] = "3600"
            return response
        return await call_next(request)

    async def _process_cors_response(self, response: Response, origin: Optional[str]) -> None:
        """Process CORS headers for response."""
        if not origin:
            return
        allowed_origins = get_cors_origins()
        if is_origin_allowed(origin, allowed_origins):
            self._add_cors_headers(response, origin)
        else:
            self._log_cors_rejection(origin, allowed_origins)

    def _add_cors_headers(self, response: Response, origin: str) -> None:
        """Add CORS headers to response."""
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD"
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Request-ID, X-Trace-ID, Accept, Origin, Referer, X-Requested-With"
        response.headers["Access-Control-Expose-Headers"] = "X-Trace-ID, X-Request-ID, Content-Length, Content-Type"

    def _log_cors_rejection(self, origin: str, allowed_origins: list[str]) -> None:
        """Log CORS rejection for debugging."""
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"CORS: Origin {origin} not allowed. Allowed: {allowed_origins}")


def setup_session_middleware(app: FastAPI) -> None:
    """Setup session middleware."""
    from app.clients.auth_client import auth_client
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
    return any([
        "localhost" in os.getenv("FRONTEND_URL", ""),
        "localhost" in os.getenv("API_URL", ""),
        os.getenv("PORT", "8000") in ["8000", "3000", "3010"],
    ])

def _create_session_config(is_localhost: bool, is_deployed: bool) -> dict:
    """Create session configuration dictionary."""
    if is_localhost or os.getenv("DISABLE_HTTPS_ONLY") == "true":
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
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        same_site=session_config["same_site"],
        https_only=session_config["https_only"],
        max_age=3600,  # 1 hour session
    )