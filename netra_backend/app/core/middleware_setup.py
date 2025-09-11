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


def setup_gcp_websocket_readiness_middleware(app: FastAPI) -> None:
    """
    Setup GCP WebSocket readiness middleware to prevent 1011 errors.
    
    CRITICAL: This middleware prevents GCP Cloud Run from accepting WebSocket
    connections before required services are ready, which causes 1011 errors.
    
    SSOT COMPLIANCE: Uses the unified GCP WebSocket initialization validator.
    """
    try:
        from netra_backend.app.middleware.gcp_websocket_readiness_middleware import (
            GCPWebSocketReadinessMiddleware
        )
        from shared.isolated_environment import get_env
        
        env_manager = get_env()
        environment = env_manager.get('ENVIRONMENT', '').lower()
        is_gcp = environment in ['staging', 'production']
        
        # Only add middleware in GCP environments
        if is_gcp:
            # GCP environments need longer timeout due to Cloud SQL connection delays
            timeout_seconds = 90.0 if environment == 'staging' else 60.0
            
            app.add_middleware(
                GCPWebSocketReadinessMiddleware,
                timeout_seconds=timeout_seconds
            )
            logger.info(f"GCP WebSocket readiness middleware added for {environment} environment (timeout: {timeout_seconds}s)")
        else:
            logger.debug(f"GCP WebSocket readiness middleware skipped for {environment} environment")
            
    except ImportError as e:
        logger.warning(f"GCP WebSocket readiness middleware not available: {e}")
    except Exception as e:
        logger.error(f"Error setting up GCP WebSocket readiness middleware: {e}")
        # Don't fail app startup if middleware setup fails
        pass


def setup_session_middleware(app: FastAPI) -> None:
    """Setup session middleware with enhanced error handling for staging deployment.
    
    CRITICAL FIX: Added comprehensive error handling and environment variable
    validation to prevent 'SessionMiddleware must be installed to access request.session' errors.
    """
    try:
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        auth_client = AuthServiceClient()
        current_environment = auth_client.detect_environment()
        session_config = _determine_session_config(current_environment)
        _log_session_config(session_config, current_environment)
        _add_session_middleware_with_validation(app, session_config, current_environment)
        logger.info(f"SessionMiddleware successfully configured for {current_environment.value}")
    except Exception as e:
        logger.error(f"CRITICAL: SessionMiddleware setup failed: {e}")
        # Fallback to basic session middleware to prevent deployment failures
        _add_fallback_session_middleware(app)
        raise RuntimeError(f"SessionMiddleware configuration failed: {e}")

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

def _add_session_middleware_with_validation(app: FastAPI, session_config: dict, environment) -> None:
    """Add session middleware to app with validation.
    
    CRITICAL FIX: Enhanced validation prevents staging deployment failures
    due to missing or invalid SECRET_KEY environment variables.
    """
    config = get_configuration()
    
    # CRITICAL: Validate secret_key before using it
    secret_key = _validate_and_get_secret_key(config, environment)
    
    # Log session middleware configuration for debugging
    logger.info(
        f"Adding SessionMiddleware: same_site={session_config['same_site']}, "
        f"https_only={session_config['https_only']}, environment={environment.value}, "
        f"secret_key_length={len(secret_key) if secret_key else 0}"
    )
    
    app.add_middleware(
        SessionMiddleware,
        secret_key=secret_key,
        same_site=session_config["same_site"],
        https_only=session_config["https_only"],
        max_age=3600,  # 1 hour session
    )

