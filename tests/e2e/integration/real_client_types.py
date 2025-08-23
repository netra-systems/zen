"""Real Client Types for E2E Testing

Data types and enums for WebSocket client state management.
"""

from dataclasses import dataclass
from enum import Enum
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
    
    def get_retry_delay(self, attempt: int) -> float:
        """Get retry delay for given attempt (exponential backoff)."""
        return min(self.retry_delay * (2 ** attempt), 30.0)
    
    def create_ssl_context(self):
        """Create SSL context for secure connections."""
        import ssl
        if self.verify_ssl:
            return ssl.create_default_context()
        else:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            return context