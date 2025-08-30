"""
Analytics Service Main Application
Standalone microservice for frontend event capture, processing, and analytics
"""
import os
import sys
import signal
import asyncio
from pathlib import Path

# Add parent directory to Python path for analytics_service imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

# CRITICAL: Load environment variables BEFORE importing any analytics service modules
# This ensures all configuration variables are available when analytics service initializes
environment = os.environ.get('ENVIRONMENT', '').lower()
if environment in ['staging', 'production', 'prod']:
    print(f"Running in {environment} - skipping .env file loading (using GSM)")
else:
    # Try parent directory first (where main .env is located)
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)  # override=True ensures env vars are set
        print(f"Loaded environment from: {env_path}")
    else:
        # Fallback to current directory
        load_dotenv(override=True)
        print("Loaded environment from current directory or system")

# NOW import analytics service modules after environment is fully loaded
from analytics_service.analytics_core.isolated_environment import get_env
from analytics_service.analytics_core.config import AnalyticsConfig

# Import shared modules
from shared.logging import get_logger, configure_service_logging
from shared.cors_config_builder import CORSConfigurationBuilder

# Configure unified logging for analytics service
configure_service_logging({
    'service_name': 'analytics-service',
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

# Health Interface for Analytics Service
class AnalyticsServiceHealthInterface:
    """Health interface for analytics service."""
    
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
health_interface = AnalyticsServiceHealthInterface("analytics-service", "1.0.0")

# Request validation utility
async def validate_request_size(request: Request, max_size_mb: int = 10) -> Optional[JSONResponse]:
    """
    Request size validation for analytics service
    
    Args:
        request: FastAPI request object
        max_size_mb: Maximum allowed size in MB
        
    Returns:
        JSONResponse with error if request is invalid, None if valid
    """
    content_length = request.headers.get("content-length")
    content_type = request.headers.get("content-type", "")
    
    if content_length:
        try:
            size = int(content_length)
            max_size_bytes = max_size_mb * 1024 * 1024  # Convert MB to bytes
            if size > max_size_bytes:
                logger.warning(f"Request payload too large: {size} bytes (max: {max_size_bytes})")
                return JSONResponse(
                    status_code=413,  # Payload Too Large
                    content={"detail": f"Request payload too large. Maximum size: {max_size_mb}MB"}
                )
        except ValueError:
            # Invalid Content-Length header
            logger.warning(f"Invalid Content-Length header: {content_length}")
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid Content-Length header"}
            )
    
    return None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle with optimized startup and graceful shutdown"""
    logger.info("Starting Analytics Service...")
    
    # Log configuration
    AnalyticsConfig.log_configuration()
    logger.info(f"Port: {get_env().get('PORT', '8090')}")
    
    # Validate configuration
    validation = AnalyticsConfig.validate_configuration()
    if not validation["valid"]:
        error_msg = f"Configuration validation failed: {', '.join(validation['issues'])}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    # Log warnings if any
    for warning in validation.get("warnings", []):
        logger.warning(f"Configuration warning: {warning}")
    
    # Initialize connections based on environment
    env = AnalyticsConfig.get_environment()
    
    # Check if we're in fast test mode
    fast_test_mode = get_env().get("ANALYTICS_FAST_TEST_MODE", "false").lower() == "true"
    
    if fast_test_mode or env == "test":
        logger.info("Running in fast test mode - skipping service initialization")
        yield
        return
    
    # Initialize ClickHouse connection
    clickhouse_initialized = False
    redis_initialized = False
    
    try:
        # TODO: Initialize ClickHouse client when implemented
        clickhouse_url = AnalyticsConfig.get_clickhouse_url()
        if clickhouse_url:
            logger.info("ClickHouse configuration validated")
            clickhouse_initialized = True
        else:
            logger.warning("ClickHouse not configured - analytics data storage disabled")
            
    except Exception as e:
        error_msg = f"ClickHouse initialization failed: {str(e)}"
        logger.error(error_msg)
        if env in ["staging", "production"]:
            raise RuntimeError(error_msg)
        logger.warning("Continuing in development mode without ClickHouse")
    
    # Initialize Redis connection
    try:
        # TODO: Initialize Redis client when implemented
        redis_url = AnalyticsConfig.get_redis_url()
        if redis_url:
            logger.info("Redis configuration validated")
            redis_initialized = True
        else:
            logger.warning("Redis not configured - real-time caching disabled")
            
    except Exception as e:
        error_msg = f"Redis initialization failed: {str(e)}"
        logger.error(error_msg)
        if env in ["staging", "production"]:
            raise RuntimeError(error_msg)
        logger.warning("Continuing in development mode without Redis")
    
    # Log initialization status
    services_status = []
    if clickhouse_initialized:
        services_status.append("ClickHouse")
    if redis_initialized:
        services_status.append("Redis")
    
    if services_status:
        logger.info(f"Analytics Service startup completed with: {', '.join(services_status)}")
    else:
        logger.info("Analytics Service startup completed in basic mode")
    
    yield
    
    # Graceful shutdown
    logger.info("Shutting down Analytics Service...")
    
    # Skip waiting for shutdown event in development - proceed directly to cleanup
    env = AnalyticsConfig.get_environment()
    if env == "development":
        logger.info("Development environment - proceeding directly to cleanup")
    else:
        # Wait for shutdown signal with timeout to prevent hanging
        try:
            shutdown_timeout = float(get_env().get("SHUTDOWN_TIMEOUT_SECONDS", "3"))
            logger.info(f"Waiting up to {shutdown_timeout} seconds for graceful shutdown...")
            
            await asyncio.wait_for(shutdown_event.wait(), timeout=shutdown_timeout)
            logger.info("Shutdown signal received, proceeding with cleanup")
        except asyncio.TimeoutError:
            logger.info(f"Shutdown timeout ({shutdown_timeout}s) reached, proceeding with cleanup")
        except Exception as e:
            logger.warning(f"Error during shutdown wait: {e}, proceeding with cleanup")
    
    # Close connections gracefully
    tasks = []
    
    # TODO: Add ClickHouse connection cleanup when implemented
    async def close_clickhouse():
        try:
            logger.debug("ClickHouse connections would be closed here")
        except Exception as e:
            logger.warning(f"Error closing ClickHouse connections: {e}")
    
    tasks.append(close_clickhouse())
    
    # TODO: Add Redis connection cleanup when implemented
    async def close_redis():
        try:
            logger.debug("Redis connections would be closed here")
        except Exception as e:
            logger.warning(f"Error closing Redis connections: {e}")
    
    tasks.append(close_redis())
    
    # Execute all cleanup tasks concurrently with timeout
    if tasks:
        try:
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
    
    logger.info("Analytics Service shutdown completed")

# Create FastAPI app
app = FastAPI(
    title="Netra Analytics Service",
    description="Frontend Event Capture, Processing, and Analytics Microservice",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS using CORSConfigurationBuilder
env = AnalyticsConfig.get_environment()
cors_builder = CORSConfigurationBuilder()
cors_config = cors_builder.fastapi.get_middleware_config()

# Add analytics-specific CORS origins
analytics_origins = AnalyticsConfig.get_cors_origins()
cors_config["allow_origins"].extend(analytics_origins)

# Add service-specific headers to the configuration
cors_config["allow_headers"].extend([
    "X-Service-ID", 
    "X-Cross-Service-Analytics",
    "X-Event-Type",
    "X-Session-ID"
])
cors_config["expose_headers"].extend([
    "X-Service-Name", 
    "X-Service-Version",
    "X-Events-Processed",
    "Vary"  # CORS-005: Expose Vary header for security
])

logger.info(f"CORS configured for {env} environment with {len(cors_config['allow_origins'])} origins")
app.add_middleware(CORSMiddleware, **cors_config)

# Security middleware for production
if AnalyticsConfig.get_environment() in ["staging", "production"]:
    allowed_hosts = [
        "analytics.staging.netrasystems.ai",  # Explicit staging analytics domain
        "api.staging.netrasystems.ai",        # Explicit staging API domain
        "app.staging.netrasystems.ai",        # Explicit staging app domain
        "analytics.netrasystems.ai",          # Production analytics domain
        "api.netrasystems.ai",               # Production API domain
        "app.netrasystems.ai",               # Production app domain
        "*.netrasystems.ai",                  # Wildcard for other subdomains
        "*.run.app",                         # Cloud Run URLs
        "localhost",                         # Local development
        "127.0.0.1"                          # Local IP
    ]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

# Custom middleware for request size limiting and service identification
@app.middleware("http")
async def security_and_service_middleware(request: Request, call_next):
    """Enhanced security middleware for analytics service"""
    
    # Request size validation
    size_error = await validate_request_size(request, max_size_mb=10)  # 10MB for analytics events
    if size_error:
        return size_error
    
    # CORS security validation
    content_type = request.headers.get("content-type")
    origin = request.headers.get("origin")
    request_id = request.headers.get("x-request-id", "unknown")
    
    if content_type and not cors_builder.security.validate_content_type(content_type):
        cors_builder.security.log_security_event(
            event_type="suspicious_content_type",
            origin=origin or "unknown",
            path=request.url.path,
            request_id=request_id,
            additional_info={"content_type": content_type, "service": "analytics-service"}
        )
    
    # Process request
    response = await call_next(request)
    
    # Add service identification headers
    response.headers["X-Service-Name"] = "analytics-service"
    response.headers["X-Service-Version"] = "1.0.0"
    
    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    # CORS-005: Add Vary: Origin header if origin is present
    if origin:
        response.headers["Vary"] = "Origin"
    
    return response

# TODO: Include API routers when implemented
# app.include_router(events_router, prefix="/api/analytics")
# app.include_router(reports_router, prefix="/api/analytics")

# Root endpoint
@app.get("/")
@app.head("/")
async def root():
    """Root endpoint"""
    return {
        "service": "analytics-service",
        "version": "1.0.0",
        "status": "running",
        "description": "Frontend Event Capture, Processing, and Analytics Microservice"
    }

# Health check at root level
@app.get("/health")
@app.head("/health")
async def health() -> Dict[str, Any]:
    """Health check with service validation"""
    basic_health = health_interface.get_basic_health()
    
    env = AnalyticsConfig.get_environment()
    basic_health["environment"] = env
    
    # For staging and production, validate critical services
    if env in ["staging", "production"]:
        services_status = {}
        
        # TODO: Add actual service connectivity checks when implemented
        try:
            clickhouse_url = AnalyticsConfig.get_clickhouse_url()
            services_status["clickhouse"] = "configured" if clickhouse_url else "not_configured"
        except Exception as e:
            services_status["clickhouse"] = f"error: {str(e)}"
        
        try:
            redis_url = AnalyticsConfig.get_redis_url()
            services_status["redis"] = "configured" if redis_url else "not_configured"
        except Exception as e:
            services_status["redis"] = f"error: {str(e)}"
        
        basic_health["services"] = services_status
        
        # Return 503 if critical services are not available
        if any("error" in status for status in services_status.values()):
            return JSONResponse(
                status_code=503,
                content={
                    **basic_health,
                    "status": "unhealthy",
                    "reason": "Critical service configuration errors"
                }
            )
    
    return basic_health

# Readiness check endpoint
@app.get("/health/ready")
@app.head("/health/ready")
async def health_ready() -> Dict[str, Any]:
    """Readiness probe with strict service validation"""
    env = AnalyticsConfig.get_environment()
    
    readiness_status = {
        "status": "ready",
        "service": "analytics-service",
        "version": "1.0.0",
        "timestamp": datetime.now(UTC).isoformat(),
        "environment": env
    }
    
    try:
        # Validate configuration
        validation = AnalyticsConfig.validate_configuration()
        if not validation["valid"]:
            return JSONResponse(
                status_code=503,
                content={
                    **readiness_status,
                    "status": "not_ready",
                    "reason": f"Configuration validation failed: {', '.join(validation['issues'])}",
                    "configuration_issues": validation["issues"]
                }
            )
        
        # TODO: Add actual service connectivity checks when implemented
        readiness_status["services_validated"] = True
        return readiness_status
            
    except Exception as e:
        logger.error(f"Readiness check failed with exception: {e}")
        return JSONResponse(
            status_code=503,
            content={
                **readiness_status,
                "status": "not_ready",
                "reason": f"Readiness validation error: {str(e)}"
            }
        )

# Alternative readiness endpoint
@app.get("/readiness")
@app.head("/readiness")
async def readiness() -> Dict[str, Any]:
    """Alternative readiness endpoint with same validation logic"""
    return await health_ready()

# CORS test endpoint
@app.get("/cors/test")
@app.head("/cors/test")
async def cors_test() -> Dict[str, Any]:
    """CORS configuration test endpoint for debugging and validation"""
    cors_info = cors_builder.health.get_config_info()
    
    return {
        "service": "analytics-service",
        "version": "1.0.0",
        "cors_status": "configured",
        "timestamp": datetime.now(UTC).isoformat(),
        "analytics_origins": AnalyticsConfig.get_cors_origins(),
        **cors_info
    }

# Configuration status endpoint
@app.get("/config/status")
@app.head("/config/status")
async def config_status() -> Dict[str, Any]:
    """Configuration status endpoint for monitoring and validation"""
    env = AnalyticsConfig.get_environment()
    
    status_response = {
        "service": "analytics-service",
        "version": "1.0.0",
        "environment": env,
        "timestamp": datetime.now(UTC).isoformat()
    }
    
    try:
        # Get configuration validation
        validation = AnalyticsConfig.validate_configuration()
        status_response["configuration"] = validation
        
        # Add service-specific status
        config_status = {
            "port": AnalyticsConfig.get_port(),
            "debug_mode": AnalyticsConfig.is_debug_mode(),
            "privacy_mode": AnalyticsConfig.is_privacy_mode_enabled(),
            "event_validation_level": AnalyticsConfig.get_event_validation_level(),
            "data_retention_days": AnalyticsConfig.get_data_retention_days(),
            "event_batch_size": AnalyticsConfig.get_event_batch_size(),
            "max_events_per_user_per_minute": AnalyticsConfig.get_max_events_per_user_per_minute()
        }
        
        status_response["config"] = config_status
        
        # Return 503 if configuration is invalid in staging/production
        if not validation["valid"] and env in ["staging", "production"]:
            return JSONResponse(
                status_code=503,
                content=status_response
            )
        
        return status_response
        
    except Exception as e:
        logger.error(f"Failed to get configuration status: {e}")
        status_response["error"] = str(e)
        status_response["configuration"] = {"valid": False, "issues": [str(e)]}
        
        # Return 503 in staging/production if config status check fails
        if env in ["staging", "production"]:
            return JSONResponse(
                status_code=503,
                content=status_response
            )
        
        return status_response

if __name__ == "__main__":
    import uvicorn
    # Port binding for container runtime with performance optimizations
    # Default to 8090 as specified in the analytics service requirements
    port = int(get_env().get("PORT", "8090"))
    
    # Performance-optimized uvicorn settings
    uvicorn_config = {
        "host": "0.0.0.0",
        "port": port,
        "workers": 1,  # Single worker for analytics service consistency
        "loop": "uvloop" if os.name != 'nt' else "asyncio",  # Use uvloop on Unix systems
        "http": "httptools" if os.name != 'nt' else "h11",  # Use httptools on Unix systems  
        "access_log": False,  # Disable access log for performance
        "server_header": False,  # Disable server header for security
        "date_header": False  # Disable date header for slight performance gain
    }
    
    logger.info(f"Starting Analytics Service on port {port} with performance optimizations")
    uvicorn.run(app, **uvicorn_config)