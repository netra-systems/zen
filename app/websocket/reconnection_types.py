"""WebSocket reconnection types and configuration.

Contains enums, data classes, and configuration for reconnection functionality.
Each component focused on data structures and configuration.
"""

from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum


class ReconnectionState(str, Enum):
    """Reconnection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"
    DISABLED = "disabled"


class DisconnectReason(str, Enum):
    """Disconnect reason codes."""
    NORMAL_CLOSURE = "normal_closure"
    CONNECTION_ERROR = "connection_error"
    HEARTBEAT_TIMEOUT = "heartbeat_timeout"
    AUTHENTICATION_FAILED = "authentication_failed"
    RATE_LIMITED = "rate_limited"
    SERVER_ERROR = "server_error"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown"


@dataclass
class ReconnectionConfig:
    """Reconnection configuration."""
    enabled: bool = True
    initial_delay_ms: int = 1000  # 1 second
    max_delay_ms: int = 30000     # 30 seconds
    backoff_multiplier: float = 2.0
    jitter_factor: float = 0.1    # 10% jitter
    max_attempts: int = 10
    reset_delay_after_success_ms: int = 300000  # 5 minutes
    permanent_failure_codes: List[str] = field(default_factory=lambda: [
        DisconnectReason.AUTHENTICATION_FAILED.value,
        DisconnectReason.RATE_LIMITED.value
    ])


@dataclass
class ReconnectionAttempt:
    """Single reconnection attempt record."""
    attempt_number: int
    timestamp: datetime
    delay_ms: int
    reason: str
    success: bool = False
    error_message: Optional[str] = None
    duration_ms: Optional[float] = None


@dataclass
class ReconnectionMetrics:
    """Reconnection metrics and statistics."""
    total_disconnects: int = 0
    total_reconnection_attempts: int = 0
    successful_reconnections: int = 0
    failed_reconnections: int = 0
    average_reconnection_time_ms: float = 0.0
    longest_downtime_ms: float = 0.0
    disconnect_reasons: Dict[str, int] = field(default_factory=dict)
    last_disconnect_time: Optional[datetime] = None
    last_successful_reconnect_time: Optional[datetime] = None