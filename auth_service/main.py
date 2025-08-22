"""
Auth Service Main Application
Standalone microservice for authentication
"""
import os
import sys
from pathlib import Path

# Add parent directory to Python path for auth_service imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, Dict

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

# Load environment variables from .env file
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
from auth_service.auth_core.routes.auth_routes import router as auth_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
    """Manage application lifecycle with optimized startup"""
    logger.info("Starting Auth Service...")
    
    # Log configuration
    from auth_service.auth_core.config import AuthConfig
    AuthConfig.log_configuration()
    # @marked: Port must be read from environment for container deployment
    logger.info(f"Port: {os.getenv('PORT', '8080')}")
    
    # Log Redis configuration status
    from auth_service.auth_core.routes.auth_routes import auth_service
    redis_enabled = auth_service.session_manager.redis_enabled
    redis_status = "enabled" if redis_enabled else "disabled (staging environment)"
    logger.info(f"Redis session management: {redis_status}")
    
    # Check if we're in fast test mode
    # @marked: Test mode flag for test infrastructure
    fast_test_mode = os.getenv("AUTH_FAST_TEST_MODE", "false").lower() == "true"
    env = AuthConfig.get_environment()
    
    if fast_test_mode or env == "test":
        logger.info("Running in fast test mode - skipping database initialization")
        yield
        return
    
    # Initialize single database connection
    from auth_service.auth_core.database.connection import auth_db
    
    initialization_errors = []
    
    # Initialize auth database (uses the same DATABASE_URL as main app)
    try:
        await auth_db.initialize()
        logger.info("Auth database initialized successfully")
    except Exception as e:
        error_msg = str(e) if str(e) else f"{type(e).__name__}: {repr(e)}"
        logger.warning(f"Auth database initialization failed: {error_msg}")
        initialization_errors.append(f"Database: {error_msg}")
    
    # In development, allow service to start even with DB issues
    if env == "development" and initialization_errors:
        logger.warning(f"Starting with {len(initialization_errors)} DB issues in development mode")
    elif initialization_errors and env in ["staging", "production"]:
        raise RuntimeError(f"Critical database failures: {initialization_errors}")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Auth Service...")
    
    # Close database connection safely
    try:
        await auth_db.close()
    except Exception as e:
        logger.warning(f"Error closing database: {e}")
    
    logger.info("Database connection closed")

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

# Configure CORS
# @marked: CORS configuration from environment for security
cors_origins_env = os.getenv("CORS_ORIGINS", "")
env = AuthConfig.get_environment()

# Handle wildcard CORS for development
if cors_origins_env == "*":
    # Allow all origins in development
    cors_origins = ["*"]
elif cors_origins_env:
    # Parse comma-separated origins
    cors_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
else:
    # Default CORS origins based on environment
    if env == "staging":
        cors_origins = [
            "https://app.staging.netrasystems.ai",
            "https://auth.staging.netrasystems.ai",
            "https://api.staging.netrasystems.ai",
            "http://localhost:3000",
            "http://localhost:8000",
            "http://localhost:8080"
        ]
    elif env == "production":
        cors_origins = [
            "https://netrasystems.ai",
            "https://app.netrasystems.ai",
            "https://api.netrasystems.ai",
            "https://auth.netrasystems.ai"
        ]
    else:
        # Development environment - support common dynamic ports plus service discovery
        cors_origins = [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:3002",
            "http://localhost:3003",
            "http://localhost:4000",
            "http://localhost:4001",
            "http://localhost:4200",
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:8000",
            "http://localhost:8001",
            "http://localhost:8002",
            "http://localhost:8003",
            "http://localhost:8080",
            "http://localhost:8081",
            "http://localhost:8082",
            "http://localhost:8083",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
            "http://127.0.0.1:3002",
            "http://127.0.0.1:3003",
            "http://127.0.0.1:4000",
            "http://127.0.0.1:4001",
            "http://127.0.0.1:4200",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5174",
            "http://127.0.0.1:8000",
            "http://127.0.0.1:8001",
            "http://127.0.0.1:8002",
            "http://127.0.0.1:8003",
            "http://127.0.0.1:8080",
            "http://127.0.0.1:8081",
            "http://127.0.0.1:8082",
            "http://127.0.0.1:8083"
        ]
        
        # Add service discovery origins if available
        try:
            from pathlib import Path
            # Look for service discovery directory
            project_root = Path(__file__).parent.parent
            service_discovery_dir = project_root / ".service_discovery"
            
            if service_discovery_dir.exists():
                # Add discovered service origins
                import json
                
                # Read backend info
                backend_file = service_discovery_dir / "backend.json"
                if backend_file.exists():
                    with open(backend_file, 'r') as f:
                        backend_info = json.load(f)
                        if backend_info.get('api_url'):
                            cors_origins.append(backend_info['api_url'])
                
                # Read frontend info
                frontend_file = service_discovery_dir / "frontend.json"
                if frontend_file.exists():
                    with open(frontend_file, 'r') as f:
                        frontend_info = json.load(f)
                        if frontend_info.get('url'):
                            cors_origins.append(frontend_info['url'])
                            
                logger.info(f"Added service discovery origins, total: {len(cors_origins)} origins")
        except Exception as e:
            logger.warning(f"Failed to load service discovery origins: {e}")

