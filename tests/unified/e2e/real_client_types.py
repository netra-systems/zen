"""Real Client Types for E2E Testing

Data types and enums for WebSocket client state management.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class ConnectionState(Enum):
    """WebSocket connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


@dataclass
class ClientConfig:
    """Configuration for WebSocket client."""
    timeout: float = 5.0
    max_retries: int = 3
    retry_delay: float = 1.0
    verify_ssl: bool = True
    heartbeat_interval: Optional[float] = None