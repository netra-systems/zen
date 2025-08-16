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
from app.auth.auth import oauth_client


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


def setup_middleware(app: FastAPI) -> None:
    """Setup all middleware for the application."""
    # IP blocking should be first to reject bad IPs early
    from app.middleware.ip_blocking import ip_blocking_middleware
    app.middleware("http")(ip_blocking_middleware)
    
    setup_cors_middleware(app)
    app.middleware("http")(create_cors_redirect_middleware())
    app.middleware("http")(create_error_context_middleware())
    app.middleware("http")(create_request_logging_middleware())
    setup_session_middleware(app)


def initialize_oauth(app: FastAPI) -> None:
    """Initialize OAuth client."""
    oauth_client.init_app(app)


def register_api_routes(app: FastAPI) -> None:
    """Register all API routes."""
    _import_and_register_routes(app)


def _import_and_register_routes(app: FastAPI) -> None:
    """Import and register all route modules."""
    route_modules = _import_route_modules()
    route_configs = _get_route_configurations(route_modules)
    _register_route_modules(app, route_configs)


def _import_route_modules() -> dict:
    """Import all route modules."""
    from app.routes import (
        supply, generation, admin, references, health, 
        corpus, synthetic_data, config, demo, unified_tools, quality
    )
    from app.routes.auth import router as auth_router
    from app.routes.agent_route import router as agent_router
    from app.routes.llm_cache import router as llm_cache_router
    from app.routes.threads_route import router as threads_router
    from app.routes.health_extended import router as health_extended_router
    from app.routes.monitoring import router as monitoring_router
    from app.routes.websockets import router as websockets_router
    # from app.routes.mcp.main import router as mcp_router  # Temporarily disabled due to import issues
    return {
        "auth_router": auth_router, "agent_router": agent_router,
        "llm_cache_router": llm_cache_router, "threads_router": threads_router,
        "health_extended_router": health_extended_router, "monitoring_router": monitoring_router,
        "websockets_router": websockets_router, "supply": supply, "generation": generation,
        "admin": admin, "references": references, "health": health, "corpus": corpus,
        "synthetic_data": synthetic_data, "config": config, "demo": demo, "unified_tools": unified_tools, "quality": quality
    }


def _get_route_configurations(modules: dict) -> dict:
    """Get route configuration mapping."""
    return {
        "auth": (modules["auth_router"], "/api/auth", ["auth"]),
        "agent": (modules["agent_router"], "/api/agent", ["agent"]),
        "threads": (modules["threads_router"], "", ["threads"]),
        "llm_cache": (modules["llm_cache_router"], "/api/llm-cache", ["llm-cache"]),
        # "mcp": (modules["mcp_router"], "", ["mcp"]),  # Temporarily disabled
        "quality": (modules["quality"].router, "", ["quality"]),
        "supply": (modules["supply"].router, "/api/supply", ["supply"]),
        "generation": (modules["generation"].router, "/api/generation", ["generation"]),
        "websockets": (modules["websockets_router"], "", ["websockets"]),
        "admin": (modules["admin"].router, "/api", ["admin"]),
        "references": (modules["references"].router, "/api", ["references"]),
        "health": (modules["health"].router, "/health", ["health"]),
        "health_extended": (modules["health_extended_router"], "", ["monitoring"]),
        "monitoring": (modules["monitoring_router"], "/api", ["database-monitoring"]),
        "corpus": (modules["corpus"].router, "/api/corpus", ["corpus"]),
        "synthetic_data": (modules["synthetic_data"].router, "", ["synthetic_data"]),
        "config": (modules["config"].router, "/api", ["config"]),
        "demo": (modules["demo"].router, "", ["demo"]),
        "unified_tools": (modules["unified_tools"].router, "/api/tools", ["unified-tools"]),
    }


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
    register_error_handlers(app)
    setup_middleware(app)
    initialize_oauth(app)
    register_api_routes(app)
    setup_root_endpoint(app)
    return app