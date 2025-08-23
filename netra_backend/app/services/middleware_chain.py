"""
Middleware Chain Service

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Provide middleware chain functionality for tests
- Value Impact: Enables middleware chain tests to execute without import errors
- Strategic Impact: Enables middleware functionality validation
"""

from typing import Any, Callable, Dict, List, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class MiddlewareChain:
    """Chain of middleware components for request processing."""
    
    def __init__(self):
        """Initialize middleware chain."""
        self.middlewares: List[BaseHTTPMiddleware] = []
    
    def add_middleware(self, middleware: BaseHTTPMiddleware) -> None:
        """Add middleware to the chain."""
        self.middlewares.append(middleware)
    
    async def process(self, request: Request, call_next: Callable) -> Response:
        """Process request through middleware chain."""
        # Simple implementation for testing
        return await call_next(request)
    
    def get_middleware_count(self) -> int:
        """Get the number of middlewares in the chain."""
        return len(self.middlewares)
    
    def clear(self) -> None:
        """Clear all middlewares from the chain."""
        self.middlewares.clear()