# Always use DynamicCORSMiddleware to properly handle OPTIONS requests
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class DynamicCORSMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, allowed_origins=None):
        super().__init__(app)
        self.allowed_origins = allowed_origins or []
        self._pattern_cache = {}  # Cache compiled patterns for performance
        
    def is_allowed_origin(self, origin: str) -> bool:
        """Check if origin is allowed - supports dynamic ports for localhost and service discovery."""
        if not origin:
            return False
        
        # Check if it matches explicit allowed origins
        if self.allowed_origins and origin in self.allowed_origins:
            return True
            
        # If wildcard mode
        if "*" in self.allowed_origins:
            return True
            
        # In development, accept any localhost/127.0.0.1 origin with any port
        import re
        
        # Use cached pattern or compile new one
        if 'localhost_pattern' not in self._pattern_cache:
            self._pattern_cache['localhost_pattern'] = re.compile(
                r'^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\])(:\d+)?$', 
                re.IGNORECASE
            )
        
        if self._pattern_cache['localhost_pattern'].match(origin):
            logger.debug(f"Auth service allowing localhost origin: {origin}")
            return True
        
        # Check service discovery origins if in development
        if env == "development":
            try:
                from pathlib import Path
                import json
                
                project_root = Path(__file__).parent.parent
                service_discovery_dir = project_root / ".service_discovery"
                
                if service_discovery_dir.exists():
                    # Check all service discovery files
                    for service_file in service_discovery_dir.glob("*.json"):
                        try:
                            with open(service_file, 'r') as f:
                                service_info = json.load(f)
                                
                            # Check various URL fields
                            for url_field in ['url', 'api_url', 'ws_url']:
                                if service_info.get(url_field):
                                    service_origin = service_info[url_field]
                                    # Convert WebSocket URLs to HTTP for CORS comparison
                                    if service_origin.startswith('ws://'):
                                        service_origin = service_origin.replace('ws://', 'http://')
                                    elif service_origin.startswith('wss://'):
                                        service_origin = service_origin.replace('wss://', 'https://')
                                    
                                    # Extract just the origin part if it has a path
                                    if '/' in service_origin.split('://')[1]:
                                        parts = service_origin.split('/')
                                        service_origin = f"{parts[0]}//{parts[2]}"
                                    
                                    if origin == service_origin:
                                        logger.debug(f"Auth service allowing service discovery origin: {origin}")
                                        return True
                        except (json.JSONDecodeError, IOError) as e:
                            logger.debug(f"Could not read service file {service_file}: {e}")
            except Exception as e:
                logger.debug(f"Service discovery check failed: {e}")
        
        logger.debug(f"Auth service denying origin: {origin}")
        return False
    
    async def dispatch(self, request, call_next):
        origin = request.headers.get("origin")
        
        # Handle preflight
        if request.method == "OPTIONS":
            response = Response(status_code=200)
            if origin and self.is_allowed_origin(origin):
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD"
                response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Request-ID, X-Trace-ID, Accept, Origin, Referer, X-Requested-With, X-Service-ID, X-Cross-Service-Auth"
                response.headers["Access-Control-Max-Age"] = "3600"
                response.headers["Vary"] = "Origin"
            return response
        
        # Process request
        response = await call_next(request)
        
        # Add CORS headers to response
        if origin and self.is_allowed_origin(origin):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD"
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Request-ID, X-Trace-ID, Accept, Origin, Referer, X-Requested-With, X-Service-ID, X-Cross-Service-Auth"
            response.headers["Access-Control-Expose-Headers"] = "X-Trace-ID, X-Request-ID, Content-Length, Content-Type, X-Service-Name, X-Service-Version"
            response.headers["Vary"] = "Origin"
        
        return response

app.add_middleware(DynamicCORSMiddleware, allowed_origins=cors_origins)

# Security middleware for production
if AuthConfig.get_environment() in ["staging", "production"]:
    allowed_hosts = [
        "*.netrasystems.ai",
        "*.run.app",
        "localhost"
    ]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

# Custom middleware for service identification
@app.middleware("http")
async def add_service_headers(request: Request, call_next):
    """Add service identification headers"""
    response = await call_next(request)
    response.headers["X-Service-Name"] = "auth-service"
    response.headers["X-Service-Version"] = "1.0.0"
    
    # Security headers
    # @marked: Security headers toggle for production environments
    if os.getenv("SECURE_HEADERS_ENABLED", "false").lower() == "true":
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
    
    return response

# Include routers
app.include_router(auth_router)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "auth-service",
        "version": "1.0.0",
        "status": "running"
    }

# Health check at root level
@app.get("/health")
async def health() -> Dict[str, Any]:
    """Basic health check with unified health system"""
    return health_interface.get_basic_health()

# Readiness check endpoint
@app.get("/health/ready")
async def health_ready() -> Dict[str, Any]:
    """Readiness probe to check if the service is ready to serve requests"""
    # Check if database connections are available
    from auth_service.auth_core.database.connection import auth_db
    
    try:
        # Try to check database connectivity
        is_ready = await auth_db.is_ready() if hasattr(auth_db, 'is_ready') else True
        
        if is_ready:
            return {
                "status": "ready",
                "service": "auth-service",
                "version": "1.0.0",
                "timestamp": datetime.now(UTC).isoformat()
            }
        else:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "service": "auth-service", "reason": "Database not ready"}
            )
    except Exception as e:
        logger.warning(f"Readiness check failed: {e}")
        # In development, we might still be ready even if DB check fails
        env = AuthConfig.get_environment()
        if env == "development":
            return {
                "status": "ready",
                "service": "auth-service", 
                "version": "1.0.0",
                "timestamp": datetime.now(UTC).isoformat(),
                "warning": "Database check failed but continuing in development mode"
            }
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "service": "auth-service", "reason": str(e)}
        )

if __name__ == "__main__":
    import uvicorn
    # @marked: Port binding for container runtime
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)