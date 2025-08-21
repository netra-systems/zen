"""WebSocket State Synchronization Types.

Type definitions and data structures for state synchronization.
"""

from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

from app.core.exceptions_base import NetraException


class CriticalCallbackFailure(NetraException):
    """Exception for critical callback failures."""
    pass


class CallbackCriticality(str, Enum):
    """Callback criticality levels."""
    CRITICAL = "critical"
    NON_CRITICAL = "non_critical"


class SyncState(str, Enum):
    """Connection synchronization states."""
    SYNCED = "synced"
    DESYNCED = "desynced"
    SYNCING = "syncing"
    FAILED = "failed"


@dataclass
class StateCheckpoint:
    """Connection state checkpoint."""
    connection_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    websocket_state: str = ""
    internal_state: str = ""
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sync_status: SyncState = SyncState.SYNCED