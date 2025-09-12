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
    """Setup authentication middleware with enhanced WebSocket exclusion.
    
    CRITICAL FIX: Enhanced WebSocket exclusion to prevent routing.py line 716 errors
    by ensuring WebSocket upgrade requests bypass HTTP authentication middleware completely.
    """
    from netra_backend.app.middleware.fastapi_auth_middleware import FastAPIAuthMiddleware
    
    # ENHANCED WebSocket exclusions - more comprehensive to prevent routing issues
    websocket_exclusions = [
        # Standard exclusions
        "/health", "/metrics", "/", "/docs", "/openapi.json", "/redoc",
        
        # Enhanced WebSocket exclusions - CRITICAL for preventing routing.py errors
        "/ws", "/websocket", "/ws/", "/websocket/",  # Base WebSocket paths
        "/ws/test", "/ws/config", "/ws/health", "/ws/stats",  # WebSocket endpoints
        "/api/v1/ws", "/api/v1/websocket",  # API WebSocket paths
        "/api/ws", "/api/websocket",  # Alternative API WebSocket paths
        
        # Auth service endpoints that must bypass middleware
        "/api/v1/auth",  # Auth service integration endpoints
        "/api/auth",  # Direct auth endpoints (login, register, etc.)
        "/auth",  # OAuth callbacks and public auth endpoints
        "/api/v1/auth/",  # Ensure trailing slash variants are excluded
        "/api/auth/",
        "/auth/",
        
        # Additional paths that could interfere with WebSocket upgrades
        "/favicon.ico",  # Prevent favicon requests from interfering
        "/robots.txt",   # Prevent robots.txt from interfering
        "/.well-known/", # OAuth/security endpoints
    ]
    
    # Add authentication middleware with comprehensive exclusions
    app.add_middleware(
        FastAPIAuthMiddleware,
        excluded_paths=websocket_exclusions
    )
    logger.info(f"Authentication middleware configured with enhanced WebSocket exclusions ({len(websocket_exclusions)} excluded paths)")
    logger.debug(f"WebSocket exclusion paths: {[path for path in websocket_exclusions if 'ws' in path.lower()]}")


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
    
    CRITICAL FIX for Starlette routing.py line 716 errors and WebSocket middleware exclusion:
    
    MIDDLEWARE ORDER (applied in reverse):
    1. Session middleware FIRST - Required for request.session access
    2. WebSocket exclusion middleware - Prevents HTTP middleware from processing WebSocket upgrades
    3. GCP Auth Context middleware - AFTER session, needs request.session 
    4. CORS middleware - Cross-origin handling with WebSocket exclusion
    5. Authentication middleware - AFTER CORS, with WebSocket path exclusion
    6. GCP WebSocket readiness - Environment specific
    7. CORS redirect middleware - Last in chain, HTTP only
    
    This order ensures:
    - SessionMiddleware is available before any middleware tries to access request.session
    - WebSocket connections bypass HTTP middleware that could cause upgrade failures
    - ASGI scope is protected from corruption during WebSocket handshake
    """
    logger.info("Starting enhanced middleware setup with WebSocket exclusion support...")
    
    try:
        # PHASE 1: Core Infrastructure Middleware
        # SESSION MIDDLEWARE MUST BE FIRST - All other middleware may depend on it
        logger.debug("Setting up session middleware (Phase 1)...")
        setup_session_middleware(app)
        
        # PHASE 2: WebSocket Protection Middleware
        # Add WebSocket-aware middleware wrapper to prevent HTTP middleware interference
        logger.debug("Setting up WebSocket exclusion middleware (Phase 2)...")
        _add_websocket_exclusion_middleware(app)
        
        # PHASE 3: Authentication and Context Middleware  
        # GCP Authentication Context middleware AFTER session (needs request.session access)
        logger.debug("Setting up GCP auth context middleware (Phase 3)...")
        setup_gcp_auth_context_middleware(app)
        
        # PHASE 4: Request Handling Middleware
        # CORS middleware handles cross-origin requests with WebSocket awareness
        logger.debug("Setting up WebSocket-aware CORS middleware (Phase 4)...")
        setup_cors_middleware(app)
        
        # Authentication middleware AFTER CORS (with enhanced WebSocket exclusion)
        logger.debug("Setting up authentication middleware with WebSocket exclusion (Phase 4)...")
        setup_auth_middleware(app)
        
        # PHASE 5: Environment Specific Middleware
        # GCP WebSocket readiness middleware (staging/production only)
        logger.debug("Setting up GCP WebSocket readiness middleware (Phase 5)...")
        setup_gcp_websocket_readiness_middleware(app)
        
        # PHASE 6: Final Request Processing (HTTP only)
        # CORS redirect middleware (handles redirects with proper CORS headers, HTTP only)
        logger.debug("Setting up HTTP-only CORS redirect middleware (Phase 6)...")
        cors_redirect = _create_http_only_cors_redirect_middleware()
        app.middleware("http")(cors_redirect)
        
        # Validation: Ensure session middleware and WebSocket exclusion are properly installed
        _validate_session_middleware_installation(app)
        _validate_websocket_exclusion_setup(app)
        
        logger.info("Enhanced middleware setup completed with WebSocket exclusion and proper SessionMiddleware order")
        
    except Exception as e:
        logger.error(f"CRITICAL: Enhanced middleware setup failed: {e}")
        # Enhanced error logging for debugging
        logger.error(f"Middleware setup failure details: {type(e).__name__}: {str(e)}", exc_info=e)
        raise RuntimeError(f"Failed to setup enhanced middleware with WebSocket exclusion: {e}")


def _add_websocket_exclusion_middleware(app: FastAPI) -> None:
    """Add WebSocket exclusion middleware to prevent HTTP middleware from processing WebSocket upgrades.
    
    CRITICAL FIX: This middleware ensures that WebSocket connections bypass HTTP middleware
    that could interfere with the WebSocket upgrade process, preventing routing.py line 716 errors.
    """
    try:
        from netra_backend.app.middleware.websocket_exclusion_middleware import WebSocketExclusionMiddleware
        app.add_middleware(WebSocketExclusionMiddleware)
        logger.info("WebSocket exclusion middleware installed successfully")
    except ImportError:
        # Create the middleware inline if not available
        logger.info("Creating WebSocket exclusion middleware inline")
        _create_inline_websocket_exclusion_middleware(app)
    except Exception as e:
        logger.error(f"Error setting up WebSocket exclusion middleware: {e}")
        # Don't fail app startup if middleware setup fails
        pass


def _create_inline_websocket_exclusion_middleware(app: FastAPI) -> None:
    """Create WebSocket exclusion middleware inline with ASGI scope protection."""
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.types import ASGIApp, Receive, Scope, Send
    from fastapi import Request, Response
    
    class WebSocketExclusionMiddleware(BaseHTTPMiddleware):
        """Middleware that excludes WebSocket connections with ASGI scope protection."""
        
        async def dispatch(self, request: Request, call_next) -> Response:
            """Only process HTTP requests with enhanced scope protection."""
            try:
                # ASGI Scope Protection: Validate request object before processing
                if not hasattr(request, 'url') or not hasattr(request.url, 'path'):
                    logger.warning("Invalid request object detected in WebSocket exclusion middleware")
                    # Create a minimal response to prevent routing errors
                    from fastapi.responses import JSONResponse
                    return JSONResponse(
                        status_code=400, 
                        content={"error": "invalid_request", "message": "Invalid request format"}
                    )
                
                # Additional scope validation
                if hasattr(request, 'scope') and request.scope:
                    scope_type = request.scope.get('type', 'unknown')
                    if scope_type == 'websocket':
                        # This should not happen in HTTP middleware, but protect against it
                        logger.warning("WebSocket scope detected in HTTP middleware - potential routing error")
                        # Bypass processing for safety
                        return await call_next(request)
                
                # Normal HTTP request processing
                return await call_next(request)
                
            except AttributeError as e:
                logger.error(f"ASGI Scope AttributeError in WebSocket exclusion: {e}")
                # Return safe response to prevent routing.py line 716 errors
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=500,
                    content={"error": "scope_error", "message": "Request scope validation failed"}
                )
            except Exception as e:
                logger.error(f"Unexpected error in WebSocket exclusion middleware: {e}")
                # Pass through to prevent breaking the request chain
                return await call_next(request)
        
        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
            """ASGI middleware call with enhanced scope protection and validation."""
            try:
                # Phase 1: Scope Type Validation
                scope_type = scope.get("type", "unknown")
                
                if scope_type == "websocket":
                    # CRITICAL: WebSocket connections bypass ALL HTTP middleware
                    logger.debug("WebSocket connection detected - bypassing HTTP middleware stack")
                    await self.app(scope, receive, send)
                    return
                
                elif scope_type == "http":
                    # Phase 2: HTTP Scope Validation and Protection
                    if not self._validate_http_scope(scope):
                        logger.warning("Invalid HTTP scope detected - applying protective measures")
                        await self._send_safe_http_response(send, scope)
                        return
                    
                    # Normal HTTP processing with scope protection
                    await super().__call__(scope, receive, send)
                    return
                    
                else:
                    # Phase 3: Unknown scope type protection
                    logger.warning(f"Unknown ASGI scope type: {scope_type} - passing through safely")
                    await self.app(scope, receive, send)
                    return
                    
            except Exception as e:
                logger.error(f"CRITICAL: ASGI scope error in WebSocket exclusion: {e}")
                # Send safe error response to prevent routing failures
                if scope.get("type") == "http":
                    await self._send_safe_http_response(send, scope, error_message=str(e))
                else:
                    # For non-HTTP scopes, try to pass through safely
                    try:
                        await self.app(scope, receive, send)
                    except:
                        logger.error("Failed to pass through non-HTTP scope safely")
        
        def _validate_http_scope(self, scope: Scope) -> bool:
            """Validate HTTP scope to prevent 'URL' object attribute errors."""
            try:
                # Check required HTTP scope components
                required_keys = ["method", "path", "query_string", "headers"]
                for key in required_keys:
                    if key not in scope:
                        logger.warning(f"Missing required HTTP scope key: {key}")
                        return False
                
                # Validate path is string-like
                path = scope.get("path")
                if not isinstance(path, str):
                    logger.warning(f"Invalid path type in HTTP scope: {type(path)}")
                    return False
                
                return True
                
            except Exception as e:
                logger.error(f"HTTP scope validation error: {e}")
                return False
        
        async def _send_safe_http_response(self, send: Send, scope: Scope, error_message: str = None) -> None:
            """Send a safe HTTP response for invalid scopes."""
            try:
                # Send HTTP response start
                await send({
                    "type": "http.response.start",
                    "status": 400,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", b"77"),  # Length of JSON response below
                    ],
                })
                
                # Send HTTP response body
                error_detail = error_message or "Invalid request scope"
                response_body = f'{{"error": "scope_validation_failed", "message": "{error_detail}"}}'
                await send({
                    "type": "http.response.body",
                    "body": response_body.encode("utf-8"),
                })
                
            except Exception as e:
                logger.error(f"Failed to send safe HTTP response: {e}")
                # Last resort - send minimal response
                try:
                    await send({"type": "http.response.start", "status": 500, "headers": []})
                    await send({"type": "http.response.body", "body": b"Server Error"})
                except:
                    logger.critical("Could not send any HTTP response - connection may be broken")
    
    app.add_middleware(WebSocketExclusionMiddleware)
    logger.info("Enhanced WebSocket exclusion middleware with ASGI scope protection created and installed")


def _create_http_only_cors_redirect_middleware() -> Callable:
    """Create CORS redirect middleware that only processes HTTP requests.
    
    CRITICAL FIX: This ensures WebSocket connections don't get processed by CORS redirect logic
    that could cause scope corruption and routing.py errors.
    """
    async def http_only_cors_redirect_middleware(request: Request, call_next: Callable) -> Any:
        """Handle CORS for redirects (HTTP only) - WebSocket connections bypass this."""
        # This middleware only handles HTTP requests
        # WebSocket upgrade requests are excluded automatically by FastAPI's HTTP middleware system
        response = await call_next(request)
        process_cors_if_needed(request, response)
        return response
    return http_only_cors_redirect_middleware


def _validate_websocket_exclusion_setup(app: FastAPI) -> None:
    """Validate that WebSocket exclusion middleware is properly set up."""
    try:
        # Check if WebSocket exclusion middleware is installed
        websocket_exclusion_found = False
        
        for middleware in app.user_middleware:
            middleware_class = middleware.cls
            if hasattr(middleware_class, '__name__'):
                if 'WebSocketExclusion' in middleware_class.__name__ or 'websocket_exclusion' in middleware_class.__name__.lower():
                    websocket_exclusion_found = True
                    logger.debug(f"Found WebSocket exclusion middleware: {middleware_class.__name__}")
                    break
        
        if websocket_exclusion_found:
            logger.info("✅ WebSocket exclusion middleware validation successful")
        else:
            logger.warning("⚠️ WebSocket exclusion middleware not detected - WebSocket connections may experience routing issues")
    
    except Exception as e:
        logger.warning(f"WebSocket exclusion validation error (non-fatal): {e}")
        # Don't fail deployment due to validation errors
        pass


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
            logger.info(" PASS:  SessionMiddleware installation validated successfully")
        else:
            logger.error(" FAIL:  SessionMiddleware not found in middleware stack - this will cause request.session errors")
            
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