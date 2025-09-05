"""
WebSocket Interface Definitions

Defines core interfaces for WebSocket functionality throughout the system.
Business Value: Platform/Internal - Ensures consistent WebSocket contracts
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol
from datetime import datetime


class WebSocketManagerProtocol(Protocol):
    """Protocol for WebSocket manager implementations."""
    
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
    
    async def close(self) -> None:
        """Close this connection."""
        ...


class WebSocketEventHandler(ABC):
    """Base class for WebSocket event handlers."""
    
    @abstractmethod
    async def handle_connect(self, connection: WebSocketConnectionProtocol) -> bool:
        """Handle new connection event."""
        pass
    
    @abstractmethod
    async def handle_disconnect(self, connection: WebSocketConnectionProtocol) -> None:
        """Handle connection disconnect event."""
        pass
    
    @abstractmethod
    async def handle_message(self, connection: WebSocketConnectionProtocol, 
                           message: Dict[str, Any]) -> bool:
        """Handle incoming message."""
        pass


class WebSocketBridge(ABC):
    """Bridge interface for WebSocket event emission."""
    
    @abstractmethod
    async def notify_agent_started(self, user_id: str, agent_name: str, 
                                 metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Notify that an agent has started."""
        pass
    
    @abstractmethod
    async def notify_agent_thinking(self, user_id: str, agent_name: str, 
                                  thought: str) -> bool:
        """Notify that an agent is thinking/reasoning."""
        pass
    
    @abstractmethod
    async def notify_tool_executing(self, user_id: str, agent_name: str,
                                  tool_name: str, tool_input: Optional[Dict] = None) -> bool:
        """Notify that a tool is being executed."""
        pass
    
    @abstractmethod
    async def notify_tool_completed(self, user_id: str, agent_name: str,
                                  tool_name: str, success: bool,
                                  result_summary: Optional[str] = None) -> bool:
        """Notify that a tool execution completed."""
        pass
    
    @abstractmethod  
    async def notify_agent_completed(self, user_id: str, agent_name: str,
                                   result: Dict[str, Any], success: bool = True) -> bool:
        """Notify that an agent has completed."""
        pass


# Compatibility types and classes

class ConnectionInfo:
    """Information about a WebSocket connection."""
    
    def __init__(self, connection_id: str, user_id: str, 
                 connected_at: Optional[datetime] = None):
        self.connection_id = connection_id
        self.user_id = user_id
        self.connected_at = connected_at or datetime.now()
        self.last_activity = self.connected_at
    
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now()
    
    def get_age_seconds(self) -> float:
        """Get connection age in seconds."""
        return (datetime.now() - self.connected_at).total_seconds()


class WebSocketState:
    """WebSocket connection state tracking."""
    
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    
    def __init__(self, initial_state: str = CONNECTING):
        self.current_state = initial_state
        self.state_history: List[tuple] = [(initial_state, datetime.now())]
    
    def transition_to(self, new_state: str) -> None:
        """Transition to new state."""
        self.current_state = new_state
        self.state_history.append((new_state, datetime.now()))
    
    def is_active(self) -> bool:
        """Check if connection is in active state."""
        return self.current_state == self.CONNECTED
    
    def get_state_duration(self) -> float:
        """Get duration in current state (seconds)."""
        if not self.state_history:
            return 0.0
        last_transition = self.state_history[-1][1]
        return (datetime.now() - last_transition).total_seconds()


# Event types for WebSocket messages
class WebSocketEventTypes:
    """Standard WebSocket event type constants."""
    
    # Agent events
    AGENT_STARTED = "agent_started"
    AGENT_THINKING = "agent_thinking"  
    AGENT_COMPLETED = "agent_completed"
    AGENT_ERROR = "agent_error"
    
    # Tool events
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


# Compatibility exports
__all__ = [
    'WebSocketManagerProtocol',
    'WebSocketConnectionProtocol', 
    'WebSocketEventHandler',
    'WebSocketBridge',
    'ConnectionInfo',
    'WebSocketState',
    'WebSocketEventTypes'
]