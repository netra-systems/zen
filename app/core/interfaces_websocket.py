"""WebSocket-related service interfaces.

This module provides interfaces for WebSocket services and real-time communication.
Defines core WebSocket service interfaces for the application.
"""

from typing import Any, Dict, Optional, Protocol
from .interfaces_service import BaseServiceInterface


class WebSocketServiceInterface(BaseServiceInterface, Protocol):
    """Interface for WebSocket services."""
    
    async def connect_client(self, client_id: str, websocket: Any) -> None:
        """Connect a WebSocket client."""
        ...
    
    async def disconnect_client(self, client_id: str) -> None:
        """Disconnect a WebSocket client."""
        ...
    
    async def broadcast_message(self, message: Dict[str, Any]) -> None:
        """Broadcast message to all connected clients."""
        ...
    
    async def send_to_client(self, client_id: str, message: Dict[str, Any]) -> None:
        """Send message to specific client."""
        ...
    
    async def get_connected_clients(self) -> Dict[str, Any]:
        """Get list of connected clients."""
        ...


class WebSocketManagerInterface(Protocol):
    """Interface for WebSocket connection management."""
    
    async def add_connection(self, connection_id: str, websocket: Any) -> None:
        """Add a new WebSocket connection."""
        ...
    
    async def remove_connection(self, connection_id: str) -> None:
        """Remove a WebSocket connection."""
        ...
    
    async def send_to_connection(self, connection_id: str, data: Any) -> bool:
        """Send data to a specific connection."""
        ...
    
    async def broadcast_to_all(self, data: Any) -> int:
        """Broadcast data to all connections."""
        ...
    
    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        ...