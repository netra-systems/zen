"""Error Metrics Middleware - Tracks and reports error metrics.

This middleware tracks error rates, types, and patterns for monitoring
and alerting purposes.
"""

import logging
import time
from typing import Callable, Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class ErrorMetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for tracking error metrics and patterns."""
    
    def __init__(self, app, **kwargs):
        """Initialize the error metrics middleware."""
        super().__init__(app)
        self.error_counts: Dict[int, int] = {}
        self.error_types: Dict[str, int] = {}
        self.request_count = 0
        self.error_count = 0
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and track error metrics."""
        self.request_count += 1
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Track error status codes
            if response.status_code >= 400:
                self.error_count += 1
                self.error_counts[response.status_code] = \
                    self.error_counts.get(response.status_code, 0) + 1
                    
                # Log high error rates
                error_rate = self.error_count / self.request_count
                if error_rate > 0.1 and self.request_count > 100:
                    logger.warning(
                        f"High error rate detected: {error_rate:.2%} "
                        f"({self.error_count}/{self.request_count} requests)"
                    )
            
            return response
            
        except Exception as e:
            self.error_count += 1
            error_type = type(e).__name__
            self.error_types[error_type] = self.error_types.get(error_type, 0) + 1
            
            logger.error(f"Unhandled exception in request: {error_type}: {str(e)}")
            raise
        
        finally:
            duration = time.time() - start_time
            if duration > 5.0:  # Log slow requests
                logger.warning(f"Slow request detected: {request.url.path} took {duration:.2f}s")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current error metrics."""
        return {
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate": self.error_count / max(self.request_count, 1),
            "error_codes": dict(self.error_counts),
            "error_types": dict(self.error_types)
        }