"""WebSocket reconnection types and configuration.

Contains enums, data classes, and configuration for reconnection functionality.
Each component focused on data structures and configuration.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


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


class CallbackCriticality(str, Enum):
    """Callback criticality levels."""
    CRITICAL = "critical"
    IMPORTANT = "important"
    NON_CRITICAL = "non_critical"


class CallbackType(str, Enum):
    """Callback type identifiers."""
    STATE_CHANGE = "state_change"
    CONNECT = "connect"
    DISCONNECT = "disconnect"


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
class CallbackFailure:
    """Callback failure record."""
    callback_type: CallbackType
    timestamp: datetime
    error_message: str
    criticality: CallbackCriticality


@dataclass
class CallbackCircuitBreaker:
    """Circuit breaker for callback failures."""
    failure_threshold: int = 3
    reset_timeout_ms: int = 60000  # 1 minute
    is_open: bool = False
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    recent_failures: List[CallbackFailure] = field(default_factory=list)


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
    callback_failures: Dict[str, int] = field(default_factory=dict)
    critical_callback_failures: int = 0