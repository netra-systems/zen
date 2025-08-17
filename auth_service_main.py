"""
Auth Service Main Application
Dedicated microservice for authentication and authorization
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
    logger.info("Starting Auth Service...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Log configuration
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"Service: {os.getenv('SERVICE_NAME', 'auth-service')}")
    logger.info(f"CORS Origins: {os.getenv('CORS_ORIGINS', '')}")
    
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
    # Default CORS origins
    cors_origins = [
        "http://localhost:3000",
        "http://localhost:8080",
        "https://staging.netrasystems.ai",
        "https://app.staging.netrasystems.ai"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Security middleware
if os.getenv("ENVIRONMENT") in ["staging", "production"]:
    allowed_hosts = [
        "*.netrasystems.ai",
        "*.run.app",
        "auth.staging.netrasystems.ai",
        "auth.netrasystems.ai"
    ]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

# Custom middleware for auth service headers
@app.middleware("http")
async def add_auth_service_headers(request: Request, call_next):
    """Add auth service specific headers"""
    response = await call_next(request)
    response.headers["X-Service-Name"] = "auth-service"
    response.headers["X-Service-Version"] = "1.0.0"
    
    # Security headers
    if os.getenv("SECURE_HEADERS_ENABLED", "false").lower() == "true":
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    return response

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "auth-service",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development")
    }

@app.get("/api/health")
async def api_health_check():
    """Alternative health check endpoint"""
    return await health_check()

# Include auth routes
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Netra Auth Service",
        "version": "1.0.0",
        "status": "running",
        "docs": "/api/docs"
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "service": "auth-service"
        }
    )

# OAuth error handler
@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc):
    """Handle unauthorized access"""
    return JSONResponse(
        status_code=401,
        content={
            "detail": "Unauthorized",
            "service": "auth-service"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=os.getenv("ENVIRONMENT") == "development",
        workers=2 if os.getenv("ENVIRONMENT") != "development" else 1
    )