"""
Auth Service Main Application
Standalone microservice for authentication
"""
import os
import sys
import signal
import asyncio
from pathlib import Path

# Add parent directory to Python path for auth_service imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, Dict

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

# Import auth service isolated environment first to handle bootstrap
from shared.isolated_environment import get_env
from shared.environment_loading_ssot import StartupEnvironmentManager, AUTH_CONFIG

# CRITICAL: Initialize environment using SSOT implementation
env = get_env()
startup_manager = StartupEnvironmentManager(env)
result = startup_manager.setup_service_environment(AUTH_CONFIG)

# Enhanced verification with dev launcher detection capability
if result.loaded and env.get('SERVICE_SECRET'):
    print("SERVICE_SECRET successfully loaded from .env")
elif not result.loaded and result.dev_launcher_detected:
    print("Auth Service: Dev launcher environment detected - using pre-configured variables")
elif not result.loaded and not env.get('SERVICE_SECRET'):
    print("WARNING: SERVICE_SECRET not found - check environment configuration")

# NOW import auth service modules after environment is properly initialized
from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.routes.auth_routes import router as auth_router, oauth_router
from shared.logging import get_logger, configure_service_logging
from shared.cors_config_builder import CORSConfigurationBuilder

# Import new JWT SSOT remediation APIs
from auth_service.auth_core.api.jwt_validation import router as jwt_validation_router
from auth_service.auth_core.api.websocket_auth import router as websocket_auth_router  
from auth_service.auth_core.api.service_auth import router as service_auth_router

# Configure unified logging for auth service
configure_service_logging({
    'service_name': 'auth-service',
    'enable_file_logging': True
})
logger = get_logger(__name__)

# Global shutdown event for graceful shutdown
shutdown_event = asyncio.Event()

# Graceful shutdown handlers
def signal_handler(signum: int, frame):
    """Handle shutdown signals gracefully"""
    signal_name = signal.Signals(signum).name
    logger.info(f"Received {signal_name} signal, initiating graceful shutdown...")
    shutdown_event.set()

def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    # Handle SIGTERM (Cloud Run shutdown signal)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Handle SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)
    
    # On Windows, also handle SIGBREAK
    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, signal_handler)
    
    logger.info("Signal handlers configured for graceful shutdown")

# Setup signal handlers early
setup_signal_handlers()

# Simplified Health Interface for Auth Service
class AuthServiceHealthInterface:
    """Simple health interface for auth service."""
    
    def __init__(self, service_name: str, version: str = "1.0.0"):
        self.service_name = service_name
        self.version = version
        self.start_time = datetime.now(UTC)
    
    def get_basic_health(self) -> Dict[str, Any]:
        """Get basic health status."""
        return {
            "status": "healthy",
            "service": self.service_name,
            "version": self.version,
            "timestamp": datetime.now(UTC).isoformat(),
            "uptime_seconds": self._get_uptime_seconds()
        }
    
    def _get_uptime_seconds(self) -> float:
        """Calculate service uptime in seconds."""
        return (datetime.now(UTC) - self.start_time).total_seconds()

