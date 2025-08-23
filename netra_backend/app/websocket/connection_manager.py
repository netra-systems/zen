"""WebSocket Connection Manager
 
Main entry point for WebSocket connection management.
Provides a unified interface to the various connection management components.

Business Value: Eliminates connection management complexity by providing a
single entry point for all WebSocket connection operations.
"""

import asyncio
from typing import Optional

from fastapi import WebSocket

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket.connection_info import ConnectionInfo, ConnectionInfoBuilder

# Import connection registry for connection tracking
from netra_backend.app.websocket.connection_registry import (
    ConnectionRegistry,
    ConnectionInfoProvider,
    ConnectionCleanupManager
)

logger = central_logger.get_logger(__name__)


class ConnectionManager:
    """Core WebSocket connection manager implementation.
    
    Provides connection lifecycle management without circular dependencies.
    """
    
    def __init__(self):
        self.registry = ConnectionRegistry()
        self.info_provider = ConnectionInfoProvider(self.registry)
        self.cleanup_manager = ConnectionCleanupManager(self.registry)
        self._connection_builder = ConnectionInfoBuilder()
        
    async def connect(self, user_id: str, websocket: WebSocket) -> ConnectionInfo:
        """Establish a new WebSocket connection."""
        # Create connection info
        conn_info = self._connection_builder.create_connection_info(user_id, websocket)
        
        # Register the connection
        await self.registry.register_connection(user_id, conn_info)
        
        logger.info(f"Connection established for user {user_id}: {conn_info.connection_id}")
        return conn_info
        
    async def find_connection(self, user_id: str, websocket: WebSocket) -> Optional[ConnectionInfo]:
        """Find an existing connection by user ID and WebSocket."""
        return await self.registry.find_connection_info(user_id, websocket)
        
    async def disconnect(self, user_id: str, websocket: WebSocket, 
                        code: int = 1000, reason: str = "Normal closure") -> None:
        """Disconnect a WebSocket connection."""
        conn_info = await self.find_connection(user_id, websocket)
        if conn_info:
            await self.cleanup_manager.cleanup_connection_registry(user_id, conn_info)
            logger.info(f"Connection disconnected for user {user_id}: {conn_info.connection_id}")
        
    async def shutdown(self) -> None:
        """Shutdown the connection manager."""
        logger.info("Shutting down connection manager...")
        await self.registry.clear_all_connections()
        
    @property
    def active_connections(self):
        """Get active connections from registry."""
        return self.registry.active_connections


def get_connection_manager() -> ConnectionManager:
    """Get the main connection manager instance."""
    return ConnectionManager()

def get_simple_websocket_manager():
    """Get a simple WebSocket manager for basic operations."""
    # Import unified manager directly
    from netra_backend.app.websocket.unified import UnifiedWebSocketManager
    return UnifiedWebSocketManager()

# Export all for backward compatibility
__all__ = [
    'ConnectionManager',
    'get_connection_manager', 
    'get_simple_websocket_manager',
    'ConnectionRegistry',
    'ConnectionInfoProvider',
    'ConnectionCleanupManager'
]