def _validate_and_get_secret_key(config, environment) -> str:
    """Validate and get secret_key using unified secret management.
    
    CRITICAL FIX for Issue #169: Uses UnifiedSecretManager for consistent secret loading
    across all deployment environments, eliminating the root cause of SessionMiddleware failures.
    
    This replaces multiple inconsistent secret loading patterns with a single SSOT approach.
    """
    from netra_backend.app.core.unified_secret_manager import get_session_secret
    
    # First try config.secret_key for backward compatibility
    config_secret = getattr(config, 'secret_key', None)
    if config_secret and config_secret != "default_secret_key" and len(config_secret) >= 32:
        logger.info(f"Using config.secret_key for {environment.value} (length: {len(config_secret)})")
        return config_secret
    
    # Use unified secret manager for comprehensive secret loading
    try:
        secret_info = get_session_secret(environment.value)
        
        if secret_info.is_fallback:
            logger.warning(f"Using fallback SECRET_KEY for {environment.value} "
                          f"(source: {secret_info.source.value})")
        
        if secret_info.is_generated:
            logger.error(f"Using generated SECRET_KEY for {environment.value} "
                        f"- GCP Secret Manager may be unavailable")
        
        # Log validation notes for debugging
        for note in secret_info.validation_notes:
            logger.debug(f"SECRET_KEY validation: {note}")
        
        logger.info(f"SECRET_KEY loaded via UnifiedSecretManager for {environment.value} "
                   f"(source: {secret_info.source.value}, length: {secret_info.length})")
        
        return secret_info.value
        
    except Exception as e:
        logger.error(f"UnifiedSecretManager failed to load SECRET_KEY: {e}")
        
        # Final emergency fallback to prevent deployment failures
        if environment.value in ["development", "testing"]:
            emergency_key = "emergency-dev-session-secret-key-32-chars-minimum-required-for-starlette"
            logger.warning(f"Using emergency development SECRET_KEY for {environment.value}")
            return emergency_key
        else:
            # For production/staging, we must fail if we can't get a proper secret
            raise ValueError(
                f"CRITICAL: Could not load SECRET_KEY for {environment.value} environment. "
                f"UnifiedSecretManager error: {e}. "
                "Check GCP Secret Manager configuration and environment variables."
            )


# Legacy secret loading functions removed - now handled by UnifiedSecretManager
# This eliminates duplicate secret management code and consolidates to SSOT pattern

def _add_fallback_session_middleware(app: FastAPI) -> None:
    """Add basic session middleware as fallback to prevent deployment failures.
    
    This ensures the app can start even if configuration loading fails.
    """
    logger.warning("Adding fallback SessionMiddleware with basic configuration")
    
    # Generate a basic session key (not for production use)
    fallback_key = "fallback-session-key-32-chars-minimum-required-for-emergency-deployment"
    
    app.add_middleware(
        SessionMiddleware,
        secret_key=fallback_key,
        same_site="lax",
        https_only=False,
        max_age=3600,
    )

def _add_session_middleware(app: FastAPI, session_config: dict) -> None:
    """Legacy session middleware setup - kept for backward compatibility."""
    config = get_configuration()
    app.add_middleware(
        SessionMiddleware,
        secret_key=config.secret_key,
        same_site=session_config["same_site"],
        https_only=session_config["https_only"],
        max_age=3600,  # 1 hour session
    )


def setup_gcp_auth_context_middleware(app: FastAPI) -> None:
    """Setup GCP Authentication Context middleware for error reporting and user isolation.
    
    CRITICAL FIX: This function integrates GCPAuthContextMiddleware into the SSOT middleware setup.
    The middleware MUST be installed AFTER SessionMiddleware to ensure request.session access.
    
    Business Value Justification:
    - Enterprise customers require GDPR/SOX compliance with user-specific error tracking
    - Multi-user error isolation enables proper enterprise audit requirements
    - Proper middleware order prevents Golden Path authentication failures
    """
    try:
        from shared.middleware.gcp_auth_context import GCPAuthContextMiddleware
        from shared.isolated_environment import get_env
        
        env_manager = get_env()
        environment = env_manager.get('ENVIRONMENT', '').lower()
        project_id = env_manager.get('GCP_PROJECT_ID') or env_manager.get('GOOGLE_CLOUD_PROJECT')
        
        # Only install in environments with GCP error reporting
        if project_id and environment in ['staging', 'production']:
            app.add_middleware(GCPAuthContextMiddleware, enable_user_isolation=True)
            logger.info(f"GCP Authentication Context Middleware installed for {environment} environment")
        else:
            logger.debug(f"GCP Auth Context middleware skipped for environment: {environment}, project_id: {bool(project_id)}")
            
    except ImportError as e:
        # Try fallback import from netra_backend
        try:
            from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
            from shared.isolated_environment import get_env
            
            env_manager = get_env()
            environment = env_manager.get('ENVIRONMENT', '').lower()
            project_id = env_manager.get('GCP_PROJECT_ID') or env_manager.get('GOOGLE_CLOUD_PROJECT')
            
            # Only install in environments with GCP error reporting
            if project_id and environment in ['staging', 'production']:
                app.add_middleware(GCPAuthContextMiddleware, enable_user_isolation=True)
                logger.info(f"GCP Authentication Context Middleware installed (fallback import) for {environment}")
            else:
                logger.debug(f"GCP Auth Context middleware skipped (fallback), environment: {environment}")
                
        except ImportError:
            logger.warning(f"GCP Authentication Context Middleware not available: {e}")
    except Exception as e:
        logger.error(f"Error setting up GCP Authentication Context middleware: {e}")
        # Don't fail app startup if middleware setup fails
        pass


