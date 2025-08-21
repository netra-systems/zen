"""WebSocket rate limiting functionality.

Provides rate limiting capabilities for WebSocket connections to prevent abuse
and ensure fair resource usage.

UPDATED: Now uses canonical rate limit types from app.schemas.rate_limit_types
"""

from datetime import datetime, timezone
from typing import Dict, Any

from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.rate_limit_types import RateLimitConfig, RateLimitResult, TokenBucket
from netra_backend.app.connection import ConnectionInfo

logger = central_logger.get_logger(__name__)


class RateLimiter:
    """Rate limiter for WebSocket connections."""
    
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        """Initialize rate limiter with configurable limits.
        
        Args:
            max_requests: Maximum requests allowed per window
            window_seconds: Time window duration in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    def is_rate_limited(self, conn_info: ConnectionInfo) -> bool:
        """Check if connection is rate limited.
        
        Args:
            conn_info: Connection information to check
            
        Returns:
            True if the connection is rate limited, False otherwise
        """
        return self._evaluate_rate_limit(conn_info)
    
    def _evaluate_rate_limit(self, conn_info: ConnectionInfo) -> bool:
        """Evaluate rate limit for connection."""
        now = datetime.now(timezone.utc)
        self._reset_window_if_expired(conn_info, now)
        if self._is_limit_exceeded(conn_info):
            return True
        self._increment_request_counter(conn_info, now)
        return False
    
    def _reset_window_if_expired(self, conn_info: ConnectionInfo, now: datetime) -> None:
        """Reset counter if rate limit window has passed."""
        if (now - conn_info.rate_limit_window_start).total_seconds() >= self.window_seconds:
            conn_info.rate_limit_count = 0
            conn_info.rate_limit_window_start = now
    
    def _is_limit_exceeded(self, conn_info: ConnectionInfo) -> bool:
        """Check if rate limit is exceeded."""
        return conn_info.rate_limit_count >= self.max_requests
    
    def _increment_request_counter(self, conn_info: ConnectionInfo, now: datetime) -> None:
        """Increment request counter and update timestamp."""
        conn_info.rate_limit_count += 1
        conn_info.last_message_time = now
    
    def get_rate_limit_info(self, conn_info: ConnectionInfo) -> Dict[str, Any]:
        """Get current rate limit information for a connection.
        
        Args:
            conn_info: Connection information
            
        Returns:
            Dictionary with rate limit details
        """
        return self._build_rate_limit_info(conn_info)
    
    def _build_rate_limit_info(self, conn_info: ConnectionInfo) -> Dict[str, Any]:
        """Build rate limit information dictionary."""
        now = datetime.now(timezone.utc)
        time_in_window = self._calculate_time_in_window(conn_info, now)
        effective_count, time_remaining = self._calculate_effective_values(conn_info, time_in_window)
        return self._create_rate_limit_dict(effective_count, time_remaining)
    
    def _calculate_time_in_window(self, conn_info: ConnectionInfo, now: datetime) -> float:
        """Calculate time elapsed in current window."""
        return (now - conn_info.rate_limit_window_start).total_seconds()
    
    def _calculate_effective_values(self, conn_info: ConnectionInfo, time_in_window: float) -> tuple:
        """Calculate effective count and time remaining."""
        if time_in_window >= self.window_seconds:
            return 0, self.window_seconds
        return conn_info.rate_limit_count, self.window_seconds - time_in_window
    
    def _create_rate_limit_dict(self, effective_count: int, time_remaining: float) -> Dict[str, Any]:
        """Create rate limit information dictionary."""
        basic_info = self._get_basic_rate_info(effective_count, time_remaining)
        status_info = self._get_rate_status_info(effective_count)
        return {**basic_info, **status_info}
    
    def _get_basic_rate_info(self, effective_count: int, time_remaining: float) -> Dict[str, Any]:
        """Get basic rate limit information."""
        return {
            "max_requests": self.max_requests,
            "window_seconds": self.window_seconds,
            "current_count": effective_count,
            "time_remaining_in_window": time_remaining
        }
    
    def _get_rate_status_info(self, effective_count: int) -> Dict[str, Any]:
        """Get rate limit status information."""
        return {
            "is_limited": effective_count >= self.max_requests,
            "requests_remaining": max(0, self.max_requests - effective_count)
        }
    
    def reset_rate_limit(self, conn_info: ConnectionInfo):
        """Reset rate limit for a connection.
        
        Args:
            conn_info: Connection to reset rate limit for
        """
        conn_info.rate_limit_count = 0
        conn_info.rate_limit_window_start = datetime.now(timezone.utc)
        logger.info(f"Rate limit reset for connection {conn_info.connection_id}")


class AdaptiveRateLimiter(RateLimiter):
    """Adaptive rate limiter that adjusts limits based on connection behavior."""
    
    def __init__(self, base_max_requests: int = 60, window_seconds: int = 60):
        """Initialize adaptive rate limiter.
        
        Args:
            base_max_requests: Base maximum requests per window
            window_seconds: Time window duration in seconds
        """
        super().__init__(base_max_requests, window_seconds)
        self.base_max_requests = base_max_requests
        self.connection_multipliers: Dict[str, float] = {}
    
    def is_rate_limited(self, conn_info: ConnectionInfo) -> bool:
        """Check if connection is rate limited with adaptive limits."""
        adaptive_limit = self._get_adaptive_limit(conn_info.connection_id)
        return self._check_with_temporary_limit(conn_info, adaptive_limit)
    
    def _get_adaptive_limit(self, connection_id: str) -> int:
        """Get adaptive rate limit for connection."""
        multiplier = self.connection_multipliers.get(connection_id, 1.0)
        return int(self.base_max_requests * multiplier)
    
    def _check_with_temporary_limit(self, conn_info: ConnectionInfo, adaptive_limit: int) -> bool:
        """Check rate limit with temporary limit adjustment."""
        original_max = self.max_requests
        self.max_requests = adaptive_limit
        try:
            return super().is_rate_limited(conn_info)
        finally:
            self.max_requests = original_max
    
    def adjust_limit_for_connection(self, connection_id: str, multiplier: float):
        """Adjust rate limit multiplier for a specific connection.
        
        Args:
            connection_id: Connection to adjust limit for
            multiplier: Multiplier to apply to base rate limit (1.0 = normal, 0.5 = half, 2.0 = double)
        """
        validated_multiplier = self._validate_multiplier(multiplier)
        self._apply_multiplier(connection_id, validated_multiplier)
    
    def _validate_multiplier(self, multiplier: float) -> float:
        """Validate and clamp multiplier to safe range."""
        return max(0.1, min(10.0, multiplier))
    
    def _apply_multiplier(self, connection_id: str, multiplier: float) -> None:
        """Apply validated multiplier to connection."""
        self.connection_multipliers[connection_id] = multiplier
        logger.info(f"Rate limit multiplier for connection {connection_id} set to {multiplier}")
    
    def promote_connection(self, connection_id: str):
        """Increase rate limit for a well-behaved connection."""
        current_multiplier = self.connection_multipliers.get(connection_id, 1.0)
        new_multiplier = min(2.0, current_multiplier * 1.2)
        self.adjust_limit_for_connection(connection_id, new_multiplier)
    
    def demote_connection(self, connection_id: str):
        """Decrease rate limit for a problematic connection."""
        current_multiplier = self.connection_multipliers.get(connection_id, 1.0)
        new_multiplier = max(0.1, current_multiplier * 0.8)
        self.adjust_limit_for_connection(connection_id, new_multiplier)
    
    def cleanup_multipliers(self, active_connection_ids: set):
        """Clean up multipliers for connections that no longer exist."""
        inactive_ids = set(self.connection_multipliers.keys()) - active_connection_ids
        for conn_id in inactive_ids:
            del self.connection_multipliers[conn_id]


# Default rate limiter instance
default_rate_limiter = RateLimiter(max_requests=60, window_seconds=60)