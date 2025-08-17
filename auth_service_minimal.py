"""
Minimal Auth Service Main Application
Standalone authentication microservice without LLM dependencies
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import logging

from app.config import settings
from app.logging_config import central_logger
from app.routes.auth import router as auth_router
from app.db.postgres import init_db, close_db

logger = central_logger.get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    logger.info("Starting Auth Service (Minimal)...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Log configuration
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"Service: auth-service")
    logger.info(f"Port: {os.getenv('PORT', '8080')}")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Auth Service...")
    await close_db()

# Create FastAPI app
app = FastAPI(
    title="Netra Auth Service",
    description="Authentication and Authorization Microservice",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Configure CORS
cors_origins = os.getenv("CORS_ORIGINS", "").split(",")
cors_origins = [origin.strip() for origin in cors_origins if origin.strip()]

if not cors_origins:
    # Default CORS origins for development
    cors_origins = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8080",
        "https://*.netrasystems.ai",
        "https://*.run.app"
    ]

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
app.include_router(auth_router, prefix="/api")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "auth-service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "api_docs": "/api/docs",
            "auth": "/api/auth"
        }
    }

# Health check
@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        # Basic health check - just verify service is responsive
        return {
            "status": "healthy",
            "service": "auth-service",
            "version": "1.0.0",
            "environment": os.getenv("ENVIRONMENT", "development")
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )

# Readiness check
@app.get("/ready")
async def ready():
    """Readiness check endpoint"""
    try:
        # Could add database connectivity check here if needed
        return {
            "status": "ready",
            "service": "auth-service"
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "error": str(e)}
        )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)