def setup_middleware(app: FastAPI) -> None:
    """
    Main middleware setup function - SSOT for all middleware configuration.
    
    CRITICAL FIX for Issue #169: Middleware registration order fixed to prevent SessionMiddleware errors.
    
    MIDDLEWARE ORDER (applied in reverse):
    1. Session middleware FIRST - Required for request.session access
    2. GCP Auth Context middleware - AFTER session, needs request.session 
    3. CORS middleware - Cross-origin handling
    4. Authentication middleware - AFTER CORS, needs session data
    5. GCP WebSocket readiness - Environment specific
    6. CORS redirect middleware - Last in chain
    
    This order ensures SessionMiddleware is available before any middleware tries to access request.session.
    """
    logger.info("Starting middleware setup with proper order for SessionMiddleware...")
    
    try:
        # PHASE 1: Core Infrastructure Middleware
        # SESSION MIDDLEWARE MUST BE FIRST - All other middleware may depend on it
        logger.debug("Setting up session middleware (Phase 1)...")
        setup_session_middleware(app)
        
        # PHASE 2: Authentication and Context Middleware  
        # GCP Authentication Context middleware AFTER session (needs request.session access)
        logger.debug("Setting up GCP auth context middleware (Phase 2)...")
        setup_gcp_auth_context_middleware(app)
        
        # PHASE 3: Request Handling Middleware
        # CORS middleware handles cross-origin requests
        logger.debug("Setting up CORS middleware (Phase 3)...")
        setup_cors_middleware(app)
        
        # Authentication middleware AFTER CORS (needs session and CORS headers)
        logger.debug("Setting up authentication middleware (Phase 3)...")
        setup_auth_middleware(app)
        
        # PHASE 4: Environment Specific Middleware
        # GCP WebSocket readiness middleware (staging/production only)
        logger.debug("Setting up GCP WebSocket readiness middleware (Phase 4)...")
        setup_gcp_websocket_readiness_middleware(app)
        
        # PHASE 5: Final Request Processing
        # CORS redirect middleware (handles redirects with proper CORS headers)
        logger.debug("Setting up CORS redirect middleware (Phase 5)...")
        cors_redirect = create_cors_redirect_middleware()
        app.middleware("http")(cors_redirect)
        
        # Validation: Ensure session middleware is properly installed
        _validate_session_middleware_installation(app)
        
        logger.info("All middleware setup completed successfully with proper SessionMiddleware order")
        
    except Exception as e:
        logger.error(f"CRITICAL: Middleware setup failed: {e}")
        # Enhanced error logging for debugging
        logger.error(f"Middleware setup failure details: {type(e).__name__}: {str(e)}", exc_info=e)
        raise RuntimeError(f"Failed to setup middleware: {e}")


def _validate_session_middleware_installation(app: FastAPI) -> None:
    """Validate that SessionMiddleware is properly installed.
    
    CRITICAL FIX for Issue #169: Post-installation validation to catch configuration issues early.
    
    Args:
        app: FastAPI application instance
    """
    try:
        # Check if any SessionMiddleware is installed
        session_middleware_found = False
        
        for middleware in app.user_middleware:
            middleware_class = middleware.cls
            if hasattr(middleware_class, '__name__'):
                if 'SessionMiddleware' in middleware_class.__name__:
                    session_middleware_found = True
                    logger.debug(f"Found SessionMiddleware: {middleware_class.__name__}")
                    break
        
        if session_middleware_found:
            logger.info("✅ SessionMiddleware installation validated successfully")
        else:
            logger.error("❌ SessionMiddleware not found in middleware stack - this will cause request.session errors")
            
            # Log all installed middleware for debugging
            middleware_list = []
            for middleware in app.user_middleware:
                middleware_list.append(middleware.cls.__name__ if hasattr(middleware.cls, '__name__') else str(middleware.cls))
            
            logger.error(f"Installed middleware: {middleware_list}")
            
            # This is a warning, not a fatal error, to prevent deployment failures
            logger.warning("SessionMiddleware validation failed - authentication may not work properly")
    
    except Exception as e:
        logger.warning(f"SessionMiddleware validation error (non-fatal): {e}")
        # Don't fail deployment due to validation errors
        pass