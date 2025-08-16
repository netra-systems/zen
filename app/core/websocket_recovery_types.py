"""Types and data structures for WebSocket recovery system.

Defines enums, dataclasses, and configuration objects used throughout
the WebSocket connection management and recovery system.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional


class ConnectionState(Enum):
    """WebSocket connection states."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"
    CLOSING = "closing"


class ReconnectionReason(Enum):
    """Reasons for reconnection attempts."""
    CONNECTION_LOST = "connection_lost"
    NETWORK_ERROR = "network_error"
    SERVER_ERROR = "server_error"
    TIMEOUT = "timeout"
    MANUAL = "manual"


@dataclass
class ConnectionMetrics:
    """Metrics for WebSocket connection."""
    connection_id: str
    connect_time: datetime
    disconnect_time: Optional[datetime] = None
    message_count: int = 0
    error_count: int = 0
    reconnect_count: int = 0
    last_ping: Optional[datetime] = None
    last_pong: Optional[datetime] = None
    latency_ms: float = 0.0


@dataclass
class MessageState:
    """State of a WebSocket message."""
    message_id: str
    content: Dict[str, Any]
    timestamp: datetime
    ack_required: bool = False
    acknowledged: bool = False
    retry_count: int = 0


@dataclass
class ReconnectionConfig:
    """Configuration for reconnection behavior."""
    max_attempts: int = 10
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    timeout_seconds: int = 30
    
    # State preservation
    preserve_pending_messages: bool = True
    max_pending_messages: int = 1000
    message_retention_hours: int = 24