"""
CORS Middleware for Cross-Origin Resource Sharing.

Handles CORS (Cross-Origin Resource Sharing) functionality including:
- Origin validation against allowed origins
- Preflight request handling
- CORS headers management
- Security policy enforcement

Business Value Justification (BVJ):
- Segment: ALL (Frontend integration requirement)
- Business Goal: Enable secure frontend-backend communication
- Value Impact: Allows web app functionality while maintaining security
- Strategic Impact: Foundation for web application architecture
"""

from typing import Any, Callable, List, Optional, Set

from netra_backend.app.core.exceptions_auth import AuthenticationError
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.auth_types import RequestContext

logger = central_logger.get_logger(__name__)


class CORSMiddleware:
    """CORS middleware for handling cross-origin requests."""
    
    def __init__(
        self,
        allowed_origins: List[str] = None,
        allowed_methods: List[str] = None,
        allowed_headers: List[str] = None,
        allow_credentials: bool = True,
        max_age: int = 86400  # 24 hours
    ):
        """Initialize CORS middleware.
        
        Args:
            allowed_origins: List of allowed origin URLs
            allowed_methods: List of allowed HTTP methods
            allowed_headers: List of allowed request headers
            allow_credentials: Whether to allow credentials
            max_age: Max age for preflight cache (seconds)
        """
        self.allowed_origins = set(allowed_origins or [
            "http://localhost:3000",
            "https://app.netrasystems.ai",
            "https://auth.netrasystems.ai"
        ])
        self.allowed_methods = set(allowed_methods or [
            "GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"
        ])
        self.allowed_headers = set(allowed_headers or [
            "Authorization", "Content-Type", "Accept", "Origin", 
            "X-Requested-With", "Cache-Control"
        ])
        self.allow_credentials = allow_credentials
        self.max_age = max_age
        
        logger.info(f"CORSMiddleware initialized with {len(self.allowed_origins)} allowed origins")
    
    async def process(self, context: RequestContext, handler: Callable) -> Any:
        """Process CORS for the request.
        
        Args:
            context: Request context
            handler: Next handler in the chain
            
        Returns:
            Handler result with CORS headers applied
            
        Raises:
            AuthenticationError: If origin is not allowed
        """
        origin = context.headers.get("Origin")
        
        # Handle preflight requests
        if context.method == "OPTIONS":
            return self._handle_preflight(context, origin)
        
        # Validate origin for actual requests
        if origin and not self.is_allowed_origin(origin):
            raise AuthenticationError(f"Origin {origin} not allowed")
        
        # Execute handler
        result = await handler(context)
        
        # Add CORS headers to response
        self._add_cors_headers(context, origin)
        
        return result
    
    def _handle_preflight(self, context: RequestContext, origin: Optional[str]) -> dict:
        """Handle CORS preflight request.
        
        Args:
            context: Request context
            origin: Request origin
            
        Returns:
            Preflight response
            
        Raises:
            AuthenticationError: If preflight request is invalid
        """
        if not origin or not self.is_allowed_origin(origin):
            raise AuthenticationError("CORS preflight failed: invalid origin")
        
        # Check requested method
        requested_method = context.headers.get("Access-Control-Request-Method")
        if requested_method and requested_method not in self.allowed_methods:
            raise AuthenticationError(f"Method {requested_method} not allowed")
        
        # Check requested headers
        requested_headers = context.headers.get("Access-Control-Request-Headers", "")
        if requested_headers:
            headers_list = [h.strip() for h in requested_headers.split(",")]
            if not all(h.lower() in {ah.lower() for ah in self.allowed_headers} for h in headers_list):
                raise AuthenticationError("Requested headers not allowed")
        
        # Add preflight response headers
        response_headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": ", ".join(self.allowed_methods),
            "Access-Control-Allow-Headers": ", ".join(self.allowed_headers),
            "Access-Control-Max-Age": str(self.max_age)
        }
        
        if self.allow_credentials:
            response_headers["Access-Control-Allow-Credentials"] = "true"
        
        return {
            "status": "preflight_ok",
            "headers": response_headers
        }
    
    def _add_cors_headers(self, context: RequestContext, origin: Optional[str]):
        """Add CORS headers to response context.
        
        Args:
            context: Request context to modify
            origin: Request origin
        """
        if not hasattr(context, '_response_headers'):
            context._response_headers = {}
        
        if origin and self.is_allowed_origin(origin):
            context._response_headers["Access-Control-Allow-Origin"] = origin
            
            if self.allow_credentials:
                context._response_headers["Access-Control-Allow-Credentials"] = "true"
            
            # Add other CORS headers
            context._response_headers["Access-Control-Allow-Methods"] = ", ".join(self.allowed_methods)
            context._response_headers["Access-Control-Allow-Headers"] = ", ".join(self.allowed_headers)
            context._response_headers["Access-Control-Expose-Headers"] = "Content-Length, Content-Type"
    
    def is_allowed_origin(self, origin: str) -> bool:
        """Check if origin is allowed.
        
        Args:
            origin: Origin URL to check
            
        Returns:
            True if origin is allowed
        """
        if not origin:
            return False
        
        # Direct match
        if origin in self.allowed_origins:
            return True
        
        # Wildcard support (e.g., "https://*.netrasystems.ai")
        for allowed in self.allowed_origins:
            if "*" in allowed:
                pattern = allowed.replace("*", ".*")
                import re
                if re.match(pattern, origin):
                    return True
        
        return False
    
    def add_allowed_origin(self, origin: str):
        """Add a new allowed origin (useful for dynamic configuration).
        
        Args:
            origin: Origin URL to add
        """
        self.allowed_origins.add(origin)
        logger.info(f"Added allowed origin: {origin}")
    
    def remove_allowed_origin(self, origin: str):
        """Remove an allowed origin.
        
        Args:
            origin: Origin URL to remove
        """
        self.allowed_origins.discard(origin)
        logger.info(f"Removed allowed origin: {origin}")
    
    def get_allowed_origins(self) -> List[str]:
        """Get list of all allowed origins.
        
        Returns:
            List of allowed origin URLs
        """
        return list(self.allowed_origins)