"""WebSocket Manager - Central export point for WebSocket functionality.

This module provides backward compatibility and a central import point for all
WebSocket management functionality, bridging legacy code with the new unified system.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Stability & Development Velocity  
- Value Impact: Fixes critical import errors, prevents system downtime
- Strategic Impact: Provides clean architecture migration path
"""

from typing import Any, Dict, List, Optional, Union

from fastapi import WebSocket

from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.registry import ServerMessage, WebSocketMessage
from netra_backend.app.websocket.connection import ConnectionInfo
from netra_backend.app.websocket.unified import (
    UnifiedWebSocketManager,
    get_unified_manager,
)

logger = central_logger.get_logger(__name__)


class WebSocketManager:
    """Legacy WebSocket Manager providing backward compatibility API.
    
    This class wraps the new UnifiedWebSocketManager to provide the expected
    legacy API while internally using the new unified system.
    """
    
    def __init__(self):
        """Initialize WebSocket manager with unified system."""
        self._unified_manager = get_unified_manager()
        self._connections: Dict[str, WebSocket] = {}
        self._connection_info: Dict[str, ConnectionInfo] = {}
        
    async def connect_user(self, user_id: str, websocket: WebSocket) -> ConnectionInfo:
        """Connect user to WebSocket (legacy API)."""
        conn_info = await self._unified_manager.connect_user(user_id, websocket)
        # Track for legacy API compatibility
        self._connections[conn_info.connection_id] = websocket
        self._connection_info[conn_info.connection_id] = conn_info
        return conn_info
        
    async def disconnect_user(self, user_id: str, websocket: WebSocket, 
                             code: int = 1000, reason: str = "Normal closure") -> None:
        """Disconnect user from WebSocket (legacy API)."""
        await self._unified_manager.disconnect_user(user_id, websocket, code, reason)
        # Clean up legacy tracking
        conn_id = self._find_connection_id_by_websocket(websocket)
        if conn_id:
            self._connections.pop(conn_id, None)
            self._connection_info.pop(conn_id, None)
    
    def _find_connection_id_by_websocket(self, websocket: WebSocket) -> Optional[str]:
        """Find connection ID by WebSocket instance."""
        for conn_id, ws in self._connections.items():
            if ws is websocket:
                return conn_id
        return None
        
    async def send_message_to_user(self, user_id: str, 
                                  message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]], 
                                  retry: bool = True) -> bool:
        """Send message to user (legacy API)."""
        return await self._unified_manager.send_message_to_user(user_id, message, retry)
        
    async def broadcast_to_job(self, job_id: str, 
                              message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> bool:
        """Broadcast message to job (legacy API)."""
        return await self._unified_manager.broadcast_to_job(job_id, message)
        
    async def handle_message(self, user_id: str, websocket: WebSocket, 
                           message: Dict[str, Any]) -> bool:
        """Handle incoming message (legacy API)."""
        return await self._unified_manager.handle_message(user_id, websocket, message)
        
    def validate_message(self, message: Dict[str, Any]) -> Union[bool, Any]:
        """Validate message (legacy API)."""
        return self._unified_manager.validate_message(message)
        
    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket statistics (legacy API)."""
        return self._unified_manager.get_unified_stats()
        
    @property
    def connections(self) -> Dict[str, WebSocket]:
        """Get connections dictionary (legacy API)."""
        return self._connections.copy()
        
    @property
    def connection_info(self) -> Dict[str, ConnectionInfo]:
        """Get connection info dictionary (legacy API)."""
        return self._connection_info.copy()
        
    async def shutdown(self) -> None:
        """Shutdown WebSocket manager (legacy API)."""
        await self._unified_manager.shutdown()
        self._connections.clear()
        self._connection_info.clear()


# Create global instances for backward compatibility
ws_manager = WebSocketManager()
manager = ws_manager

# Export for backward compatibility
__all__ = [
    'WebSocketManager',
    'ws_manager', 
    'manager'
]