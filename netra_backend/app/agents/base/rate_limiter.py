"""Rate Limiter Implementation for Agent Request Control

Agent-specific rate limiter wrapper:
- Wraps WebSocket rate limiter for agent use
- Maintains compatibility interface
- Tracks request patterns and capacity
- Provides status monitoring and control

Business Value: Prevents system overload, ensures fair resource allocation.
"""

import time
from datetime import datetime, timezone
from typing import Any, Dict

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core import ConnectionInfo
from netra_backend.app.websocket_core.rate_limiter import RateLimiter as CoreRateLimiter

logger = central_logger.get_logger(__name__)


class RateLimiter:
    """Agent-specific rate limiter wrapper around WebSocket rate limiter."""
    
    def __init__(self, max_requests: int, time_window: float):
        """Initialize with agent-specific interface."""
        self.max_requests = max_requests
        self.time_window = time_window
        self._requests = []
        
        self.core_limiter = self._create_core_limiter(max_requests, time_window)
        self._agent_conn_info = self._create_agent_connection_info()
    
    def _create_core_limiter(self, max_requests: int, time_window: float) -> CoreRateLimiter:
        """Create core rate limiter with conversion."""
        return CoreRateLimiter(
            max_requests=max_requests, 
            window_seconds=int(time_window)
        )
        
    def _create_agent_connection_info(self) -> ConnectionInfo:
        """Create mock connection info for agent rate limiting."""
        conn_info = self._build_connection_info(datetime.now(timezone.utc))
        self._initialize_rate_limit_fields(conn_info, datetime.now(timezone.utc))
        return conn_info
    
    def _build_connection_info(self, timestamp: datetime) -> ConnectionInfo:
        """Build basic connection info structure."""
        return ConnectionInfo(
            connection_id="agent_rate_limiter",
            user_id="system_agent",
            client_info={},
            connection_time=timestamp
        )
    
    def _initialize_rate_limit_fields(self, conn_info: ConnectionInfo, timestamp: datetime) -> None:
        """Initialize rate limiting fields on connection info."""
        conn_info.rate_limit_count = 0
        conn_info.rate_limit_window_start = timestamp
        
    async def acquire(self) -> bool:
        """Acquire rate limit permission."""
        is_limited = self.core_limiter.is_rate_limited(self._agent_conn_info)
        
        if not is_limited:
            self._update_local_tracking()
        
        return not is_limited
    
    def _update_local_tracking(self) -> None:
        """Update local tracking for compatibility."""
        now = time.time()
        self._cleanup_old_requests(now)
        self._requests.append(now)
    
    def _cleanup_old_requests(self, current_time: float) -> None:
        """Remove requests outside time window."""
        cutoff_time = current_time - self.time_window
        self._requests = [req_time for req_time in self._requests 
                         if req_time > cutoff_time]
    
    def get_status(self) -> Dict[str, Any]:
        """Get rate limiter status."""
        core_status = self.core_limiter.get_rate_limit_info(self._agent_conn_info)
        self._update_request_tracking()
        
        return self._build_status_response(core_status)
    
    def _update_request_tracking(self) -> None:
        """Update request tracking for compatibility."""
        now = time.time()
        self._cleanup_old_requests(now)
    
    def _build_status_response(self, core_status: Dict[str, Any]) -> Dict[str, Any]:
        """Build status response with compatibility data."""
        basic_info = self._get_basic_status_info()
        capacity_info = self._get_capacity_status_info(core_status)
        
        return {**basic_info, **capacity_info, "core_status": core_status}
    
    def _get_basic_status_info(self) -> Dict[str, Any]:
        """Get basic status information."""
        return {
            "current_requests": len(self._requests),
            "max_requests": self.max_requests,
            "time_window": self.time_window
        }
    
    def _get_capacity_status_info(self, core_status: Dict[str, Any]) -> Dict[str, Any]:
        """Get capacity status information."""
        return {
            "available_capacity": core_status.get("requests_remaining", 0)
        }