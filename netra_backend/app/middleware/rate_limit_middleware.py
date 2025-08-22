"""
Rate Limiting Middleware for API protection.

Handles rate limiting functionality including:
- Request rate limiting by IP/user
- Burst protection
- Sliding window rate limiting
- Rate limit headers
- Circuit breaker patterns

Business Value Justification (BVJ):
- Segment: ALL (Infrastructure protection)
- Business Goal: Prevent abuse and ensure service stability
- Value Impact: Protects against DDoS, ensures fair usage
- Strategic Impact: Foundation for scalable API operations
"""

import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional

from netra_backend.app.core.exceptions_auth import AuthenticationError
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.auth_types import RequestContext

logger = central_logger.get_logger(__name__)


class RateLimitMiddleware:
    """Rate limiting middleware with sliding window implementation."""
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_size: int = 10,
        window_size_seconds: int = 60,
        cleanup_interval_seconds: int = 300  # 5 minutes
    ):
        """Initialize rate limit middleware.
        
        Args:
            requests_per_minute: Maximum requests per minute per client
            burst_size: Maximum burst requests allowed
            window_size_seconds: Time window for rate limiting (seconds)
            cleanup_interval_seconds: How often to clean old entries
        """
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.window_size_seconds = window_size_seconds
        self.cleanup_interval_seconds = cleanup_interval_seconds
        
        # Track requests by client identifier (IP, user_id, etc.)
        self._request_history: Dict[str, deque] = defaultdict(deque)
        self._burst_counts: Dict[str, int] = defaultdict(int)
        self._last_cleanup = time.time()
        
        logger.info(f"RateLimitMiddleware initialized: {requests_per_minute} req/min, burst={burst_size}")
    
    async def process(self, context: RequestContext, handler: Callable) -> Any:
        """Process request through rate limiting.
        
        Args:
            context: Request context
            handler: Next handler in the chain
            
        Returns:
            Handler result if rate limit not exceeded
            
        Raises:
            AuthenticationError: If rate limit is exceeded
        """
        # Clean up old entries periodically
        self._cleanup_if_needed()
        
        # Get client identifier
        client_id = self._get_client_identifier(context)
        current_time = time.time()
        
        # Check rate limits
        if self._is_rate_limited(client_id, current_time):
            self._log_rate_limit_exceeded(client_id, context)
            raise AuthenticationError("Rate limit exceeded")
        
        # Record this request
        self._record_request(client_id, current_time)
        
        # Execute handler
        result = await handler(context)
        
        # Add rate limit headers to response
        self._add_rate_limit_headers(context, client_id, current_time)
        
        return result
    
    def _get_client_identifier(self, context: RequestContext) -> str:
        """Get unique identifier for rate limiting.
        
        Args:
            context: Request context
            
        Returns:
            Client identifier (user_id if authenticated, otherwise IP)
        """
        if context.authenticated and context.user_id:
            return f"user:{context.user_id}"
        return f"ip:{context.client_ip}"
    
    def _is_rate_limited(self, client_id: str, current_time: float) -> bool:
        """Check if client is rate limited.
        
        Args:
            client_id: Client identifier
            current_time: Current timestamp
            
        Returns:
            True if client should be rate limited
        """
        # Clean old requests from this client's history
        self._clean_client_history(client_id, current_time)
        
        request_history = self._request_history[client_id]
        requests_in_window = len(request_history)
        
        # Check sliding window rate limit
        if requests_in_window >= self.requests_per_minute:
            return True
        
        # Check burst limit (requests in last 10 seconds)
        burst_window_start = current_time - 10  # 10 seconds
        recent_requests = sum(1 for req_time in request_history if req_time > burst_window_start)
        
        if recent_requests >= self.burst_size:
            return True
        
        return False
    
    def _record_request(self, client_id: str, current_time: float):
        """Record a new request for the client.
        
        Args:
            client_id: Client identifier
            current_time: Current timestamp
        """
        self._request_history[client_id].append(current_time)
        
        # Increment burst counter
        self._burst_counts[client_id] += 1
    
    def _clean_client_history(self, client_id: str, current_time: float):
        """Clean old requests from client's history.
        
        Args:
            client_id: Client identifier
            current_time: Current timestamp
        """
        history = self._request_history[client_id]
        cutoff_time = current_time - self.window_size_seconds
        
        # Remove requests outside the window
        while history and history[0] < cutoff_time:
            history.popleft()
    
    def _cleanup_if_needed(self):
        """Clean up old entries if cleanup interval has passed."""
        current_time = time.time()
        
        if current_time - self._last_cleanup < self.cleanup_interval_seconds:
            return
        
        # Clean up empty or very old entries
        clients_to_remove = []
        cutoff_time = current_time - (self.window_size_seconds * 2)  # Extra buffer
        
        for client_id, history in self._request_history.items():
            if not history or (history and history[-1] < cutoff_time):
                clients_to_remove.append(client_id)
        
        for client_id in clients_to_remove:
            del self._request_history[client_id]
            if client_id in self._burst_counts:
                del self._burst_counts[client_id]
        
        self._last_cleanup = current_time
        
        if clients_to_remove:
            logger.debug(f"Cleaned up {len(clients_to_remove)} old rate limit entries")
    
    def _add_rate_limit_headers(self, context: RequestContext, client_id: str, current_time: float):
        """Add rate limit headers to response.
        
        Args:
            context: Request context to modify
            client_id: Client identifier
            current_time: Current timestamp
        """
        if not hasattr(context, '_response_headers'):
            context._response_headers = {}
        
        history = self._request_history[client_id]
        requests_used = len(history)
        requests_remaining = max(0, self.requests_per_minute - requests_used)
        
        # Calculate reset time (when oldest request in window expires)
        if history:
            reset_time = int(history[0] + self.window_size_seconds)
        else:
            reset_time = int(current_time + self.window_size_seconds)
        
        context._response_headers.update({
            "X-RateLimit-Limit": str(self.requests_per_minute),
            "X-RateLimit-Remaining": str(requests_remaining),
            "X-RateLimit-Reset": str(reset_time),
            "X-RateLimit-Window": str(self.window_size_seconds)
        })
    
    def _log_rate_limit_exceeded(self, client_id: str, context: RequestContext):
        """Log rate limit exceeded event.
        
        Args:
            client_id: Client identifier
            context: Request context
        """
        logger.warning(
            f"Rate limit exceeded for {client_id} - "
            f"Path: {context.path} - "
            f"IP: {context.client_ip} - "
            f"User: {context.user_id or 'anonymous'}"
        )
    
    def get_client_stats(self, client_id: str) -> Dict[str, Any]:
        """Get rate limit statistics for a client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Statistics dictionary
        """
        current_time = time.time()
        self._clean_client_history(client_id, current_time)
        
        history = self._request_history[client_id]
        requests_used = len(history)
        requests_remaining = max(0, self.requests_per_minute - requests_used)
        
        return {
            "client_id": client_id,
            "requests_used": requests_used,
            "requests_remaining": requests_remaining,
            "requests_per_minute": self.requests_per_minute,
            "window_size_seconds": self.window_size_seconds,
            "reset_time": int(history[0] + self.window_size_seconds) if history else None
        }
    
    def reset_client_limits(self, client_id: str):
        """Reset rate limits for a specific client (useful for testing).
        
        Args:
            client_id: Client identifier to reset
        """
        if client_id in self._request_history:
            del self._request_history[client_id]
        if client_id in self._burst_counts:
            del self._burst_counts[client_id]
        logger.info(f"Reset rate limits for client: {client_id}")