"""
Auth Service Main Application
Standalone microservice for authentication
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import logging
from typing import Dict, Any
from datetime import datetime, UTC

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
    logger.info(f"Port: {os.getenv('PORT', '8080')}")
    
    # Check if we're in fast test mode
    fast_test_mode = os.getenv("AUTH_FAST_TEST_MODE", "false").lower() == "true"
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if fast_test_mode or env == "test":
        logger.info("Running in fast test mode - skipping database initialization")
        yield
        return
    
    # Initialize database connections on startup
    from auth_service.auth_core.database.connection import auth_db
    from auth_service.auth_core.database.main_db_sync import main_db_sync
    
    initialization_errors = []
    
    # Try to initialize auth database
    try:
        await auth_db.initialize()
        logger.info("Auth database initialized successfully")
    except Exception as e:
        logger.warning(f"Auth database initialization failed: {e}")
        initialization_errors.append(f"Auth DB: {e}")
    
    # Try to initialize main database sync (non-critical for basic auth)
    try:
        await main_db_sync.initialize()
        logger.info("Main database sync initialized successfully")
    except Exception as e:
        logger.warning(f"Main database sync failed (non-critical): {e}")
        initialization_errors.append(f"Main DB Sync: {e}")
    
    # In development, allow service to start even with some DB issues
    if env == "development" and initialization_errors:
        logger.warning(f"Starting with {len(initialization_errors)} DB issues in development mode")
    elif initialization_errors and env in ["staging", "production"]:
        raise RuntimeError(f"Critical database failures: {initialization_errors}")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Auth Service...")
    
    # Close database connections safely
    try:
        await auth_db.close()
    except Exception as e:
        logger.warning(f"Error closing auth DB: {e}")
    
    try:
        await main_db_sync.close()
    except Exception as e:
        logger.warning(f"Error closing main DB sync: {e}")
    
    logger.info("Database connections closed")

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
cors_origins_env = os.getenv("CORS_ORIGINS", "")
env = os.getenv("ENVIRONMENT", "development")

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
            "https://staging.netrasystems.ai",
            "https://app.staging.netrasystems.ai",
            "https://api.staging.netrasystems.ai",
            "https://auth.staging.netrasystems.ai",
            "http://localhost:3000"
        ]
    elif env == "production":
        cors_origins = [
            "https://netrasystems.ai",
            "https://app.netrasystems.ai",
            "https://api.netrasystems.ai",
            "https://auth.netrasystems.ai"
        ]
    else:
        cors_origins = [
            "http://localhost:3000",
            "http://localhost:8000",
            "http://localhost:8080",
            "http://localhost:8081"
        ]

# When using wildcard with credentials, we need custom handling
if cors_origins == ["*"]:
    # In development with wildcard, we can't use credentials with "*"
    # So we'll handle CORS dynamically
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import Response
    
    class DynamicCORSMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            origin = request.headers.get("origin")
            
            # Handle preflight
            if request.method == "OPTIONS":
                response = Response(status_code=200)
                if origin:
                    response.headers["Access-Control-Allow-Origin"] = origin
                    response.headers["Access-Control-Allow-Credentials"] = "true"
                    response.headers["Access-Control-Allow-Methods"] = "*"
                    response.headers["Access-Control-Allow-Headers"] = "*"
                return response
            
            # Process request
            response = await call_next(request)
            
            # Add CORS headers to response
            if origin:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "*"
                response.headers["Access-Control-Allow-Headers"] = "*"
                response.headers["Access-Control-Expose-Headers"] = "*"
            
            return response
    
    app.add_middleware(DynamicCORSMiddleware)
else:
    # Use standard CORS middleware for specific origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"]
    )

# Security middleware for production
if os.getenv("ENVIRONMENT") in ["staging", "production"]:
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

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)