# Initialize health interface
health_interface = AuthServiceHealthInterface("auth-service", "1.0.0")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle with optimized startup and graceful shutdown"""
    logger.info("Starting Auth Service...")
    
    # Log configuration
    from auth_service.auth_core.config import AuthConfig
    AuthConfig.log_configuration()
    # @marked: Port must be read from environment for container deployment
    logger.info(f"Port: {get_env().get('PORT', '8080')}")
    
    # CRITICAL OAUTH VALIDATION - FAIL FAST IF OAUTH IS BROKEN
    env = AuthConfig.get_environment()
    if env in ["staging", "production"]:
        logger.info("🔐 VALIDATING CRITICAL OAUTH CONFIGURATION...")
        oauth_validation_errors = []
        
        # Check Google Client ID
        google_client_id = AuthConfig.get_google_client_id()
        if not google_client_id:
            # TOMBSTONE: GOOGLE_CLIENT_ID variable superseded by environment-specific GOOGLE_OAUTH_CLIENT_ID_* variables
            oauth_validation_errors.append("Google OAuth client ID is not configured")
            logger.error("❌ CRITICAL: Google OAuth client ID is missing!")
        elif len(google_client_id) < 50:
            oauth_validation_errors.append(f"Google OAuth client ID appears too short: {google_client_id[:20]}...")
            logger.error(f"❌ CRITICAL: Google OAuth client ID appears too short: {google_client_id[:20]}...")
        elif not google_client_id.endswith(".apps.googleusercontent.com"):
            oauth_validation_errors.append(f"Google OAuth client ID has invalid format (should end with .apps.googleusercontent.com): {google_client_id}")
            logger.error(f"❌ CRITICAL: Google OAuth client ID has invalid format: {google_client_id}")
        else:
            logger.info(f"✅ Google OAuth client ID configured: {google_client_id[:20]}...")
        
        # Check Google Client Secret
        google_client_secret = AuthConfig.get_google_client_secret()
        if not google_client_secret:
            # TOMBSTONE: GOOGLE_CLIENT_SECRET variable superseded by environment-specific GOOGLE_OAUTH_CLIENT_SECRET_* variables
            oauth_validation_errors.append("Google OAuth client secret is not configured")
            logger.error("❌ CRITICAL: Google OAuth client secret is missing!")
        elif len(google_client_secret) < 20:
            oauth_validation_errors.append(f"Google OAuth client secret appears too short")
            logger.error(f"❌ CRITICAL: Google OAuth client secret appears too short")
        else:
            logger.info("✅ Google OAuth client secret configured")
        
        # Check environment variables that were actually loaded
        env_manager = get_env()
        # TOMBSTONE: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET superseded by environment-specific variables
        checked_env_vars = {
            "GOOGLE_OAUTH_CLIENT_ID_STAGING": env_manager.get("GOOGLE_OAUTH_CLIENT_ID_STAGING"),
            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": env_manager.get("GOOGLE_OAUTH_CLIENT_SECRET_STAGING"),
            "ENVIRONMENT": env_manager.get("ENVIRONMENT")
        }
        
        logger.info("🔍 OAuth Environment Variables Status:")
        for var_name, var_value in checked_env_vars.items():
            if var_value:
                if "SECRET" in var_name:
                    logger.info(f"  {var_name}: [CONFIGURED - {len(var_value)} chars]")
                else:
                    logger.info(f"  {var_name}: {var_value[:50]}{'...' if len(var_value) > 50 else ''}")
            else:
                logger.warning(f"  {var_name}: [NOT SET]")
        
        # FAIL FAST if OAuth is broken in staging/production
        if oauth_validation_errors:
            error_message = f"""
🚨🚨🚨 CRITICAL OAUTH CONFIGURATION FAILURE 🚨🚨🚨

Environment: {env}
Auth Service CANNOT START due to missing/invalid OAuth configuration!

Errors found:
{chr(10).join(f"  - {error}" for error in oauth_validation_errors)}

Environment variables checked:
{chr(10).join(f"  - {var}: {'SET' if val else 'MISSING'}" for var, val in checked_env_vars.items())}

This is a FATAL ERROR in {env} environment. 
OAuth functionality will be completely broken without proper configuration.

Required actions:
1. Set proper Google OAuth credentials using environment-specific variables (e.g. GOOGLE_OAUTH_CLIENT_ID_STAGING)
2. Ensure Cloud Run deployment has access to the secrets
3. Verify OAuth credentials are valid in Google Cloud Console

