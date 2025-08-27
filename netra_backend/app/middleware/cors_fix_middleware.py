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
from shared.cors_config import get_cors_origins, is_origin_allowed

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
        """Add missing Access-Control-Allow-Origin header if needed."""
        # Get the response from the next middleware
        response = await call_next(request)
        
        # Check if CORS headers are present (indicating CORSMiddleware ran)
        has_cors_headers = (
            "access-control-allow-credentials" in response.headers or
            "access-control-expose-headers" in response.headers or
            "access-control-allow-methods" in response.headers
        )
        
        # If CORS headers exist but Access-Control-Allow-Origin is missing, add it
        if has_cors_headers and "access-control-allow-origin" not in response.headers:
            origin = request.headers.get("origin")
            if origin and is_origin_allowed(origin, self.allowed_origins, self.environment):
                response.headers["Access-Control-Allow-Origin"] = origin
                logger.debug(f"Added missing Access-Control-Allow-Origin header for {origin}")
        
        return response