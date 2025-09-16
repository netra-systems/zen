"""Real Client Types for E2E Testing

Minimal client type definitions for integration tests.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any

class ConnectionState(Enum):
    """WebSocket connection state enumeration."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"

@dataclass
class ClientConfig:
    """Configuration for real WebSocket client."""
    websocket_url: str
    api_base_url: str
    auth_url: Optional[str] = None
    timeout: float = 30.0
    retry_attempts: int = 3
    retry_delay: float = 2.0
    headers: Optional[Dict[str, str]] = None
    auth_token: Optional[str] = None