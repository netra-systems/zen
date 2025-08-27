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
from shared.cors_config import (
    get_cors_origins, 
    is_origin_allowed, 
    validate_content_type,
    is_service_to_service_request,
    log_cors_security_event
)

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
        self.allowed_origins = get_cors_origins(environment)
        logger.info(f"CORSFixMiddleware initialized with {len(self.allowed_origins)} origins for {environment}")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Enhanced CORS processing with security features."""
        origin = request.headers.get("origin")
        request_id = request.headers.get("x-request-id", "unknown")
        path = request.url.path
        
        # CORS-013: Check for service-to-service requests
        is_s2s = is_service_to_service_request(dict(request.headers))
        
        # CORS-012: Validate Content-Type for security
        content_type = request.headers.get("content-type")
        if content_type and not validate_content_type(content_type):
            # SEC-002: Log suspicious Content-Type
            log_cors_security_event(
                event_type="suspicious_content_type",
                origin=origin or "unknown",
                path=path,
                environment=self.environment,
                request_id=request_id,
                additional_info={"content_type": content_type}
            )
            # Continue processing but log the event
        
        # Get the response from the next middleware
        response = await call_next(request)
        
        # Check if CORS headers are present (indicating CORSMiddleware ran)
        has_cors_headers = (
            "access-control-allow-credentials" in response.headers or
            "access-control-expose-headers" in response.headers or
            "access-control-allow-methods" in response.headers
        )
        
        # CORS-005: Always add Vary: Origin header to prevent CDN cache poisoning
        if origin:
            response.headers["Vary"] = "Origin"
        
        # If CORS headers exist but Access-Control-Allow-Origin is missing, add it
        if has_cors_headers and "access-control-allow-origin" not in response.headers:
            if origin:
                # Use enhanced origin validation with service-to-service bypass
                if is_origin_allowed(origin, self.allowed_origins, self.environment, service_to_service=is_s2s):
                    response.headers["Access-Control-Allow-Origin"] = origin
                    logger.debug(f"Added missing Access-Control-Allow-Origin header for {origin}")
                else:
                    # SEC-002: Log CORS validation failure
                    log_cors_security_event(
                        event_type="cors_validation_failure",
                        origin=origin,
                        path=path,
                        environment=self.environment,
                        request_id=request_id,
                        additional_info={"is_service_to_service": is_s2s}
                    )
        
        return response