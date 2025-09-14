"""
WebSocket Interface Definitions

Defines core interfaces for WebSocket functionality throughout the system.
Business Value: Platform/Internal - Ensures consistent WebSocket contracts
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol
from datetime import datetime


class WebSocketProtocol(Protocol):
    """Protocol for WebSocket implementations."""
    
    async def send_message(self, user_id: str, message: Dict[str, Any]) -> bool:
        """Send message to user via WebSocket."""
        ...
    
    async def broadcast_message(self, message: Dict[str, Any]) -> int:
        """Broadcast message to all connected users."""
        ...
    
    def get_connection_count(self) -> int:
        """Get current connection count."""
        ...


class WebSocketConnectionProtocol(Protocol):
    """Protocol for WebSocket connection objects."""
    
    @property
    def user_id(self) -> str:
        """Get user ID for this connection."""
        ...
    
    @property 
    def connection_id(self) -> str:
        """Get connection ID."""
        ...
    
    @property
    def is_connected(self) -> bool:
        """Check if connection is active."""
        ...
    
    async def send(self, message: Dict[str, Any]) -> bool:
        """Send message through this connection."""
        ...


class WebSocketEventHandler(ABC):
    """Base class for WebSocket event handlers."""
    
    @abstractmethod
    async def handle_message(self, connection_id: str, message: Dict[str, Any]) -> None:
        """Handle incoming WebSocket message."""
        pass
    
    @abstractmethod
    async def handle_connection(self, connection_id: str, user_id: str) -> None:
        """Handle new WebSocket connection."""
        pass
    
    @abstractmethod
    async def handle_disconnection(self, connection_id: str) -> None:
        """Handle WebSocket disconnection."""
        pass


class WebSocketBridge(ABC):
    """Abstract bridge for WebSocket operations."""
    
    @abstractmethod
    async def send_agent_update(
        self, 
        run_id: str, 
        event_type: str, 
        data: Dict[str, Any],
        thread_id: Optional[str] = None
    ) -> bool:
        """Send agent update via WebSocket."""
        pass
    
    @abstractmethod
    async def notify_progress(
        self,
        run_id: str,
        progress: int,
        message: str,
        thread_id: Optional[str] = None
    ) -> bool:
        """Notify progress update."""
        pass


class ConnectionInfo:
    """Information about a WebSocket connection."""
    
    def __init__(
        self,
        connection_id: str,
        user_id: str,
        connected_at: datetime,
        last_ping: Optional[datetime] = None
    ):
        self.connection_id = connection_id
        self.user_id = user_id
        self.connected_at = connected_at
        self.last_ping = last_ping or connected_at
        self.is_active = True
    
    def update_ping(self) -> None:
        """Update last ping timestamp."""
        self.last_ping = datetime.utcnow()


class WebSocketState:
    """Represents the state of WebSocket operations."""
    
    CONNECTING = "connecting"
    CONNECTED = "connected" 
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class WebSocketEventTypes:
    """Standard WebSocket event types."""
    
    # Agent execution events
    AGENT_STARTED = "agent_started"
    AGENT_THINKING = "agent_thinking"
    AGENT_COMPLETED = "agent_completed"
    AGENT_ERROR = "agent_error"
    
    # Tool execution events
    TOOL_EXECUTING = "tool_executing"
    TOOL_COMPLETED = "tool_completed"
    
    # System events
    CONNECTION_ESTABLISHED = "connection_established"
    CONNECTION_CLOSED = "connection_closed"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    
    # Progress events  
    PROGRESS_UPDATE = "progress_update"
    STATUS_UPDATE = "status_update"


# Compatibility aliases for interface imports
WebSocketManagerInterface = WebSocketManagerProtocol
WebSocketServiceInterface = WebSocketEventHandler  # Most appropriate mapping


# Compatibility exports
__all__ = [
    'WebSocketManagerProtocol',
    'WebSocketConnectionProtocol', 
    'WebSocketEventHandler',
    'WebSocketBridge',
    'ConnectionInfo',
    'WebSocketState',
    'WebSocketEventTypes',
    # Compatibility aliases
    'WebSocketManagerInterface',
    'WebSocketServiceInterface'
]