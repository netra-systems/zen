"""WebSocket Manager Connections - Connection lifecycle management.

This module handles WebSocket connection establishment, disconnection, and cleanup operations
with proper error handling and heartbeat management.
All functions are ≤8 lines as per CLAUDE.md requirements.
"""

import time
from typing import Dict, Any

from fastapi import WebSocket

from app.logging_config import central_logger
from app.websocket.connection import ConnectionInfo
from app.ws_manager_core import WebSocketManagerCore

logger = central_logger.get_logger(__name__)


class WebSocketConnectionManager:
    """Manages WebSocket connection lifecycle operations."""

    def __init__(self, core: WebSocketManagerCore) -> None:
        """Initialize with core manager reference."""
        self.core = core

    async def establish_connection(self, user_id: str, websocket: WebSocket) -> ConnectionInfo:
        """Establish and register a new WebSocket connection."""
        conn_info = await self.core.connection_manager.connect(user_id, websocket)
        await self.core.heartbeat_manager.start_heartbeat_for_connection(conn_info)
        await self._send_connection_established(conn_info)
        return conn_info

    async def _send_connection_established(self, conn_info: ConnectionInfo) -> None:
        """Send connection established message to client."""
        message = {
            "type": "connection_established",
            "connection_id": conn_info.connection_id,
            "timestamp": time.time()
        }
        await self._send_system_message(conn_info, message)

    async def _send_system_message(self, conn_info: ConnectionInfo, message: Dict[str, Any]) -> None:
        """Send a system message to specific connection."""
        message["system"] = True
        from app.ws_manager_messaging import WebSocketMessagingManager
        messaging = WebSocketMessagingManager(self.core)
        await messaging.send_to_connection(conn_info, message, retry=False)

    async def terminate_connection(self, user_id: str, websocket: WebSocket, 
                                 code: int = 1000, reason: str = "Normal closure") -> None:
        """Properly disconnect and clean up a WebSocket connection."""
        conn_info = await self.core.connection_manager.find_connection(user_id, websocket)
        if conn_info:
            await self._cleanup_connection_resources(conn_info)
        await self.core.connection_manager.disconnect(user_id, websocket, code, reason)

    async def _cleanup_connection_resources(self, conn_info: ConnectionInfo) -> None:
        """Clean up resources for a connection."""
        await self.core.heartbeat_manager.stop_heartbeat_for_connection(conn_info.connection_id)
        self.core.broadcast_manager.leave_all_rooms(conn_info.connection_id)

    async def handle_pong_response(self, user_id: str, websocket: WebSocket) -> None:
        """Handle pong response from client for heartbeat."""
        conn_info = await self.core.connection_manager.find_connection(user_id, websocket)
        if conn_info:
            await self.core.heartbeat_manager.handle_pong(conn_info)

    def get_user_connection_info(self, user_id: str) -> list:
        """Get detailed information about user's connections."""
        return self.core.connection_manager.get_connection_info(user_id)