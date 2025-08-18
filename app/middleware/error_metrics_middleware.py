"""Error metrics collection middleware for monitoring and analytics.

Collects and tracks error metrics, request performance,
and provides monitoring insights for system health.
"""

import time
from typing import Callable, Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ErrorMetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting error metrics."""
    
    def __init__(self, app):
        """Initialize error metrics middleware."""
        super().__init__(app)
        self.error_counts: Dict[str, int] = {}
        self.last_reset = time.time()
        self.reset_interval = 300  # 5 minutes
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Collect error metrics from requests."""
        start_time = time.time()
        try:
            return await self._handle_successful_request(request, call_next, start_time)
        except Exception as error:
            await self._handle_error_request(request, error, start_time)
            raise error

    async def _handle_successful_request(self, request: Request, call_next: Callable, start_time: float) -> Response:
        """Handle successful request processing."""
        response = await call_next(request)
        duration = time.time() - start_time
        self._record_request_metric(request, response.status_code, duration)
        return response

    async def _handle_error_request(self, request: Request, error: Exception, start_time: float) -> None:
        """Handle error request processing."""
        duration = time.time() - start_time
        self._record_error_metric(request, error, duration)
    
    def _record_request_metric(
        self,
        request: Request,
        status_code: int,
        duration: float
    ) -> None:
        """Record request completion metrics."""
        self._reset_counters_if_needed()
        self._record_success_metric(request)
        self._log_slow_request_if_needed(request, duration, status_code)
    
    def _record_success_metric(self, request: Request) -> None:
        """Record successful request metric."""
        metric_key = f"{request.method}:{request.url.path}:success"
        self.error_counts[metric_key] = self.error_counts.get(metric_key, 0) + 1
    
    def _log_slow_request_if_needed(self, request: Request, duration: float, status_code: int) -> None:
        """Log slow requests that exceed threshold."""
        if duration > 5.0:
            self._log_slow_request_warning(request, duration, status_code)
    
    def _log_slow_request_warning(self, request: Request, duration: float, status_code: int) -> None:
        """Log warning for slow request."""
        logger.warning(
            f"Slow request: {request.method} {request.url.path}",
            duration_seconds=duration,
            status_code=status_code
        )
    
    def _record_error_metric(
        self,
        request: Request,
        error: Exception,
        duration: float
    ) -> None:
        """Record error metrics."""
        self._reset_counters_if_needed()
        metric_key = self._build_error_metric_key(request, error)
        self.error_counts[metric_key] = self.error_counts.get(metric_key, 0) + 1
        self._log_error_metric(metric_key, duration, error)
    
    def _build_error_metric_key(self, request: Request, error: Exception) -> str:
        """Build error metric key from request and error."""
        return f"{request.method}:{request.url.path}:error:{type(error).__name__}"
    
    def _log_error_metric(self, metric_key: str, duration: float, error: Exception) -> None:
        """Log error metric information."""
        logger.info(
            f"Error metric recorded: {metric_key}",
            duration_seconds=duration,
            error_message=str(error)
        )
    
    def _reset_counters_if_needed(self) -> None:
        """Reset error counters periodically."""
        current_time = time.time()
        if current_time - self.last_reset > self.reset_interval:
            self.error_counts.clear()
            self.last_reset = current_time
            logger.debug("Error metrics counters reset")
    
    def get_error_metrics(self) -> Dict[str, Any]:
        """Get current error metrics."""
        return {
            'error_counts': self.error_counts.copy(),
            'last_reset': self.last_reset,
            'reset_interval': self.reset_interval
        }