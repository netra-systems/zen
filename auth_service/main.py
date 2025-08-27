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

import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, Dict

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from auth_service.auth_core.isolated_environment import get_env

# Load environment variables from .env file ONLY in development
# In staging/production, all config comes from Cloud Run env vars and Google Secret Manager
environment = get_env().get('ENVIRONMENT', '').lower()
if environment in ['staging', 'production', 'prod']:
    print(f"Running in {environment} - skipping .env file loading (using GSM)")
else:
    # Try parent directory first (where main .env is located)
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded environment from: {env_path}")
    else:
        # Fallback to current directory
        load_dotenv()
        print("Loaded environment from current directory or system")

from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.routes.auth_routes import router as auth_router, oauth_router
from shared.logging import get_logger, configure_service_logging
from shared.cors_config import get_fastapi_cors_config

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
        elif google_client_id.startswith("REPLACE_") or len(google_client_id) < 50:
            oauth_validation_errors.append(f"Google OAuth client ID appears invalid: {google_client_id[:20]}...")
            logger.error(f"❌ CRITICAL: Google OAuth client ID looks like a placeholder: {google_client_id[:20]}...")
        else:
            logger.info(f"✅ Google OAuth client ID configured: {google_client_id[:20]}...")
        
        # Check Google Client Secret
        google_client_secret = AuthConfig.get_google_client_secret()
        if not google_client_secret:
            # TOMBSTONE: GOOGLE_CLIENT_SECRET variable superseded by environment-specific GOOGLE_OAUTH_CLIENT_SECRET_* variables
            oauth_validation_errors.append("Google OAuth client secret is not configured")
            logger.error("❌ CRITICAL: Google OAuth client secret is missing!")
        elif google_client_secret.startswith("REPLACE_") or len(google_client_secret) < 20:
            oauth_validation_errors.append(f"Google OAuth client secret appears invalid")
            logger.error(f"❌ CRITICAL: Google OAuth client secret looks like a placeholder")
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
    else:
        logger.info(f"Skipping OAuth validation in {env} environment")
    
    # Log Redis configuration status
    from auth_service.auth_core.routes.auth_routes import auth_service
    redis_enabled = auth_service.session_manager.redis_enabled
    redis_status = "enabled" if redis_enabled else "disabled (staging environment)"
    logger.info(f"Redis session management: {redis_status}")
    
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
    
    # Initialize auth database (uses the same DATABASE_URL as main app)
    try:
        await auth_db.initialize()
        logger.info("Auth database initialized successfully")
        
        # Verify database connectivity immediately
        db_ready = await auth_db.is_ready()
        if not db_ready:
            raise RuntimeError("Database initialization succeeded but connectivity test failed")
        
        logger.info("Auth database connectivity verified successfully")
        
    except Exception as e:
        error_msg = str(e) if str(e) else f"{type(e).__name__}: {repr(e)}"
        logger.error(f"Auth database initialization failed: {error_msg}")
        
        # FAIL FAST: Do not start service if database is unavailable
        # This prevents misleading "healthy" status when critical dependencies are down
        if env in ["staging", "production"]:
            raise RuntimeError(f"Database initialization failed in {env}: {error_msg}")
        elif env == "development":
            # Development can continue without database for basic testing
            logger.warning(f"Development mode: continuing without database - {error_msg}")
        else:
            # Unknown environment - be conservative and fail
            raise RuntimeError(f"Database initialization failed in {env}: {error_msg}")
    
    logger.info("Auth Service startup completed")
    
    yield
    
    # Graceful shutdown
    logger.info("Shutting down Auth Service...")
    
    # Wait for shutdown signal with timeout to prevent hanging
    try:
        # Set a timeout for graceful shutdown (Cloud Run gives 10 seconds by default)
        shutdown_timeout = float(get_env().get("SHUTDOWN_TIMEOUT_SECONDS", "8"))
        logger.info(f"Waiting up to {shutdown_timeout} seconds for graceful shutdown...")
        
        # Use asyncio.wait_for with proper timeout handling
        await asyncio.wait_for(shutdown_event.wait(), timeout=shutdown_timeout)
        logger.info("Shutdown signal received, proceeding with cleanup")
    except asyncio.TimeoutError:
        logger.warning(f"Shutdown timeout ({shutdown_timeout}s) exceeded, forcing cleanup")
    except Exception as e:
        logger.error(f"Error during shutdown wait: {e}, proceeding with cleanup")
    
    # Close connections gracefully
    tasks = []
    
    # Close database connection safely
    async def close_database():
        try:
            await auth_db.close()
            logger.info("Database connection closed successfully")
        except Exception as e:
            logger.warning(f"Error closing database: {e}")
    
    tasks.append(close_database())
    
    # Close Redis connections if enabled
    async def close_redis():
        try:
            if hasattr(auth_service.session_manager, 'close_redis'):
                await auth_service.session_manager.close_redis()
                logger.info("Redis connections closed successfully")
        except Exception as e:
            logger.warning(f"Error closing Redis connections: {e}")
    
    tasks.append(close_redis())
    
    # Execute all cleanup tasks concurrently with timeout
    if tasks:
        try:
            cleanup_timeout = float(get_env().get("CLEANUP_TIMEOUT_SECONDS", "5"))
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

# Configure CORS using unified configuration
# @marked: CORS configuration from unified shared config
env = AuthConfig.get_environment()
cors_config = get_fastapi_cors_config(env)

# Add service-specific headers to the configuration
cors_config["allow_headers"].extend([
    "X-Service-ID", 
    "X-Cross-Service-Auth"
])
cors_config["expose_headers"].extend([
    "X-Service-Name", 
    "X-Service-Version"
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
    """Canonical security middleware using SSOT implementation"""
    # Request size validation (canonical implementation)
    size_error = await validate_request_size(request)
    if size_error:
        return size_error
    
    # Process request
    response = await call_next(request)
    
    # Add service and security headers (canonical implementation)
    add_service_headers(response, "auth-service", "1.0.0")
    add_security_headers(response)
    
    return response

# Include routers without API versioning
app.include_router(auth_router, prefix="")
app.include_router(oauth_router, prefix="")

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