"""WebSocket recovery manager for multiple connections.

Manages multiple WebSocket connections with centralized recovery
and provides global connection monitoring and recovery operations.
"""

from typing import Dict, Any, Optional

from app.logging_config import central_logger
from .websocket_recovery_types import ConnectionState, ReconnectionConfig
from .websocket_connection_manager import WebSocketConnectionManager

logger = central_logger.get_logger(__name__)


class WebSocketRecoveryManager:
    """Manager for multiple WebSocket connections with recovery."""
    
    def __init__(self):
        """Initialize recovery manager."""
        self.connections: Dict[str, WebSocketConnectionManager] = {}
        self.default_config = ReconnectionConfig()
    
    async def create_connection(
        self,
        connection_id: str,
        url: str,
        config: Optional[ReconnectionConfig] = None
    ) -> WebSocketConnectionManager:
        """Create managed WebSocket connection."""
        if connection_id in self.connections:
            await self.remove_connection(connection_id)
        manager = self._create_connection_manager(connection_id, url, config)
        self._register_connection(connection_id, manager)
        return manager
    
    def _create_connection_manager(
        self, connection_id: str, url: str, config: Optional[ReconnectionConfig]
    ) -> WebSocketConnectionManager:
        """Create new connection manager instance."""
        return WebSocketConnectionManager(
            connection_id, url, config or self.default_config
        )
    
    def _register_connection(self, connection_id: str, manager: WebSocketConnectionManager) -> None:
        """Register connection in manager."""
        self.connections[connection_id] = manager
        logger.info(f"Created WebSocket connection manager: {connection_id}")
    
    async def remove_connection(self, connection_id: str) -> None:
        """Remove and cleanup connection."""
        if connection_id in self.connections:
            manager = self.connections[connection_id]
            await manager.disconnect("removed")
            del self.connections[connection_id]
            logger.info(f"Removed WebSocket connection: {connection_id}")
    
    async def recover_all_connections(self) -> Dict[str, bool]:
        """Attempt recovery for all failed connections."""
        results = {}
        for connection_id, manager in self.connections.items():
            if self._needs_recovery(manager):
                results[connection_id] = await self._attempt_connection_recovery(connection_id, manager)
        return results
    
    def _needs_recovery(self, manager: WebSocketConnectionManager) -> bool:
        """Check if connection needs recovery."""
        return manager.state in [ConnectionState.FAILED, ConnectionState.DISCONNECTED]
    
    async def _attempt_connection_recovery(self, connection_id: str, manager: WebSocketConnectionManager) -> bool:
        """Attempt recovery for single connection."""
        try:
            success = await manager.connect()
            return success
        except Exception as e:
            logger.error(f"Recovery failed for {connection_id}: {e}")
            return False
    
    def get_all_status(self) -> Dict[str, Any]:
        """Get status of all connections."""
        return {
            connection_id: manager.get_status()
            for connection_id, manager in self.connections.items()
        }
    
    async def cleanup_all(self) -> None:
        """Cleanup all connections."""
        for connection_id in list(self.connections.keys()):
            await self.remove_connection(connection_id)


# Global WebSocket recovery manager instance
websocket_recovery_manager = WebSocketRecoveryManager()