"""Connection cleanup and monitoring operations."""

import asyncio
import time
from typing import List

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ConnectionCleanupMonitor:
    """Handles connection cleanup and monitoring operations."""
    
    def __init__(self, connection_manager, heartbeat_manager, error_handler, 
                 connection_timeouts, stats, cleanup_interval):
        """Initialize cleanup monitor."""
        self.connection_manager = connection_manager
        self.heartbeat_manager = heartbeat_manager
        self.error_handler = error_handler
        self.connection_timeouts = connection_timeouts
        self.stats = stats
        self.cleanup_interval = cleanup_interval
        self.last_cleanup_time = time.time()
    
    async def cleanup_loop(self, running_flag, remove_connection_callback):
        """Background cleanup loop."""
        while running_flag():
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._run_cleanup(remove_connection_callback)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(5)  # Brief delay before retry
    
    async def _run_cleanup(self, remove_connection_callback):
        """Run connection cleanup."""
        start_time = time.time()
        self.stats["cleanup_runs"] += 1
        
        timed_out_connections = self._find_timed_out_connections()
        await self._remove_timed_out_connections(timed_out_connections, remove_connection_callback)
        await self._cleanup_dead_heartbeats()
        self._cleanup_old_errors()
        
        self.last_cleanup_time = time.time()
        
        if timed_out_connections:
            logger.info(f"Cleanup completed: removed {len(timed_out_connections)} timed out connections")
    
    def _find_timed_out_connections(self) -> List[str]:
        """Find connections that have timed out."""
        current_time = time.time()
        timed_out_connections = []
        
        for connection_id, timeout_time in self.connection_timeouts.items():
            if current_time > timeout_time:
                timed_out_connections.append(connection_id)
        
        return timed_out_connections
    
    async def _remove_timed_out_connections(self, timed_out_connections: List[str], 
                                          remove_callback) -> None:
        """Remove timed out connections."""
        for connection_id in timed_out_connections:
            logger.info(f"Removing timed out connection: {connection_id}")
            await remove_callback(connection_id)
            self.stats["timeouts"] += 1
    
    async def _cleanup_dead_heartbeats(self) -> None:
        """Clean up dead connections from heartbeat manager."""
        await self.heartbeat_manager.cleanup_dead_connections()
    
    def _cleanup_old_errors(self) -> None:
        """Clean up old error records."""
        self.error_handler.cleanup_old_errors()
    
    async def close_all_connections(self, user_connections, connection_timeouts):
        """Close all active connections."""
        connections = self.connection_manager.get_all_connections()
        
        for conn_info in connections:
            try:
                await conn_info.websocket.close()
            except Exception as e:
                logger.debug(f"Error closing connection {conn_info.connection_id}: {e}")
        
        # Clear all tracking
        user_connections.clear()
        connection_timeouts.clear()
    
    def get_health_status(self, user_connections) -> dict:
        """Get cleanup and monitoring health status."""
        return {
            "cleanup_runs": self.stats["cleanup_runs"],
            "timeouts": self.stats["timeouts"],
            "last_cleanup": self.last_cleanup_time,
            "active_connections": len(self.connection_manager.get_all_connections()),
            "user_connections": {
                user_id: len(conn_ids) 
                for user_id, conn_ids in user_connections.items()
            }
        }