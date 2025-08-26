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
        """Process request and secure responses."""
        # Debug logging to see if middleware is being called
        logger.info(f"SecurityResponseMiddleware processing: {request.url.path}")
        
        # Call the next middleware/handler
        response = await call_next(request)
        
        # Debug logging for response
        logger.info(f"Response for {request.url.path}: status={response.status_code}, is_api={self._is_api_endpoint(request.url.path)}, has_auth={self._has_valid_auth(request)}")
        
        # Security check: convert 404/405 to 401 for unauthenticated API requests
        if (response.status_code in [404, 405] and 
            self._is_api_endpoint(request.url.path) and 
            not self._has_valid_auth(request)):
            
            logger.warning(f"Converting HTTP {response.status_code} to 401 for protected endpoint: {request.url.path}")
            
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