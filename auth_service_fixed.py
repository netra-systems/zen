"""
Fixed Auth Service Main Application
Handles sslmode parameter correctly for asyncpg
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import logging
from typing import Dict, Any
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from app.config import settings
from app.logging_config import central_logger
from app.routes.auth import router as auth_router

logger = central_logger.get_logger(__name__)

def fix_database_url():
    """Fix database URL for asyncpg by removing sslmode parameter"""
    db_url = os.getenv('DATABASE_URL', '')
    if not db_url:
        return
    
    # Parse the URL
    parsed = urlparse(db_url)
    
    # Parse query parameters
    query_params = parse_qs(parsed.query)
    
    # Remove sslmode if present (asyncpg doesn't support it)
    if 'sslmode' in query_params:
        del query_params['sslmode']
    
    # Rebuild query string
    new_query = urlencode(query_params, doseq=True)
    
    # Rebuild URL without sslmode
    new_parsed = parsed._replace(query=new_query)
    new_url = urlunparse(new_parsed)
    
    # Set the fixed URL
    os.environ['DATABASE_URL'] = new_url
    logger.info("Fixed database URL for asyncpg compatibility")

# Fix database URL before importing db modules
fix_database_url()

from app.db.postgres import init_db, close_db
from app.core.health import HealthInterface, HealthLevel, DatabaseHealthChecker

# Initialize unified health interface
health_interface = HealthInterface("auth-service", "1.0.0")
health_interface.register_checker(DatabaseHealthChecker("postgres"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    logger.info("Starting Auth Service (Fixed)...")
    
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
    docs_url="/docs" if os.getenv("ENVIRONMENT") != "production" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT") != "production" else None
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware for security
if os.getenv("ENVIRONMENT") == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*.netrasystems.ai", "*.run.app"]
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    health_status = await health_interface.get_health()
    status_code = 200 if health_status.level == HealthLevel.OK else 503
    return JSONResponse(content=health_status.dict(), status_code=status_code)

# Include auth routes
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Netra Auth Service",
        "version": "1.0.0",
        "status": "operational"
    }

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)