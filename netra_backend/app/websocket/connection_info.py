"""WebSocket Connection Data Structures

Modernized connection information models using business-focused patterns.
Split from monolithic connection.py for better modularity.

Business Value: Enables better connection tracking and monitoring.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ConnectionState(Enum):
    """Connection state enumeration for atomic state management."""
    ACTIVE = "active"
    CLOSING = "closing"
    FAILED = "failed"
    CLOSED = "closed"


@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection."""
    websocket: WebSocket
    user_id: str
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_ping: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_pong: Optional[datetime] = None
    message_count: int = 0
    error_count: int = 0
    connection_id: str = field(default_factory=lambda: f"conn_{int(time.time() * 1000)}")
    last_message_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    rate_limit_count: int = 0
    rate_limit_window_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_closing: bool = False
    state: ConnectionState = ConnectionState.ACTIVE
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    
    def transition_to_closing(self) -> bool:
        """Atomically transition to closing state."""
        if self.state == ConnectionState.ACTIVE:
            self.state = ConnectionState.CLOSING
            self.is_closing = True
            return True
        return False
        
    def transition_to_failed(self) -> None:
        """Atomically transition to failed state."""
        self.state = ConnectionState.FAILED
        self.failure_count += 1
        self.last_failure_time = datetime.now(timezone.utc)
        
    def transition_to_closed(self) -> None:
        """Atomically transition to closed state."""
        self.state = ConnectionState.CLOSED
        self.is_closing = False
        
    def is_ghost_connection(self) -> bool:
        """Check if this is a ghost connection."""
        return (self.state == ConnectionState.FAILED or 
                (self.state == ConnectionState.CLOSING and 
                 self._is_stale_closing_connection()))
                 
    def _is_stale_closing_connection(self) -> bool:
        """Check if connection has been closing for too long."""
        if not self.last_failure_time:
            return False
        time_diff = (datetime.now(timezone.utc) - 
                    self.last_failure_time).total_seconds()
        return time_diff > 60  # 60 seconds timeout
        
    def should_retry_closure(self) -> bool:
        """Check if connection closure should be retried."""
        return (self.state == ConnectionState.FAILED and 
                self.failure_count < 3)
                
    def can_be_cleaned_up(self) -> bool:
        """Check if connection can be safely cleaned up."""
        return (self.state in [ConnectionState.FAILED, ConnectionState.CLOSED] or
                self.is_ghost_connection())


@dataclass
class ConnectionStats:
    """Connection statistics for monitoring."""
    total_connections: int = 0
    successful_connections: int = 0
    failed_connections: int = 0
    connection_failures: int = 0
    active_connections: int = 0
    active_users: int = 0
    connections_by_user: Dict[str, int] = field(default_factory=dict)


class ConnectionInfoBuilder:
    """Builder for creating ConnectionInfo instances."""
    
    def __init__(self):
        self._websocket = None
        self._user_id = None
        
    def with_websocket(self, websocket: WebSocket) -> 'ConnectionInfoBuilder':
        """Set websocket for connection."""
        self._websocket = websocket
        return self
        
    def with_user_id(self, user_id: str) -> 'ConnectionInfoBuilder':
        """Set user ID for connection."""
        self._user_id = user_id
        return self
        
    def build(self) -> ConnectionInfo:
        """Build ConnectionInfo instance."""
        if not self._websocket or not self._user_id:
            raise ValueError("WebSocket and user_id required")
        return ConnectionInfo(websocket=self._websocket, user_id=self._user_id)


class ConnectionValidator:
    """Validates connection state and operations."""
    
    @staticmethod
    def is_websocket_connected(websocket: WebSocket) -> bool:
        """Check if websocket is in connected state."""
        return websocket.client_state == WebSocketState.CONNECTED
        
    @staticmethod  
    def is_websocket_safe_to_close(websocket: WebSocket) -> bool:
        """Check if websocket is safe to close."""
        return ConnectionValidator._has_valid_client_state(websocket)
        
    @staticmethod
    def _has_valid_client_state(websocket: WebSocket) -> bool:
        """Check if websocket has valid client state."""
        if not hasattr(websocket, 'client_state'):
            return False
        return websocket.client_state == WebSocketState.CONNECTED
        
    @staticmethod
    def should_attempt_close(websocket: WebSocket) -> bool:
        """Determine if close should be attempted."""
        if not ConnectionValidator._has_valid_client_state_for_close(websocket):
            return False
        return ConnectionValidator._check_application_state_for_close(websocket)
        
    @staticmethod
    def _has_valid_client_state_for_close(websocket: WebSocket) -> bool:
        """Check if websocket has valid client state for closing."""
        if not hasattr(websocket, 'client_state'):
            return False
        return websocket.client_state == WebSocketState.CONNECTED
        
    @staticmethod
    def _check_application_state_for_close(websocket: WebSocket) -> bool:
        """Check application state conditions for closing."""
        if not hasattr(websocket, 'application_state'):
            return True
        return websocket.application_state != WebSocketState.DISCONNECTED


class ConnectionMetrics:
    """Metrics collection for connections."""
    
    def __init__(self):
        self._stats = ConnectionStats()
        
    def record_connection_attempt(self) -> None:
        """Record connection attempt."""
        self._stats.total_connections += 1
        
    def record_connection_success(self) -> None:
        """Record successful connection."""
        self._stats.successful_connections += 1
        
    def record_connection_failure(self) -> None:
        """Record connection failure."""
        self._stats.failed_connections += 1
        self._stats.connection_failures += 1
        
    def update_active_counts(self, active_connections: int, active_users: int) -> None:
        """Update active connection counts."""
        self._stats.active_connections = active_connections
        self._stats.active_users = active_users
        
    def update_user_connections(self, connections_by_user: Dict[str, int]) -> None:
        """Update connections by user mapping."""
        self._stats.connections_by_user = connections_by_user.copy()
        
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics."""
        return {
            "total_connections": self._stats.total_connections,
            "successful_connections": self._stats.successful_connections,
            "failed_connections": self._stats.failed_connections,
            "connection_failures": self._stats.connection_failures,
            "active_connections": self._stats.active_connections,
            "active_users": self._stats.active_users,
            "connections_by_user": self._stats.connections_by_user
        }
        
    def reset(self) -> None:
        """Reset all metrics."""
        self._stats = ConnectionStats()


class ConnectionDurationCalculator:
    """Calculates connection duration and timing."""
    
    @staticmethod
    def calculate_duration(conn_info: ConnectionInfo) -> float:
        """Calculate connection duration in seconds."""
        return (datetime.now(timezone.utc) - conn_info.connected_at).total_seconds()
        
    @staticmethod
    def format_duration(duration: float) -> str:
        """Format duration for display."""
        return f"{duration:.1f}s"
        
    @staticmethod
    def create_duration_message(user_id: str, conn_info: ConnectionInfo) -> str:
        """Create formatted duration message."""
        duration = ConnectionDurationCalculator.calculate_duration(conn_info)
        formatted_duration = ConnectionDurationCalculator.format_duration(duration)
        return ConnectionDurationCalculator._build_message(user_id, conn_info, formatted_duration)
        
    @staticmethod
    def _build_message(user_id: str, conn_info: ConnectionInfo, 
                      formatted_duration: str) -> str:
        """Build complete message with connection details."""
        return (
            f"WebSocket disconnected for user {user_id} "
            f"(ID: {conn_info.connection_id}, Duration: {formatted_duration}, "
            f"Messages: {conn_info.message_count}, Errors: {conn_info.error_count})"
        )