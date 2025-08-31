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
        from analytics_service.analytics_core.database.connection import (
            get_clickhouse_manager,
            get_redis_manager
        )
        from analytics_service.analytics_core.services.event_processor import EventProcessor, ProcessorConfig
        
        # Get singleton managers from connection module
        clickhouse_manager = get_clickhouse_manager()
        await clickhouse_manager.initialize()
        
        redis_manager = get_redis_manager()
        await redis_manager.initialize()
        
        # Initialize event processor
        processor_config = ProcessorConfig(
            batch_size=config.event_batch_size,
            flush_interval_seconds=config.event_flush_interval_ms // 1000,
            max_events_per_user_per_minute=config.max_events_per_user_per_minute
        )
        event_processor = EventProcessor(
            clickhouse_manager=clickhouse_manager,
            redis_manager=redis_manager,
            config=processor_config
        )
        await event_processor.initialize()
        
        # Store managers in app state for access by routes
        app.state.clickhouse_manager = clickhouse_manager
        app.state.redis_manager = redis_manager  
        app.state.event_processor = event_processor
        
        logger.info("Service initialization completed successfully")
        logger.info(f"ClickHouse: {config.clickhouse_host}:{config.clickhouse_port}")
        logger.info(f"Redis: {config.redis_host}:{config.redis_port}")
        
    except Exception as e:
        logger.error(f"Service initialization failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down analytics service")
    
    # Clean shutdown of services
    try:
        if hasattr(app.state, 'event_processor'):
            await app.state.event_processor.stop()
        if hasattr(app.state, 'clickhouse_manager'):
            await app.state.clickhouse_manager.close()
        if hasattr(app.state, 'redis_manager'):
            await app.state.redis_manager.close()
        logger.info("Service shutdown completed successfully")
    except Exception as e:
        logger.error(f"Error during service shutdown: {e}")


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
        """Health check endpoint with real database connectivity tests."""
        from analytics_service.analytics_core.database.connection import (
            ClickHouseHealthChecker,
            RedisHealthChecker
        )
        
        health_status = {
            "status": "healthy",
            "service": config.service_name,
            "version": config.service_version,
            "environment": config.environment,
            "uptime_seconds": time.time() - SERVICE_START_TIME,
            "checks": {}
        }
        
        # Check ClickHouse health
        try:
            ch_checker = ClickHouseHealthChecker()
            ch_health = await ch_checker.check_health()
            health_status["checks"]["clickhouse"] = ch_health
            if ch_health.get("status") != "healthy":
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["checks"]["clickhouse"] = {
                "status": "error",
                "error": str(e)
            }
            health_status["status"] = "unhealthy"
        
        # Check Redis health
        try:
            redis_checker = RedisHealthChecker()
            redis_health = await redis_checker.check_health()
            health_status["checks"]["redis"] = redis_health
            if redis_health.get("status") != "healthy":
                health_status["status"] = "degraded" if health_status["status"] == "healthy" else "unhealthy"
        except Exception as e:
            health_status["checks"]["redis"] = {
                "status": "error",
                "error": str(e)
            }
            health_status["status"] = "unhealthy"
        
        return health_status
    
    # Placeholder endpoints for analytics
    @app.post("/api/analytics/events")
    async def ingest_events(request: dict = None):
        """Placeholder for event ingestion endpoint."""
        if request is None:
            request = {}
        events = request.get("events", []) if request else []
        return {
            "success": True,
            "events_processed": len(events),
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