Auth Service startup ABORTED.
🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨
"""
            logger.error(error_message)
            raise RuntimeError(f"OAuth configuration validation failed in {env}: {', '.join(oauth_validation_errors)}")
        
        logger.info("✅ OAuth configuration validation PASSED")
        
        # ADDITIONAL VALIDATION: Verify OAuth provider can initialize
        logger.info("🔍 Verifying OAuth provider initialization...")
        try:
            from auth_service.auth_core.oauth_manager import OAuthManager
            oauth_manager = OAuthManager()
            
            # Check if Google provider is available and configured
            available_providers = oauth_manager.get_available_providers()
            if "google" not in available_providers:
                raise RuntimeError("Google OAuth provider not available after configuration validation")
            
            # Verify Google provider is properly configured
            if not oauth_manager.is_provider_configured("google"):
                raise RuntimeError("Google OAuth provider not properly configured")
            
            # Try to get the Google provider instance
            google_provider = oauth_manager.get_provider("google")
            if not google_provider:
                raise RuntimeError("Failed to get Google OAuth provider instance")
            
            # Verify provider can generate authorization URL (without actually making a request)
            try:
                test_url = google_provider.get_authorization_url("test-state-validation")
                if not test_url or "accounts.google.com" not in test_url:
                    raise RuntimeError(f"Invalid authorization URL generated: {test_url[:50] if test_url else 'None'}")
                logger.info("✅ OAuth provider can generate valid authorization URLs")
            except Exception as url_error:
                raise RuntimeError(f"OAuth provider cannot generate authorization URLs: {url_error}")
            
            logger.info(f"✅ OAuth provider initialization verified - {len(available_providers)} provider(s) available")
            
        except Exception as provider_error:
            error_msg = f"OAuth provider validation failed: {provider_error}"
            logger.error(f"❌ CRITICAL: {error_msg}")
            raise RuntimeError(f"OAuth provider initialization failed in {env}: {error_msg}")
            
    else:
        logger.info(f"Skipping OAuth validation in {env} environment")
    
    # Log Redis configuration status
    try:
        from auth_service.auth_core.routes.auth_routes import auth_service
        # Check if redis_client is available (AuthService uses redis_client, not session_manager)
        if hasattr(auth_service, 'redis_client'):
            redis_enabled = auth_service.redis_client is not None
            redis_status = "enabled" if redis_enabled else "disabled"
        else:
            # Redis client might not be initialized yet
            redis_status = "will be configured during route initialization"
        logger.info(f"Redis session management: {redis_status}")
    except Exception as e:
        logger.warning(f"Could not determine Redis status: {e}")
        redis_status = "status unknown"
    
    # Check if we're in fast test mode
    # @marked: Test mode flag for test infrastructure
    fast_test_mode = get_env().get("AUTH_FAST_TEST_MODE", "false").lower() == "true"
    env = AuthConfig.get_environment()
    
    if fast_test_mode or env == "test":
        logger.info("Running in fast test mode - skipping database initialization")
        yield
        return
    
    # Initialize single database connection
    from auth_service.auth_core.database.connection import auth_db
    
    # Initialize auth database (builds URL from POSTGRES_* variables)
    try:
        await auth_db.initialize()
        logger.info("🔌 AUTH DATABASE: Connection initialized")
        
        # Verify database connectivity immediately
        db_ready = await auth_db.is_ready()
        if not db_ready:
            raise RuntimeError("Database initialization succeeded but connectivity test failed")
        
        logger.info("✅ AUTH DATABASE: Connected and verified - User data persistence ENABLED")
        
    except Exception as e:
        error_msg = str(e) if str(e) else f"{type(e).__name__}: {repr(e)}"
        logger.error(f"❌ AUTH DATABASE: Connection FAILED - {error_msg}")
        
        # FAIL FAST: Do not start service if database is unavailable
        # This prevents misleading "healthy" status when critical dependencies are down
        if env in ["staging", "production"]:
            logger.critical(f"🚨 FATAL: Database required in {env.upper()} - Service cannot start!")
            raise RuntimeError(f"Database initialization failed in {env}: {error_msg}")
        elif env == "development":
            # Development can continue without database for basic testing
            logger.warning(f"⚠️ AUTH DATABASE: Running in STATELESS mode (JWT validation only) - {error_msg}")
            logger.warning(f"⚠️ AUTH DATABASE: User persistence DISABLED - OAuth login will not persist users")
        else:
            # Unknown environment - be conservative and fail
            logger.critical(f"🚨 FATAL: Database required in {env.upper()} - Service cannot start!")
            raise RuntimeError(f"Database initialization failed in {env}: {error_msg}")
    
    logger.info("Auth Service startup completed")
    
    yield
    
    # Graceful shutdown
    logger.info("Shutting down Auth Service...")
    
    # Skip waiting for shutdown event in development - proceed directly to cleanup
    env = AuthConfig.get_environment()
    if env == "development":
        logger.info("Development environment - proceeding directly to cleanup")
    else:
        # Wait for shutdown signal with timeout to prevent hanging (production/staging only)
        try:
            # Set a timeout for graceful shutdown (Cloud Run gives 10 seconds by default)
            shutdown_timeout = float(get_env().get("SHUTDOWN_TIMEOUT_SECONDS", "3"))
            logger.info(f"Waiting up to {shutdown_timeout} seconds for graceful shutdown...")
            
            # Use asyncio.wait_for with proper timeout handling
            await asyncio.wait_for(shutdown_event.wait(), timeout=shutdown_timeout)
            logger.info("Shutdown signal received, proceeding with cleanup")
        except asyncio.TimeoutError:
            logger.info(f"Shutdown timeout ({shutdown_timeout}s) reached, proceeding with cleanup")
        except Exception as e:
            logger.warning(f"Error during shutdown wait: {e}, proceeding with cleanup")
    
    # Close connections gracefully
    tasks = []
    
    # Close database connection safely
    async def close_database():
        try:
            await auth_db.close()
            logger.debug("Database connection closed successfully during graceful shutdown")
        except Exception as e:
            logger.warning(f"Error closing database during shutdown: {e}")
    
    tasks.append(close_database())
    
    # Close Redis connections if enabled
    async def close_redis():
        try:
            # AuthService uses redis_client directly, not session_manager
            if hasattr(auth_service, 'redis_client') and auth_service.redis_client:
                if hasattr(auth_service.redis_client, 'close'):
                    await auth_service.redis_client.close()
                logger.info("Redis connections closed successfully")
        except Exception as e:
            logger.warning(f"Error closing Redis connections: {e}")
    
    tasks.append(close_redis())
    
    # Execute all cleanup tasks concurrently with timeout
    if tasks:
        try:
            # Use shorter cleanup timeout in development for faster shutdown
            default_cleanup_timeout = "2" if env == "development" else "5"
            cleanup_timeout = float(get_env().get("CLEANUP_TIMEOUT_SECONDS", default_cleanup_timeout))
            logger.info(f"Running cleanup tasks with {cleanup_timeout}s timeout...")
            
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=cleanup_timeout
            )
            
            # Check for any exceptions in cleanup tasks
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning(f"Cleanup task {i} failed: {result}")
                    
            logger.info("All cleanup tasks completed successfully")
            
        except asyncio.TimeoutError:
            logger.warning(f"Cleanup timeout ({cleanup_timeout}s) exceeded, some connections may not have closed gracefully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    else:
        logger.info("No cleanup tasks to execute")
    
    logger.info("Auth Service shutdown completed")

# Create FastAPI app
app = FastAPI(
    title="Netra Auth Service",
    description="Standalone Authentication Microservice",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS using CORSConfigurationBuilder
# @marked: CORS configuration from unified shared config builder
env = AuthConfig.get_environment()
cors_builder = CORSConfigurationBuilder()
cors_config = cors_builder.fastapi.get_middleware_config()

# Add service-specific headers to the configuration
cors_config["allow_headers"].extend([
    "X-Service-ID", 
    "X-Cross-Service-Auth"
])
cors_config["expose_headers"].extend([
    "X-Service-Name", 
    "X-Service-Version",
    "Vary"  # CORS-005: Expose Vary header for security
])

logger.info(f"CORS configured for {env} environment with {len(cors_config['allow_origins'])} origins")
app.add_middleware(CORSMiddleware, **cors_config)

# Security middleware for production
if AuthConfig.get_environment() in ["staging", "production"]:
    allowed_hosts = [
        "auth.staging.netrasystems.ai",  # Explicit staging auth domain
        "api.staging.netrasystems.ai",   # Explicit staging API domain
        "app.staging.netrasystems.ai",   # Explicit staging app domain
        "auth.netrasystems.ai",          # Production auth domain
        "api.netrasystems.ai",           # Production API domain
        "app.netrasystems.ai",           # Production app domain
        "*.netrasystems.ai",              # Wildcard for other subdomains
        "*.run.app",                     # Cloud Run URLs
        "localhost",                     # Local development
        "127.0.0.1"                      # Local IP
    ]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

# Custom middleware for request size limiting and service identification
from auth_service.auth_core.security.middleware import (
    validate_request_size,
    add_service_headers,
    add_security_headers
)

@app.middleware("http")
async def security_and_service_middleware(request: Request, call_next):
    """Enhanced security middleware with CORS security features"""
    
    # Request size validation (canonical implementation)
    size_error = await validate_request_size(request)
    if size_error:
        return size_error
    
    # CORS-012: Validate Content-Type for security
    content_type = request.headers.get("content-type")
    origin = request.headers.get("origin")
    request_id = request.headers.get("x-request-id", "unknown")
    
    if content_type and not cors_builder.security.validate_content_type(content_type):
        # SEC-002: Log suspicious Content-Type
        cors_builder.security.log_security_event(
            event_type="suspicious_content_type",
            origin=origin or "unknown",
            path=request.url.path,
            request_id=request_id,
            additional_info={"content_type": content_type, "service": "auth-service"}
        )
    
    # Process request
    response = await call_next(request)
    
    # Add service and security headers (canonical implementation)
    add_service_headers(response, "auth-service", "1.0.0")
    add_security_headers(response)
    
    # CORS-005: Add Vary: Origin header if origin is present
    if origin:
        response.headers["Vary"] = "Origin"
    
    return response

# Include routers without API versioning
app.include_router(auth_router, prefix="")
app.include_router(oauth_router, prefix="")

# Include new JWT SSOT remediation APIs
app.include_router(jwt_validation_router, prefix="")
app.include_router(websocket_auth_router, prefix="")
app.include_router(service_auth_router, prefix="")

# Root endpoint
@app.get("/")
@app.head("/")
async def root():
    """Root endpoint"""
    return {
        "service": "auth-service",
        "version": "1.0.0",
        "status": "running"
    }

# Health check at root level
@app.get("/health")
@app.head("/health")
async def health() -> Dict[str, Any]:
    """Health check with database validation to prevent silent failures"""
    from auth_service.auth_core.database.connection import auth_db
    
    basic_health = health_interface.get_basic_health()
    
    # For staging and production, validate database connectivity
    env = AuthConfig.get_environment()
    if env in ["staging", "production"]:
        try:
            # Check database connectivity
            db_ready = await auth_db.is_ready() if hasattr(auth_db, 'is_ready') else False
            if not db_ready:
                # Return 503 Service Unavailable if database is down
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "unhealthy",
                        "service": "auth-service",
                        "version": "1.0.0",
                        "timestamp": datetime.now(UTC).isoformat(),
                        "reason": "Database connectivity failed",
                        "environment": env
                    }
                )
            
            # Add database status to health response
            basic_health["database_status"] = "connected"
            basic_health["environment"] = env
            return basic_health
            
        except Exception as e:
            logger.error(f"Health check database validation failed: {e}")
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "service": "auth-service",
                    "version": "1.0.0",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "reason": f"Database validation error: {str(e)}",
                    "environment": env
                }
            )
    else:
        # Development mode - basic health check only
        basic_health["environment"] = env
        return basic_health

# Readiness check endpoint
@app.get("/health/ready")
@app.head("/health/ready")
async def health_ready() -> Dict[str, Any]:
    """Readiness probe with strict database validation - fails fast if dependencies unavailable"""
    from auth_service.auth_core.database.connection import auth_db
    
    env = AuthConfig.get_environment()
    
    try:
        # ALWAYS validate database connectivity for readiness checks
        # No graceful degradation - service is NOT ready if database is down
        is_ready = await auth_db.is_ready() if hasattr(auth_db, 'is_ready') else False
        
        if is_ready:
            return {
                "status": "ready",
                "service": "auth-service",
                "version": "1.0.0",
                "timestamp": datetime.now(UTC).isoformat(),
                "environment": env,
                "database_status": "connected"
            }
        else:
            logger.error(f"Readiness check failed: Database not ready in {env} environment")
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready", 
                    "service": "auth-service", 
                    "reason": "Database connectivity failed",
                    "environment": env,
                    "timestamp": datetime.now(UTC).isoformat()
                }
            )
            
    except Exception as e:
        logger.error(f"Readiness check failed with exception: {e}")
        # NO graceful degradation - service is not ready if database check fails
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready", 
                "service": "auth-service", 
                "reason": f"Database validation error: {str(e)}",
                "environment": env,
                "timestamp": datetime.now(UTC).isoformat()
            }
        )

# Additional readiness endpoint for external health checks
@app.get("/readiness")
@app.head("/readiness")
async def readiness() -> Dict[str, Any]:
    """Alternative readiness endpoint with same validation logic"""
    return await health_ready()

# CORS health check endpoint
@app.get("/cors/test")
@app.head("/cors/test")
async def cors_test() -> Dict[str, Any]:
    """CORS configuration test endpoint for debugging and validation"""
    cors_info = cors_builder.health.get_config_info()
    
    return {
        "service": "auth-service",
        "version": "1.0.0",
        "cors_status": "configured",
        "timestamp": datetime.now(UTC).isoformat(),
        **cors_info
    }

# Auth service health endpoint for Golden Path validation
@app.get("/health/auth")
@app.head("/health/auth")
async def health_auth() -> Dict[str, Any]:
    """
    Auth service health endpoint for Golden Path validation.
    
    Validates JWT capabilities, session management, and OAuth status specifically
    for the Golden Path user flow (login -> chat message flow).
    """
    from auth_service.auth_core.database.connection import auth_db
    from auth_service.auth_core.oauth_manager import OAuthManager
    
    env = AuthConfig.get_environment()
    health_response = {
        "service": "auth-service",
        "version": "1.0.0",
        "environment": env,
        "timestamp": datetime.now(UTC).isoformat(),
        "status": "healthy",
        "capabilities": {
            "jwt_validation": False,
            "session_management": False,
            "oauth_configured": False,
            "database_connected": False
        },
        "golden_path_ready": False
    }
    
    try:
        # Check JWT capabilities (most critical for Golden Path)
        try:
            from auth_service.auth_core.services.auth_service import AuthService
            auth_svc = AuthService()
            
            # Verify JWT creation and validation capabilities
            if hasattr(auth_svc, 'create_access_token') and hasattr(auth_svc, 'verify_token'):
                health_response["capabilities"]["jwt_validation"] = True
            
        except Exception as jwt_error:
            logger.warning(f"JWT capability check failed: {jwt_error}")
        
        # Check session management (Redis-based or in-memory)
        try:
            if hasattr(auth_service, 'redis_client') and auth_service.redis_client:
                health_response["capabilities"]["session_management"] = True
            elif hasattr(auth_service, 'session_store'):
                health_response["capabilities"]["session_management"] = True
                
        except Exception as session_error:
            logger.warning(f"Session management check failed: {session_error}")
        
        # Check OAuth configuration for user login flow
        try:
            oauth_manager = OAuthManager()
            available_providers = oauth_manager.get_available_providers()
            if "google" in available_providers:
                google_provider = oauth_manager.get_provider("google")
                if google_provider and oauth_manager.is_provider_configured("google"):
                    health_response["capabilities"]["oauth_configured"] = True
                    
        except Exception as oauth_error:
            logger.warning(f"OAuth configuration check failed: {oauth_error}")
        
        # Check database connectivity for user persistence
        try:
            db_ready = await auth_db.is_ready() if hasattr(auth_db, 'is_ready') else False
            if db_ready:
                health_response["capabilities"]["database_connected"] = True
                
        except Exception as db_error:
            logger.warning(f"Database connectivity check failed: {db_error}")
        
        # Determine overall Golden Path readiness
        # Core requirements: JWT validation and OAuth configured
        core_ready = (
            health_response["capabilities"]["jwt_validation"] and
            health_response["capabilities"]["oauth_configured"]
        )
        
        # Optional but recommended: session management and database
        full_ready = (
            core_ready and
            health_response["capabilities"]["session_management"] and
            health_response["capabilities"]["database_connected"]
        )
        
        if full_ready:
            health_response["golden_path_ready"] = True
            health_response["status"] = "healthy"
            return health_response
        elif core_ready:
            health_response["golden_path_ready"] = True
            health_response["status"] = "degraded"
            health_response["warnings"] = [
                "Session management or database connectivity limited - user sessions may not persist"
            ]
            return health_response
        else:
            # Critical capabilities missing
            missing_capabilities = []
            if not health_response["capabilities"]["jwt_validation"]:
                missing_capabilities.append("JWT validation")
            if not health_response["capabilities"]["oauth_configured"]:
                missing_capabilities.append("OAuth configuration")
            
            health_response["status"] = "unhealthy"
            health_response["golden_path_ready"] = False
            health_response["error"] = f"Missing critical capabilities: {', '.join(missing_capabilities)}"
            
            # Return 503 in staging/production for missing critical capabilities
            if env in ["staging", "production"]:
                return JSONResponse(
                    status_code=503,
                    content=health_response
                )
            
            return health_response
            
    except Exception as e:
        logger.error(f"Auth health check failed: {e}")
        health_response["status"] = "unhealthy"
        health_response["golden_path_ready"] = False
        health_response["error"] = f"Health check failed: {str(e)}"
        
        # Return 503 for any health check failure in staging/production
        if env in ["staging", "production"]:
            return JSONResponse(
                status_code=503,
                content=health_response
            )
        
        return health_response

# OAuth status endpoint for monitoring and validation
@app.get("/oauth/status")
@app.head("/oauth/status")
async def oauth_status() -> Dict[str, Any]:
    """OAuth provider status endpoint for health monitoring and validation"""
    from auth_service.auth_core.oauth_manager import OAuthManager
    
    env = AuthConfig.get_environment()
    status_response = {
        "service": "auth-service",
        "version": "1.0.0",
        "environment": env,
        "timestamp": datetime.now(UTC).isoformat(),
        "oauth_providers": {}
    }
    
    try:
        # Initialize OAuth manager to check provider status
        oauth_manager = OAuthManager()
        
        # Get available providers
        available_providers = oauth_manager.get_available_providers()
        status_response["available_providers"] = available_providers
        
        # Check Google provider specifically
        if "google" in available_providers:
            google_provider = oauth_manager.get_provider("google")
            if google_provider:
                # Perform self-check
                self_check_results = google_provider.self_check()
                status_response["oauth_providers"]["google"] = self_check_results
                
                # Add configuration status
                config_status = google_provider.get_configuration_status()
                status_response["oauth_providers"]["google"]["config"] = config_status
        else:
            status_response["oauth_providers"]["google"] = {
                "is_healthy": False,
                "error": "Google OAuth provider not available"
            }
        
        # Overall OAuth health
        all_healthy = all(
            provider_info.get("is_healthy", False) 
            for provider_info in status_response["oauth_providers"].values()
        )
        status_response["oauth_healthy"] = all_healthy
        
        # Return 503 if OAuth is unhealthy in staging/production
        if not all_healthy and env in ["staging", "production"]:
            return JSONResponse(
                status_code=503,
                content=status_response
            )
        
        return status_response
        
    except Exception as e:
        logger.error(f"Failed to get OAuth status: {e}")
        status_response["error"] = str(e)
        status_response["oauth_healthy"] = False
        
        # Return 503 in staging/production if OAuth status check fails
        if env in ["staging", "production"]:
            return JSONResponse(
                status_code=503,
                content=status_response
            )
        
        return status_response

if __name__ == "__main__":
    import uvicorn
    # @marked: Port binding for container runtime with performance optimizations
    # Default to 8081 to align with dev launcher expectations and E2E test configurations
    port = int(get_env().get("PORT", "8081"))
    
    # Performance-optimized uvicorn settings
    uvicorn_config = {
        "host": "0.0.0.0",
        "port": port,
        "workers": 1,  # Single worker for auth service consistency
        "loop": "uvloop" if os.name != 'nt' else "asyncio",  # Use uvloop on Unix systems
        "http": "httptools" if os.name != 'nt' else "h11",  # Use httptools on Unix systems  
        "access_log": False,  # Disable access log for performance
        "server_header": False,  # Disable server header for security
        "date_header": False  # Disable date header for slight performance gain
    }
    
    logger.info(f"Starting Auth Service on port {port} with performance optimizations")
    uvicorn.run(app, **uvicorn_config)