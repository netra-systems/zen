"""
Security Response Middleware

Prevents information disclosure vulnerabilities by converting 404/405 responses
to 401 for unauthenticated requests to API endpoints.

Business Value Justification (BVJ):
- Segment: ALL (Security foundation for all tiers)  
- Business Goal: Prevent API surface enumeration attacks
- Value Impact: Prevents attackers from mapping API structure without authentication
- Strategic Impact: Critical security hardening against reconnaissance attacks
"""

import asyncio
from typing import Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class SecurityResponseMiddleware(BaseHTTPMiddleware):
    """
    Security middleware that prevents information disclosure through HTTP status codes.
    
    Converts 404/405 responses to 401 for API endpoints when the request
    is not authenticated, preventing attackers from mapping the API surface area.
    """
    
    def __init__(self, app):
        """Initialize security response middleware."""
        super().__init__(app)
        logger.info("SecurityResponseMiddleware initialized")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and secure responses.
        
        Completely rewritten to avoid async generator protocol issues.
        Uses a defensive approach with minimal exception handling.
        """
        
        # CRITICAL FIX: Skip middleware for health checks to prevent startup blocking
        if request.url.path in ["/health", "/health/live", "/health/ready"]:
            return await call_next(request)
        
        # For all other paths, use a simplified approach that avoids async generator issues
        try:
            response = await call_next(request)
        except Exception as e:
            # Log the exception but don't try to handle it - let it propagate
            # This avoids async generator context manager issues
            logger.warning(f"SecurityResponseMiddleware bypassed due to exception: {e}")
            raise
            
        # Only apply security transformation for successful responses  
        # Avoid any complex exception handling that could interfere with async generators
        if (response.status_code in [404, 405] and 
            self._is_api_endpoint(request.url.path) and 
            not self._is_excluded_from_auth(request.url.path) and
            not self._has_valid_auth(request)):
            
            logger.info(f"Converting HTTP {response.status_code} to 401 for protected endpoint: {request.url.path}")
            
            return JSONResponse(
                status_code=401,
                content={"error": "authentication_failed", "message": "Authentication required"},
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        return response
    
    def _is_api_endpoint(self, path: str) -> bool:
        """Check if path is an API endpoint that should be protected."""
        return path.startswith("/api/")
    
    def _has_valid_auth(self, request: Request) -> bool:
        """Check if request has valid authentication."""
        # Check if request state indicates successful authentication
        # This will be set by the auth middleware if authentication was successful
        return getattr(request.state, 'authenticated', False)
    
    def _is_excluded_from_auth(self, path: str) -> bool:
        """Check if path is excluded from authentication requirements.
        
        This should match the same exclusion logic used in FastAPIAuthMiddleware
        to ensure consistency between auth middleware and security middleware.
        """
        # Default excluded paths that match FastAPIAuthMiddleware configuration
        excluded_paths = [
            "/health", "/metrics", "/", "/docs", "/openapi.json", "/redoc",
            "/ws", "/websocket", "/ws/test", "/ws/config", "/ws/health", "/ws/stats",
            "/api/v1/auth"
        ]
        return any(excluded in path for excluded in excluded_paths)