"""
Graceful Shutdown Middleware for FastAPI

Business Value Justification (BVJ):
- Segment: Platform/Internal - Development Velocity, Risk Reduction  
- Business Goal: Zero-downtime deployments for continuous chat availability
- Value Impact: Eliminates chat interruptions during deployments
- Strategic Impact: Enables seamless scaling operations without user disruption

Tracks active requests and rejects new requests during shutdown.
"""

import uuid
import time
from typing import Callable
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from netra_backend.app.core.unified_logging import central_logger
from netra_backend.app.services.graceful_shutdown import get_shutdown_manager

logger = central_logger.get_logger(__name__)


class GracefulShutdownMiddleware(BaseHTTPMiddleware):
    """Middleware to handle graceful shutdown for HTTP requests."""
    
    def __init__(self, app, shutdown_manager=None):
        super().__init__(app)
        self.shutdown_manager = shutdown_manager or get_shutdown_manager()
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with graceful shutdown support."""
        
        # Check if we're shutting down
        if self.shutdown_manager.is_shutting_down():
            return await self._handle_shutdown_request(request)
        
        # Generate unique request ID
        from shared.id_generation.unified_id_generator import UnifiedIdGenerator
        request_id = UnifiedIdGenerator.generate_base_id("shutdown_req", random_suffix=True)[:12]  # Keep shortened format
        
        # Track request in shutdown manager
        async with self.shutdown_manager.request_context(request_id):
            try:
                # Add request metadata to request for potential logging
                request.state.request_id = request_id
                request.state.start_time = time.time()
                
                # Process request normally
                response = await call_next(request)
                
                # Log successful request completion
                duration = time.time() - request.state.start_time
                logger.debug(f"Request {request_id} completed in {duration:.3f}s")
                
                return response
                
            except Exception as e:
                # Log error and let it propagate
                duration = time.time() - request.state.start_time
                logger.error(f"Request {request_id} failed after {duration:.3f}s: {e}")
                raise
    
    async def _handle_shutdown_request(self, request: Request) -> Response:
        """Handle requests received during shutdown."""
        
        # Allow health check endpoints during shutdown
        if self._is_health_check_endpoint(request):
            logger.debug(f"Allowing health check during shutdown: {request.url.path}")
            # Let the health check proceed - it will return appropriate shutdown status
            return await self._forward_health_check(request)
        
        # Allow graceful shutdown status endpoint
        if request.url.path == "/api/shutdown/status":
            return await self._get_shutdown_status_response()
        
        # Reject all other requests during shutdown
        logger.info(f"Rejecting request during shutdown: {request.method} {request.url.path}")
        
        return JSONResponse(
            status_code=503,
            content={
                "error": "Service Unavailable",
                "message": "Service is shutting down gracefully",
                "details": {
                    "shutdown_status": self.shutdown_manager.get_shutdown_status(),
                    "retry_after": 5,  # Suggest retry after 5 seconds
                    "timestamp": time.time()
                }
            },
            headers={
                "Retry-After": "5",
                "Connection": "close"
            }
        )
    
    def _is_health_check_endpoint(self, request: Request) -> bool:
        """Check if request is for health check endpoint."""
        health_paths = [
            "/health",
            "/health/live",
            "/health/ready", 
            "/api/health",
            "/api/health/live",
            "/api/health/ready"
        ]
        return request.url.path in health_paths
    
    async def _forward_health_check(self, request: Request) -> Response:
        """Forward health check request during shutdown."""
        # This is a simple pass-through - the actual health service
        # will handle returning appropriate shutdown status
        try:
            # Import here to avoid circular imports
            from netra_backend.app.services.unified_health_service import UnifiedHealthService
            from netra_backend.app.services.health_registry import health_registry
            
            health_service = health_registry.get_service("netra_backend")
            if not health_service:
                return JSONResponse(
                    status_code=503,
                    content={"status": "unhealthy", "message": "Health service not available"}
                )
            
            # Return readiness status (which will be unhealthy during shutdown)
            if "ready" in request.url.path:
                health_response = await health_service.get_readiness()
            elif "live" in request.url.path:
                health_response = await health_service.get_liveness()
            else:
                health_response = await health_service.get_health(include_details=False)
            
            status_code = 200 if health_response.status == "healthy" else 503
            
            return JSONResponse(
                status_code=status_code,
                content=health_response.model_dump() if hasattr(health_response, 'model_dump') else health_response.__dict__
            )
            
        except Exception as e:
            logger.error(f"Error processing health check during shutdown: {e}")
            return JSONResponse(
                status_code=503,
                content={"status": "unhealthy", "error": str(e)}
            )
    
    async def _get_shutdown_status_response(self) -> Response:
        """Return shutdown status information."""
        status = self.shutdown_manager.get_shutdown_status()
        
        return JSONResponse(
            status_code=200,
            content={
                "shutdown_manager": status,
                "timestamp": time.time(),
                "service": "netra_backend"
            }
        )


def create_graceful_shutdown_middleware():
    """Factory function to create graceful shutdown middleware."""
    return GracefulShutdownMiddleware


# Health check middleware that works during shutdown
class ShutdownAwareHealthMiddleware(BaseHTTPMiddleware):
    """Specialized middleware for health checks during shutdown."""
    
    def __init__(self, app):
        super().__init__(app)
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process health check requests with shutdown awareness."""
        
        # Only handle health check paths
        if not self._is_health_path(request.url.path):
            return await call_next(request)
        
        try:
            response = await call_next(request)
            
            # Add shutdown information to health responses
            shutdown_manager = get_shutdown_manager()
            if shutdown_manager.is_shutting_down():
                # Modify response to indicate shutdown status
                if hasattr(response, 'body'):
                    # For health checks, ensure we return 503 during shutdown
                    response.status_code = 503
                    
                    # Add shutdown headers
                    response.headers["X-Shutdown-Status"] = "true"
                    response.headers["X-Shutdown-Phase"] = shutdown_manager.get_shutdown_status().get("phase", "unknown")
            
            return response
            
        except Exception as e:
            logger.error(f"Error in health check middleware: {e}")
            # Return basic unhealthy response
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": time.time()
                }
            )
    
    def _is_health_path(self, path: str) -> bool:
        """Check if path is a health check endpoint."""
        health_patterns = [
            "/health",
            "/api/health"
        ]
        return any(path.startswith(pattern) for pattern in health_patterns)