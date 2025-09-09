"""
FastAPI application factory module.
Handles application creation, router registration, and middleware setup.
"""
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

from netra_backend.app.core.app_factory_route_configs import (
    get_all_route_configurations,
)
from netra_backend.app.core.app_factory_route_imports import import_all_route_modules
from netra_backend.app.core.unified_error_handler import (
    general_exception_handler,
    http_exception_handler,
    netra_exception_handler,
    validation_exception_handler,
)
from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.core.lifespan_manager import lifespan
from netra_backend.app.core.middleware_setup import (
    create_cors_redirect_middleware,
    setup_auth_middleware,
    setup_cors_middleware,
    setup_session_middleware,
)
from netra_backend.app.core.request_context import (
    create_error_context_middleware,
    create_request_logging_middleware,
)

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
    _add_path_traversal_middleware(app)
    _add_security_headers_middleware(app)
    _add_gcp_websocket_readiness_middleware(app)


def _add_path_traversal_middleware(app: FastAPI) -> None:
    """Add path traversal protection middleware."""
    from netra_backend.app.middleware.path_traversal_protection import (
        path_traversal_protection_middleware,
    )
    app.middleware("http")(path_traversal_protection_middleware)


def _add_security_response_middleware_final(app: FastAPI) -> None:
    """Add security response middleware LAST to run FIRST (prevents information disclosure)."""
    from netra_backend.app.middleware.security_response_middleware import SecurityResponseMiddleware
    app.add_middleware(SecurityResponseMiddleware)


def _add_cors_fix_middleware(app: FastAPI) -> None:
    """Add CORS fix middleware to handle missing Access-Control-Allow-Origin header."""
    from netra_backend.app.config import get_config
    from netra_backend.app.middleware.cors_fix_middleware import CORSFixMiddleware
    settings = get_config()
    app.add_middleware(CORSFixMiddleware, environment=settings.environment)


def _add_security_headers_middleware(app: FastAPI) -> None:
    """Add security headers middleware."""
    from netra_backend.app.config import get_config
    from netra_backend.app.middleware.security_headers import SecurityHeadersMiddleware
    settings = get_config()
    app.add_middleware(SecurityHeadersMiddleware, environment=settings.environment)


def _add_gcp_websocket_readiness_middleware(app: FastAPI) -> None:
    """Add GCP WebSocket readiness middleware to prevent 1011 errors."""
    from netra_backend.app.core.middleware_setup import setup_gcp_websocket_readiness_middleware
    setup_gcp_websocket_readiness_middleware(app)


def setup_request_middleware(app: FastAPI) -> None:
    """Setup CORS, auth, error, and request logging middleware."""
    # Setup WebSocket-aware CORS middleware that excludes WebSocket upgrades
    setup_cors_middleware(app)
    
    # NOTE: WebSocket CORS is handled separately by WebSocketCORSMiddleware
    # which is applied at the ASGI level when needed. For HTTP requests,
    # the WebSocketAwareCORSMiddleware handles CORS.
    
    # Continue with HTTP middleware
    app.middleware("http")(create_cors_redirect_middleware())
    setup_auth_middleware(app)  # Add auth middleware after CORS (with WebSocket exclusions)
    app.middleware("http")(create_error_context_middleware())
    app.middleware("http")(create_request_logging_middleware())
    setup_session_middleware(app)


def setup_middleware(app: FastAPI) -> None:
    """Setup all middleware for the application."""
    # CORS middleware must be added AFTER security middleware
    # so it runs BEFORE security middleware in the request flow
    setup_request_middleware(app)  # This includes CORS
    setup_security_middleware(app)
    # Add security response middleware LAST so it runs FIRST (LIFO order)
    _add_security_response_middleware_final(app)
    # Add CORS fix middleware to handle missing Access-Control-Allow-Origin header
    _add_cors_fix_middleware(app)


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
    from netra_backend.app.logging_config import central_logger
    @app.get("/")
    def read_root():
        logger = central_logger.get_logger(__name__)
        logger.debug("Root endpoint was hit.")
        return {"message": "Welcome to Netra API"}


def create_app() -> FastAPI:
    """Create and fully configure the FastAPI application."""
    app = create_fastapi_app()
    _configure_app_handlers(app)
    _configure_app_routes(app)
    
    # Install GCP error reporting handlers if available
    _install_gcp_error_handlers(app)
    
    # Return the FastAPI app instance
    # The middleware stack including CORS is already configured on the app
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


def _install_gcp_error_handlers(app: FastAPI) -> None:
    """Install comprehensive GCP error reporting integration.
    
    This now includes:
    1. GCP Client Manager integration
    2. Python logging handler for logger.error() calls
    3. Exception handlers for unhandled exceptions
    4. FastAPI middleware for request context
    """
    try:
        from netra_backend.app.services.monitoring.gcp_error_reporter import (
            install_exception_handlers, 
            get_error_reporter
        )
        from netra_backend.app.services.monitoring.gcp_client_manager import create_gcp_client_manager
        from netra_backend.app.core.unified_logging import get_logger
        from shared.isolated_environment import get_env
        
        logger = get_logger(__name__)
        
        # Load GCP configuration
        env = get_env()
        project_id = env.get('GCP_PROJECT_ID') or env.get('GOOGLE_CLOUD_PROJECT')
        
        if not project_id:
            logger.info("No GCP project ID found, skipping GCP error reporting setup")
            return
        
        # Create and initialize GCP Client Manager
        client_manager = create_gcp_client_manager(project_id)
        
        # Get error reporter and integrate with client manager
        error_reporter = get_error_reporter()
        error_reporter.set_client_manager(client_manager)
        
        # Install all handlers (logging handler, exception handlers, middleware)
        install_exception_handlers(app)
        
        # Install authentication context middleware for enterprise error tracking
        _install_auth_context_middleware(app)
        
        logger.info("Complete GCP error reporting integration installed")
        
    except ImportError as e:
        # GCP libraries not available, skip installation
        from netra_backend.app.core.unified_logging import get_logger
        logger = get_logger(__name__)
        logger.debug(f"GCP libraries not available: {e}")
        pass
    except Exception as e:
        # Don't let error reporting setup break the app
        from netra_backend.app.core.unified_logging import get_logger
        logger = get_logger(__name__)
        logger.warning(f"Could not install GCP error handlers: {e}")


def _install_auth_context_middleware(app: FastAPI) -> None:
    """Install authentication context middleware for GCP error reporting.
    
    This middleware captures authentication context for enterprise error tracking
    and multi-user isolation in GCP Error Reporting.
    """
    try:
        from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        from netra_backend.app.core.unified_logging import get_logger
        
        logger = get_logger(__name__)
        
        # Install auth context middleware
        app.add_middleware(GCPAuthContextMiddleware, enable_user_isolation=True)
        logger.info("GCP Authentication Context Middleware installed")
        
    except ImportError as e:
        from netra_backend.app.core.unified_logging import get_logger
        logger = get_logger(__name__)
        logger.debug(f"Authentication context middleware not available: {e}")
    except Exception as e:
        from netra_backend.app.core.unified_logging import get_logger
        logger = get_logger(__name__)
        logger.warning(f"Failed to install auth context middleware: {e}")