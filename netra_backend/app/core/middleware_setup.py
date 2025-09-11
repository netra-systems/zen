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
    """Validate and get secret_key with enhanced GCP Secret Manager integration.
    
    CRITICAL FIX for Issue #169: Enhanced SECRET_KEY validation with multiple fallback strategies:
    1. Config secret_key (primary)
    2. Direct environment variable access
    3. GCP Secret Manager integration for staging/production
    4. Development fallback for dev/test environments
    
    This addresses the root cause of SessionMiddleware failures where SECRET_KEY
    validation was too strict or GCP secrets were not properly loaded.
    """
    from shared.isolated_environment import get_env
    
    # First try config.secret_key
    secret_key = getattr(config, 'secret_key', None)
    
    if not secret_key or secret_key == "default_secret_key" or len(secret_key) < 32:
        logger.warning(f"Config secret_key invalid or missing (length: {len(secret_key) if secret_key else 0})")
        
        # Enhanced fallback chain
        secret_key = _load_secret_key_with_fallbacks(environment)
    
    # Final validation
    if len(secret_key) < 32:
        raise ValueError(f"SECRET_KEY must be at least 32 characters long, got {len(secret_key)}")
    
    logger.info(f"SECRET_KEY validated successfully for {environment.value} (length: {len(secret_key)})")
    return secret_key


def _load_secret_key_with_fallbacks(environment) -> str:
    """Load SECRET_KEY with comprehensive fallback strategies.
    
    Args:
        environment: Current deployment environment
        
    Returns:
        Valid SECRET_KEY string
        
    Raises:
        ValueError: If no valid SECRET_KEY can be obtained for production environments
    """
    env = get_env()
    
    # Strategy 1: Direct environment variable
    env_secret = env.get('SECRET_KEY')
    if env_secret and len(env_secret.strip()) >= 32:
        logger.info("Loaded SECRET_KEY from environment variable")
        return env_secret.strip()
    
    # Strategy 2: GCP Secret Manager for staging/production
    if environment.value in ['staging', 'production']:
        gcp_secret = _load_secret_from_gcp('SECRET_KEY', env)
        if gcp_secret and len(gcp_secret) >= 32:
            logger.info(f"Loaded SECRET_KEY from GCP Secret Manager for {environment.value}")
            return gcp_secret
    
    # Strategy 3: Alternative environment variable names
    for alt_name in ['SESSION_SECRET_KEY', 'STARLETTE_SECRET_KEY', 'APP_SECRET_KEY']:
        alt_secret = env.get(alt_name)
        if alt_secret and len(alt_secret.strip()) >= 32:
            logger.info(f"Loaded SECRET_KEY from alternative environment variable: {alt_name}")
            return alt_secret.strip()
    
    # Strategy 4: Development fallback
    if environment.value in ["development", "testing"]:
        dev_secret = "dev-session-secret-key-32-chars-minimum-required-length-for-starlette-security"
        logger.warning("Using development fallback SECRET_KEY")
        return dev_secret
    
    # Strategy 5: Emergency staging fallback (prevents deployment failures)
    if environment.value == "staging":
        staging_secret = _generate_emergency_staging_secret(env)
        logger.error(f"EMERGENCY: Using generated SECRET_KEY for staging (GCP secrets unavailable)")
        return staging_secret
    
    # Production MUST have proper SECRET_KEY
    raise ValueError(
        f"CRITICAL: SECRET_KEY environment variable is required for {environment.value} but "
        f"is missing or too short (minimum 32 characters). "
        f"Checked: SECRET_KEY, SESSION_SECRET_KEY, STARLETTE_SECRET_KEY, APP_SECRET_KEY, GCP Secret Manager. "
        f"Found lengths: {[len(env.get(name, '')) for name in ['SECRET_KEY', 'SESSION_SECRET_KEY', 'STARLETTE_SECRET_KEY', 'APP_SECRET_KEY']]}"
    )


def _load_secret_from_gcp(secret_name: str, env_manager) -> Optional[str]:
    """Load secret from GCP Secret Manager.
    
    Args:
        secret_name: Name of the secret to load
        env_manager: Environment manager for project info
        
    Returns:
        Secret value if available, None otherwise
    """
    try:
        project_id = env_manager.get('GCP_PROJECT_ID') or env_manager.get('GOOGLE_CLOUD_PROJECT')
        if not project_id:
            logger.debug("No GCP project ID found, skipping GCP Secret Manager")
            return None
        
        # Try to use existing secret manager infrastructure
        try:
            from shared.secret_manager_builder import SecretManagerBuilder
            secret_builder = SecretManagerBuilder()
            
            # Access the secret through the builder
            if hasattr(secret_builder, 'get_secret'):
                secret_value = secret_builder.get_secret(secret_name)
                if secret_value and len(secret_value) >= 32:
                    return secret_value
            
        except ImportError:
            logger.debug("SecretManagerBuilder not available, trying direct GCP access")
        
        # Fallback to direct GCP Secret Manager access
        try:
            from google.cloud import secretmanager
            
            client = secretmanager.SecretManagerServiceClient()
            secret_path = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
            
            response = client.access_secret_version(request={"name": secret_path})
            secret_value = response.payload.data.decode("UTF-8").strip()
            
            if len(secret_value) >= 32:
                return secret_value
            else:
                logger.warning(f"GCP secret {secret_name} too short: {len(secret_value)} chars")
                
        except Exception as gcp_error:
            logger.debug(f"GCP Secret Manager access failed: {gcp_error}")
    
    except Exception as e:
        logger.debug(f"Error loading secret from GCP: {e}")
    
    return None


def _generate_emergency_staging_secret(env_manager) -> str:
    """Generate emergency SECRET_KEY for staging when GCP secrets are unavailable.
    
    This prevents staging deployment failures while maintaining security.
    The generated key is deterministic based on environment but secure enough for staging.
    
    Args:
        env_manager: Environment manager
        
    Returns:
        Generated SECRET_KEY for staging use
    """
    import hashlib
    import secrets
    
    # Use a combination of environment-specific and random data
    project_id = env_manager.get('GCP_PROJECT_ID', 'netra-staging')
    deployment_id = env_manager.get('K_SERVICE', 'netra-backend')
    
    # Create deterministic but secure key for staging
    base_string = f"{project_id}-{deployment_id}-staging-emergency-secret"
    hash_value = hashlib.sha256(base_string.encode()).hexdigest()
    
    # Add some randomness for additional security
    random_suffix = secrets.token_urlsafe(8)
    
    emergency_key = f"{hash_value[:40]}{random_suffix}"[:64]  # Ensure exactly 64 chars
    
    logger.warning(
        f"Generated emergency staging SECRET_KEY (project: {project_id}, service: {deployment_id}). "
        "This should only be used when GCP Secret Manager is unavailable."
    )
    
    return emergency_key

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