"""
CORS Fix Middleware

This middleware adds the missing Access-Control-Allow-Origin header
that FastAPI's CORSMiddleware fails to add when allow_credentials=True.

Business Value Justification (BVJ):
- Segment: ALL (Required for frontend-backend communication)
- Business Goal: Enable secure cross-origin requests
- Value Impact: Fixes browser CORS errors that block user interactions
- Strategic Impact: Ensures microservice architecture works correctly
"""

import logging
from typing import Callable
from fastapi import Request
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from shared.cors_config_builder import CORSConfigurationBuilder

logger = logging.getLogger(__name__)


class CORSFixMiddleware(BaseHTTPMiddleware):
    """
    Middleware to fix missing Access-Control-Allow-Origin header.
    
    This runs AFTER FastAPI's CORSMiddleware to add the missing
    Access-Control-Allow-Origin header when the origin is valid.
    """
    
    def __init__(self, app, environment: str = "development"):
        """Initialize CORS fix middleware."""
        super().__init__(app)
        self.environment = environment
        
        # Initialize CORS configuration builder
        env_vars = {"ENVIRONMENT": environment} if environment else None
        self.cors = CORSConfigurationBuilder(env_vars)
        self.allowed_origins = self.cors.origins.allowed
        logger.info(f"CORSFixMiddleware initialized with {len(self.allowed_origins)} origins for {self.cors.environment}")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Enhanced CORS processing with security features and error handling."""
        origin = request.headers.get("origin")
        request_id = request.headers.get("x-request-id", "unknown")
        path = request.url.path
        
        # CORS-013: Check for service-to-service requests
        is_s2s = self.cors.service_detector.is_internal_request(dict(request.headers))
        
        # CORS-012: Validate Content-Type for security
        content_type = request.headers.get("content-type")
        if content_type and not self.cors.security.validate_content_type(content_type):
            # SEC-002: Log suspicious Content-Type
            self.cors.security.log_security_event(
                event_type="suspicious_content_type",
                origin=origin or "unknown",
                path=path,
                request_id=request_id,
                additional_info={"content_type": content_type}
            )
            # Continue processing but log the event
        
        try:
            # Get the response from the next middleware
            # call_next is always a callable in FastAPI middleware
            response = await call_next(request)
        except Exception as e:
            # On error, create an error response with CORS headers
            logger.error(f"Error processing request: {e}")
            
            # Create error response
            from fastapi.responses import JSONResponse
            response = JSONResponse(
                status_code=500,
                content={"error": "Internal server error"}
            )
            
            # Add CORS headers to error response if origin is allowed
            if origin and self.cors.origins.is_allowed(origin, service_to_service=is_s2s):
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD"
                response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Request-ID, X-Trace-ID, Accept, Origin, Referer, X-Requested-With, X-Service-Name"
                response.headers["Access-Control-Expose-Headers"] = "X-Trace-ID, X-Request-ID, Content-Length, Content-Type, Vary"
                response.headers["Vary"] = "Origin"
            
            return response
        
        # Check if CORS headers are present (indicating CORSMiddleware ran)
        has_cors_headers = (
            "access-control-allow-credentials" in response.headers or
            "access-control-expose-headers" in response.headers or
            "access-control-allow-methods" in response.headers
        )
        
        # CORS-005: Always add Vary: Origin header to prevent CDN cache poisoning
        if origin:
            response.headers["Vary"] = "Origin"
        
        # Always ensure CORS headers are present for allowed origins (including error responses)
        if origin and self.cors.origins.is_allowed(origin, service_to_service=is_s2s):
            # If no CORS headers at all, add full set
            if not has_cors_headers and "access-control-allow-origin" not in response.headers:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD"
                response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Request-ID, X-Trace-ID, Accept, Origin, Referer, X-Requested-With, X-Service-Name"
                response.headers["Access-Control-Expose-Headers"] = "X-Trace-ID, X-Request-ID, Content-Length, Content-Type, Vary"
                logger.debug(f"Added full CORS headers for {origin} on response with status {response.status_code}")
            # If CORS headers exist but Access-Control-Allow-Origin is missing, add it
            elif has_cors_headers and "access-control-allow-origin" not in response.headers:
                response.headers["Access-Control-Allow-Origin"] = origin
                logger.debug(f"Added missing Access-Control-Allow-Origin header for {origin}")
        elif origin and not self.cors.origins.is_allowed(origin, service_to_service=is_s2s):
            # SEC-002: Log CORS validation failure
            self.cors.security.log_security_event(
                event_type="cors_validation_failure",
                origin=origin,
                path=path,
                request_id=request_id,
                additional_info={"is_service_to_service": is_s2s}
            )
        
        return response