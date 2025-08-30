"""
Analytics Service Main Application

FastAPI application entry point for the analytics microservice.
Follows microservice independence patterns with service-specific configuration.
"""
import os
import sys
from pathlib import Path

# Add parent directory to Python path for analytics_service imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from analytics_service.analytics_core.config import get_config, get_service_port

# Setup logging before importing other modules
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Track service start time
SERVICE_START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup
    config = get_config()
    logger.info(f"Starting {config.service_name} v{config.service_version}")
    logger.info(f"Environment: {config.environment}")
    logger.info(f"Port: {config.service_port}")
    logger.info(f"Configuration: {config.mask_sensitive_config()}")
    
    # Initialize services (database connections, etc.)
    try:
        # TODO: Add service initialization (ClickHouse, Redis, etc.)
        logger.info("Service initialization completed")
    except Exception as e:
        logger.error(f"Service initialization failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down analytics service")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    config = get_config()
    
    app = FastAPI(
        title="Netra Analytics Service",
        description="Analytics and event processing microservice for Netra AI Optimization Platform",
        version=config.service_version,
        docs_url="/docs" if config.is_development else None,
        redoc_url="/redoc" if config.is_development else None,
        lifespan=lifespan
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    
    # Request logging middleware
    if config.enable_request_logging:
        @app.middleware("http")
        async def log_requests(request: Request, call_next):
            start_time = time.time()
            response = await call_next(request)
            process_time = time.time() - start_time
            
            if request.url.path not in ["/health", "/health/ready", "/health/live"]:
                logger.info(
                    f"{request.method} {request.url.path} - "
                    f"Status: {response.status_code} - "
                    f"Time: {process_time:.3f}s"
                )
            return response
    
    # Exception handlers
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
    
    # Include routers (when they're created)
    # app.include_router(health_routes.router)
    # app.include_router(analytics_routes.router)
    # app.include_router(websocket_routes.router)
    
    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "service": config.service_name,
            "version": config.service_version,
            "environment": config.environment,
            "status": "running",
            "uptime_seconds": time.time() - SERVICE_START_TIME
        }
    
    # Basic health check endpoint
    @app.get("/health")
    async def health():
        return {
            "status": "healthy",
            "service": config.service_name,
            "version": config.service_version,
            "uptime_seconds": time.time() - SERVICE_START_TIME
        }
    
    # Placeholder endpoints for analytics
    @app.post("/api/analytics/events")
    async def ingest_events(request: dict):
        """Placeholder for event ingestion endpoint."""
        return {
            "success": True,
            "events_processed": len(request.get("events", [])),
            "message": "Event ingestion endpoint (placeholder)"
        }
    
    @app.get("/api/analytics/reports/user-activity")
    async def get_user_activity():
        """Placeholder for user activity report endpoint."""
        return {
            "success": True,
            "data": [],
            "message": "User activity report endpoint (placeholder)"
        }
    
    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    config = get_config()
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=config.service_port,
        workers=config.worker_count,
        reload=config.is_development,
        log_level=config.log_level.lower(),
        access_log=config.enable_request_logging
    )