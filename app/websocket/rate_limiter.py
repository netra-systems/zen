"""WebSocket rate limiting functionality.

Provides rate limiting capabilities for WebSocket connections to prevent abuse
and ensure fair resource usage.
"""

from datetime import datetime, timezone
from typing import Dict, Any

from app.logging_config import central_logger
from .connection import ConnectionInfo

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
        now = datetime.now(timezone.utc)
        
        # Reset counter if window has passed
        if (now - conn_info.rate_limit_window_start).total_seconds() >= self.window_seconds:
            conn_info.rate_limit_count = 0
            conn_info.rate_limit_window_start = now
        
        # Check if limit exceeded
        if conn_info.rate_limit_count >= self.max_requests:
            return True
        
        # Increment counter
        conn_info.rate_limit_count += 1
        conn_info.last_message_time = now
        return False
    
    def get_rate_limit_info(self, conn_info: ConnectionInfo) -> Dict[str, Any]:
        """Get current rate limit information for a connection.
        
        Args:
            conn_info: Connection information
            
        Returns:
            Dictionary with rate limit details
        """
        now = datetime.now(timezone.utc)
        time_in_window = (now - conn_info.rate_limit_window_start).total_seconds()
        
        # If window has passed, effective count is 0
        if time_in_window >= self.window_seconds:
            effective_count = 0
            time_remaining = self.window_seconds
        else:
            effective_count = conn_info.rate_limit_count
            time_remaining = self.window_seconds - time_in_window
        
        return {
            "max_requests": self.max_requests,
            "window_seconds": self.window_seconds,
            "current_count": effective_count,
            "time_remaining_in_window": time_remaining,
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
        # Get adaptive limit for this connection
        multiplier = self.connection_multipliers.get(conn_info.connection_id, 1.0)
        original_max = self.max_requests
        self.max_requests = int(self.base_max_requests * multiplier)
        
        try:
            result = super().is_rate_limited(conn_info)
        finally:
            self.max_requests = original_max
        
        return result
    
    def adjust_limit_for_connection(self, connection_id: str, multiplier: float):
        """Adjust rate limit multiplier for a specific connection.
        
        Args:
            connection_id: Connection to adjust limit for
            multiplier: Multiplier to apply to base rate limit (1.0 = normal, 0.5 = half, 2.0 = double)
        """
        self.connection_multipliers[connection_id] = max(0.1, min(10.0, multiplier))
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