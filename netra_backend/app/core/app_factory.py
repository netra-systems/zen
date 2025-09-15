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
from netra_backend.app.core.telemetry_bootstrap import bootstrap_telemetry
from netra_backend.app.core.sentry_integration import initialize_sentry

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
    """Setup all middleware for the application - DELEGATES TO SSOT.
    
    CRITICAL FIX: This function now delegates to the SSOT middleware setup
    in middleware_setup.py to prevent SessionMiddleware order issues that
    cause WebSocket 1011 internal errors.
    """
    # CRITICAL: Use the SSOT middleware setup function instead of duplicated logic
    # This ensures SessionMiddleware is installed FIRST as required
    from netra_backend.app.core.middleware_setup import setup_middleware as ssot_setup_middleware
    ssot_setup_middleware(app)
    
    # Legacy setup removed - using SSOT setup_middleware from middleware_setup.py
    # The SSOT version ensures proper middleware order: Session -> CORS -> Auth -> GCP


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
    # Initialize observability stack BEFORE creating FastAPI app to ensure automatic instrumentation
    _initialize_telemetry()
    _initialize_sentry()
    
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


def _initialize_telemetry() -> None:
    """Initialize OpenTelemetry automatic instrumentation.
    
    Called early in application startup to ensure instrumentation is active
    before FastAPI app creation and middleware setup.
    """
    try:
        success = bootstrap_telemetry()
        if success:
            # Use standard logging since central_logger may not be fully initialized yet
            import logging
            logging.info("OpenTelemetry automatic instrumentation initialized successfully")
        else:
            import logging
            logging.debug("OpenTelemetry initialization skipped (disabled or unavailable)")
    except Exception as e:
        # Don't let telemetry initialization break the app
        import logging
        logging.warning(f"Failed to initialize telemetry: {e}")


def _initialize_sentry() -> None:
    """Initialize Sentry error tracking and performance monitoring.
    
    Called early in application startup alongside telemetry initialization
    to ensure error tracking is active before application startup.
    """
    try:
        from netra_backend.app.config import get_config
        config = get_config()
        
        success = initialize_sentry(config)
        if success:
            # Use standard logging since central_logger may not be fully initialized yet
            import logging
            logging.info("Sentry error tracking initialized successfully")
        else:
            import logging
            logging.debug("Sentry initialization skipped (disabled or unavailable)")
    except Exception as e:
        # Don't let Sentry initialization break the app
        import logging
        logging.warning(f"Failed to initialize Sentry: {e}")


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
        
        # Note: Authentication context middleware is now handled by SSOT setup_middleware()
        # in middleware_setup.py to ensure proper dependency order with SessionMiddleware
        
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


