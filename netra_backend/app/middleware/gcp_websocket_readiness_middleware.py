"""
GCP WebSocket Readiness Middleware - SSOT Route Protection

MISSION CRITICAL: Prevents 1011 WebSocket errors by blocking WebSocket connections
until all required services are ready in GCP Cloud Run environment.

ROOT CAUSE FIX: GCP Cloud Run accepts WebSocket connections immediately after 
container start, but before backend services are fully initialized. This middleware
checks service readiness before allowing WebSocket connections.

SSOT COMPLIANCE:
- Uses existing GCP WebSocket initialization validator
- Integrates with FastAPI middleware patterns
- Uses shared.isolated_environment for environment detection
- Follows existing error handling patterns

Business Value Justification:  
- Segment: Platform/Internal
- Business Goal: Platform Stability & Chat Value Delivery
- Value Impact: Eliminates 1011 WebSocket errors preventing chat functionality
- Strategic Impact: Enables reliable WebSocket connections in production GCP environment
"""

import asyncio
import time
import logging
from typing import Callable, Dict, Any, Optional, Tuple
from starlette.requests import Request
from starlette.responses import Response
from starlette.websockets import WebSocket
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from shared.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger


class GCPWebSocketReadinessMiddleware(BaseHTTPMiddleware):
    """
    Middleware to protect WebSocket routes from 1011 errors in GCP Cloud Run.
    
    CRITICAL: This middleware prevents GCP Cloud Run from accepting WebSocket
    connections before required services are ready, which causes 1011 errors.
    
    SSOT COMPLIANCE: Uses the unified GCP WebSocket initialization validator
    and integrates with existing FastAPI middleware patterns.
    """
    
    def __init__(self, app: ASGIApp, timeout_seconds: float = 60.0):
        super().__init__(app)
        self.timeout_seconds = timeout_seconds
        self.logger = central_logger.get_logger(__name__)
        
        # Environment detection using SSOT patterns
        self.env_manager = get_env()
        self.environment = self.env_manager.get('ENVIRONMENT', '').lower()
        self.is_gcp_environment = self.environment in ['staging', 'production']
        self.is_cloud_run = self.env_manager.get('K_SERVICE') is not None
        
        # Caching for performance
        self._last_readiness_check_time = 0.0
        self._last_readiness_result = False
        self._cache_duration = 30.0  # Cache readiness for 30 seconds
        
        self.logger.info(
            f"GCP WebSocket Readiness Middleware initialized - "
            f"Environment: {self.environment}, GCP: {self.is_gcp_environment}, "
            f"Cloud Run: {self.is_cloud_run}, Timeout: {timeout_seconds}s"
        )
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Dispatch middleware logic with WebSocket route protection.
        
        CRITICAL: This prevents 1011 errors by validating service readiness 
        before allowing WebSocket connections in GCP Cloud Run.
        """
        # Only protect WebSocket routes in GCP environments
        if not self._should_protect_request(request):
            return await call_next(request)
        
        # For WebSocket connections, validate readiness
        if self._is_websocket_request(request):
            readiness_result = await self._check_websocket_readiness(request)
            
            if not readiness_result[0]:  # readiness_result is (ready: bool, details: dict)
                # Reject WebSocket connection to prevent 1011 errors
                return await self._reject_websocket_connection(request, readiness_result[1])
        
        # Proceed with request
        return await call_next(request)
    
    def _should_protect_request(self, request: Request) -> bool:
        """Determine if request should be protected by readiness validation."""
        # Only protect in GCP environments
        if not self.is_gcp_environment:
            return False
        
        # Only protect WebSocket routes
        if not self._is_websocket_request(request):
            return False
        
        return True
    
    def _is_websocket_request(self, request: Request) -> bool:
        """Check if request is a WebSocket connection attempt."""
        # Check for WebSocket upgrade headers
        connection = request.headers.get('connection', '').lower()
        upgrade = request.headers.get('upgrade', '').lower()
        
        return 'upgrade' in connection and upgrade == 'websocket'
    
    async def _check_websocket_readiness(self, request: Request) -> Tuple[bool, Dict[str, Any]]:
        """
        Check WebSocket readiness using cached results for performance.
        
        Returns:
            Tuple of (ready: bool, details: dict)
        """
        current_time = time.time()
        
        # Use cached result if still valid
        if (current_time - self._last_readiness_check_time) < self._cache_duration:
            return self._last_readiness_result, {
                "cached": True,
                "cache_age": current_time - self._last_readiness_check_time,
                "ready": self._last_readiness_result
            }
        
        # Perform new readiness check
        try:
            # Get app state from request (FastAPI pattern)
            app_state = getattr(request.app.state, '__dict__', {})
            
            # Import and use SSOT validator
            from netra_backend.app.websocket_core.gcp_initialization_validator import gcp_websocket_readiness_check
            
            ready, details = await gcp_websocket_readiness_check(request.app.state)
            
            # Cache result
            self._last_readiness_check_time = current_time
            self._last_readiness_result = ready
            
            details["cached"] = False
            details["check_time"] = current_time
            
            return ready, details
            
        except ImportError:
            # Validator not available - allow connection in non-GCP environments
            self.logger.warning("GCP WebSocket validator not available - allowing connection")
            return True, {"validator_available": False, "allowed": True}
            
        except Exception as e:
            # Error during validation
            self.logger.error(f"WebSocket readiness check error: {e}")
            
            # In GCP environments, errors should block connections
            if self.is_gcp_environment:
                return False, {"error": str(e), "blocked": True}
            else:
                return True, {"error": str(e), "allowed": True}
    
    async def _reject_websocket_connection(self, request: Request, details: Dict[str, Any]) -> Response:
        """
        Reject WebSocket connection with 503 Service Unavailable.
        
        CRITICAL: Returns 503 instead of allowing connection to fail with 1011.
        This provides better error reporting and prevents client confusion.
        """
        failed_services = details.get('failed_services', [])
        state = details.get('state', 'unknown')
        
        self.logger.warning(
            f"[U+1F6AB] Rejecting WebSocket connection - services not ready. "
            f"State: {state}, Failed services: {failed_services}, "
            f"Path: {request.url.path}"
        )
        
        # Return 503 Service Unavailable with detailed error
        error_message = {
            "error": "service_not_ready",
            "message": "WebSocket service is not ready. Please try again in a few moments.",
            "details": {
                "state": state,
                "failed_services": failed_services,
                "environment": self.environment,
                "retry_after_seconds": 10
            }
        }
        
        import json
        from starlette.responses import JSONResponse
        
        return JSONResponse(
            status_code=503,
            content=error_message,
            headers={"Retry-After": "10"}
        )


# SSOT Middleware Factory Function
def create_gcp_websocket_readiness_middleware(app=None, timeout_seconds: float = 60.0) -> type:
    """
    Create GCP WebSocket readiness middleware using SSOT patterns.
    
    SSOT COMPLIANCE: This is the canonical way to create the middleware.
    All other creation methods should delegate to this function.
    
    Args:
        app: ASGI app (can be None for middleware class)
        timeout_seconds: Timeout for readiness validation
        
    Returns:
        Configured middleware class or instance
    """
    if app is None:
        # Return configured middleware class for FastAPI add_middleware()
        class ConfiguredGCPWebSocketReadinessMiddleware(GCPWebSocketReadinessMiddleware):
            def __init__(self, app):
                super().__init__(app, timeout_seconds=timeout_seconds)
        return ConfiguredGCPWebSocketReadinessMiddleware
    else:
        # Return middleware instance
        return GCPWebSocketReadinessMiddleware(app, timeout_seconds=timeout_seconds)


# Integration with FastAPI app
def setup_gcp_websocket_protection(app, timeout_seconds: float = 60.0) -> None:
    """
    Setup GCP WebSocket protection middleware on FastAPI app.
    
    INTEGRATION: Add this to app factory to enable WebSocket route protection.
    
    Args:
        app: FastAPI application instance
        timeout_seconds: Timeout for readiness validation
        
    Usage:
        from netra_backend.app.middleware.gcp_websocket_readiness_middleware import setup_gcp_websocket_protection
        setup_gcp_websocket_protection(app)
    """
    middleware = create_gcp_websocket_readiness_middleware(timeout_seconds)
    app.add_middleware(GCPWebSocketReadinessMiddleware, timeout_seconds=timeout_seconds)
    
    logger = central_logger.get_logger(__name__)
    logger.info(f"GCP WebSocket protection middleware registered with {timeout_seconds}s timeout")


# Health check integration
async def websocket_readiness_health_check(app_state: Any) -> Dict[str, Any]:
    """
    Health check endpoint for WebSocket readiness status.
    
    INTEGRATION: Use this in /health endpoints to report WebSocket readiness.
    
    Returns:
        Health check details including readiness status
    """
    try:
        from netra_backend.app.websocket_core.gcp_initialization_validator import gcp_websocket_readiness_check
        
        ready, details = await gcp_websocket_readiness_check(app_state)
        
        return {
            "websocket_ready": ready,
            "service": "websocket_readiness",
            "status": "healthy" if ready else "degraded",
            "details": details,
            "timestamp": time.time()
        }
        
    except ImportError:
        return {
            "websocket_ready": True,
            "service": "websocket_readiness", 
            "status": "healthy",
            "details": {"validator_available": False},
            "timestamp": time.time()
        }
        
    except Exception as e:
        return {
            "websocket_ready": False,
            "service": "websocket_readiness",
            "status": "unhealthy",
            "details": {"error": str(e)},
            "timestamp": time.time()
        }