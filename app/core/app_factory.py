"""
FastAPI application factory module.
Handles application creation, router registration, and middleware setup.
"""
from fastapi import FastAPI
from pydantic import ValidationError
from fastapi import HTTPException

from app.core.lifespan_manager import lifespan
from app.core.middleware_setup import (
    setup_cors_middleware, 
    create_cors_redirect_middleware,
    setup_session_middleware
)
from app.core.request_context import (
    create_error_context_middleware,
    create_request_logging_middleware
)
from app.core.exceptions_base import NetraException
from app.core.error_handlers import (
    netra_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler,
)
from .app_factory_route_imports import import_all_route_modules
from .app_factory_route_configs import get_all_route_configurations
# OAuth now handled by auth service


def create_fastapi_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(lifespan=lifespan)
    return app


# Startup and shutdown events now handled by lifespan manager


def register_error_handlers(app: FastAPI) -> None:
    """Register application error handlers."""
    app.add_exception_handler(NetraException, netra_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)


def setup_security_middleware(app: FastAPI) -> None:
    """Setup security middleware components."""
    _add_ip_blocking_middleware(app)
    _add_path_traversal_middleware(app)
    _add_security_headers_middleware(app)


def _add_ip_blocking_middleware(app: FastAPI) -> None:
    """Add IP blocking middleware."""
    from app.middleware.ip_blocking import ip_blocking_middleware
    app.middleware("http")(ip_blocking_middleware)


def _add_path_traversal_middleware(app: FastAPI) -> None:
    """Add path traversal protection middleware."""
    from app.middleware.path_traversal_protection import path_traversal_protection_middleware
    app.middleware("http")(path_traversal_protection_middleware)


def _add_security_headers_middleware(app: FastAPI) -> None:
    """Add security headers middleware."""
    from app.middleware.security_headers import SecurityHeadersMiddleware
    from app.config import settings
    app.add_middleware(SecurityHeadersMiddleware, environment=settings.environment)


def setup_request_middleware(app: FastAPI) -> None:
    """Setup CORS, error, and request logging middleware."""
    setup_cors_middleware(app)
    app.middleware("http")(create_cors_redirect_middleware())
    app.middleware("http")(create_error_context_middleware())
    app.middleware("http")(create_request_logging_middleware())
    setup_session_middleware(app)


def setup_middleware(app: FastAPI) -> None:
    """Setup all middleware for the application."""
    setup_security_middleware(app)
    setup_request_middleware(app)


def initialize_oauth(app: FastAPI) -> None:
    """Initialize OAuth client."""
    # OAuth now handled by auth service - no initialization needed
    pass


def register_api_routes(app: FastAPI) -> None:
    """Register all API routes."""
    _import_and_register_routes(app)


def _import_and_register_routes(app: FastAPI) -> None:
    """Import and register all route modules."""
    route_modules = import_all_route_modules()
    route_configs = get_all_route_configurations(route_modules)
    _register_route_modules(app, route_configs)


def _register_route_modules(app: FastAPI, routes: dict) -> None:
    """Register route modules with the app."""
    for name, (router, prefix, tags) in routes.items():
        app.include_router(router, prefix=prefix, tags=tags)


def setup_root_endpoint(app: FastAPI) -> None:
    """Setup the root API endpoint."""
    from app.logging_config import central_logger
    @app.get("/")
    def read_root():
        logger = central_logger.get_logger(__name__)
        logger.info("Root endpoint was hit.")
        return {"message": "Welcome to Netra API"}


def create_app() -> FastAPI:
    """Create and fully configure the FastAPI application."""
    app = create_fastapi_app()
    _configure_app_handlers(app)
    _configure_app_routes(app)
    return app


def _configure_app_handlers(app: FastAPI) -> None:
    """Configure error handlers and middleware."""
    register_error_handlers(app)
    setup_middleware(app)
    initialize_oauth(app)


def _configure_app_routes(app: FastAPI) -> None:
    """Configure application routes."""
    register_api_routes(app)
    setup_root_endpoint(app)