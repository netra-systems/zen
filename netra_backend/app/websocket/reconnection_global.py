"""Global WebSocket reconnection management.

Manages reconnection for multiple WebSocket connections across the system.
"""

from typing import Any, Dict, Optional

from netra_backend.app.reconnection_manager import WebSocketReconnectionManager
from netra_backend.app.reconnection_types import ReconnectionConfig, ReconnectionState


class GlobalReconnectionManager:
    """Manages reconnection for multiple WebSocket connections."""
    
    def __init__(self, default_config: Optional[ReconnectionConfig] = None):
        self.default_config = default_config or ReconnectionConfig()
        self.connection_managers: Dict[str, WebSocketReconnectionManager] = {}

    def get_or_create_manager(self, connection_id: str, 
                             config: Optional[ReconnectionConfig] = None) -> WebSocketReconnectionManager:
        """Get existing or create new reconnection manager."""
        if connection_id not in self.connection_managers:
            self.connection_managers[connection_id] = WebSocketReconnectionManager(
                connection_id, config or self.default_config
            )
        return self.connection_managers[connection_id]

    def remove_manager(self, connection_id: str) -> None:
        """Remove reconnection manager for a connection."""
        if connection_id in self.connection_managers:
            manager = self.connection_managers[connection_id]
            manager.stop_reconnection()
            del self.connection_managers[connection_id]

    def get_global_stats(self) -> Dict[str, Any]:
        """Get global reconnection statistics."""
        total_connections = len(self.connection_managers)
        stats_data = self._calculate_global_stats()
        return {
            "total_managed_connections": total_connections,
            **stats_data,
            "managers": self._get_managers_status()
        }

    def _calculate_global_stats(self) -> Dict[str, Any]:
        """Calculate global statistics from all managers."""
        active_reconnections = sum(1 for mgr in self.connection_managers.values() 
                                 if mgr.state == ReconnectionState.RECONNECTING)
        failed_connections = sum(1 for mgr in self.connection_managers.values() 
                               if mgr.state == ReconnectionState.FAILED)
        return {
            "active_reconnections": active_reconnections,
            "failed_connections": failed_connections
        }

    def _get_managers_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status for all managers."""
        return {
            conn_id: manager.get_status() 
            for conn_id, manager in self.connection_managers.items()
        }