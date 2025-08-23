"""WebSocket Batched Broadcast Manager.

Enhanced broadcast management with batching capabilities and micro-functions.
"""

from typing import Any, Dict, Optional, Union

from netra_backend.app.batch_message_core import MessageBatcher
from netra_backend.app.batch_message_types import BatchConfig
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.websocket_message_types import ServerMessage
from netra_backend.app.websocket.connection import ConnectionManager

logger = central_logger.get_logger(__name__)


class BatchedBroadcastManager:
    """Enhanced broadcast manager with batching capabilities and micro-functions."""
    
    def __init__(self, connection_manager: ConnectionManager, batch_config: Optional[BatchConfig] = None):
        self.connection_manager = connection_manager
        self.batch_config = batch_config or BatchConfig()
        self.message_batcher = MessageBatcher(self.batch_config, connection_manager)
        self._init_stats()
    
    def _init_stats(self) -> None:
        """Initialize broadcast statistics."""
        self._stats = {
            "total_broadcasts": 0,
            "batched_broadcasts": 0,
            "direct_broadcasts": 0
        }
    
    async def broadcast_to_user(self, user_id: str, message: Union[Dict[str, Any], ServerMessage],
                               priority: int = 1, use_batching: bool = True) -> bool:
        """Broadcast message to user with optional batching."""
        self._stats["total_broadcasts"] += 1
        return await self._route_message_by_priority(user_id, message, priority, use_batching)
    
    async def _route_message_by_priority(self, user_id: str, message: Union[Dict[str, Any], ServerMessage],
                                        priority: int, use_batching: bool) -> bool:
        """Route message based on priority and batching settings."""
        if self._should_use_batching(use_batching, priority):
            return await self._send_via_batching(user_id, message, priority)
        else:
            return await self._send_direct_broadcast(user_id, message)
    
    def _should_use_batching(self, use_batching: bool, priority: int) -> bool:
        """Determine if message should use batching."""
        return use_batching and priority < self.batch_config.priority_threshold
    
    async def _send_via_batching(self, user_id: str, message: Union[Dict[str, Any], ServerMessage], 
                                priority: int) -> bool:
        """Send message via batching system."""
        success = await self.message_batcher.queue_message(user_id, message, priority)
        if success:
            self._stats["batched_broadcasts"] += 1
        return success
    
    async def _send_direct_broadcast(self, user_id: str, message: Union[Dict[str, Any], ServerMessage]) -> bool:
        """Send message directly for high-priority broadcasts."""
        self._stats["direct_broadcasts"] += 1
        return await self._send_direct(user_id, message)
    
    async def _send_direct(self, user_id: str, message: Union[Dict[str, Any], ServerMessage]) -> bool:
        """Send message directly without batching."""
        connections = await self.connection_manager.get_user_connections(user_id)
        if not connections:
            return False
        
        success_count = await self._send_to_all_connections(connections, message)
        return success_count > 0
    
    async def _send_to_all_connections(self, connections, message: Union[Dict[str, Any], ServerMessage]) -> int:
        """Send message to all user connections."""
        success_count = 0
        for conn_info in connections:
            if await self._send_to_single_connection(conn_info, message):
                success_count += 1
        return success_count
    
    async def _send_to_single_connection(self, conn_info, message: Union[Dict[str, Any], ServerMessage]) -> bool:
        """Send message to single connection."""
        try:
            await conn_info.websocket.send_json(message)
            return self._handle_send_success(conn_info)
        except Exception as e:
            return self._handle_send_error(conn_info, e)
    
    def _handle_send_success(self, conn_info) -> bool:
        """Handle successful message send."""
        conn_info.message_count += 1
        return True
    
    def _handle_send_error(self, conn_info, error: Exception) -> bool:
        """Handle message send error."""
        logger.error(f"Error sending direct message to {conn_info.connection_id}: {error}")
        return False
    
    async def shutdown(self) -> None:
        """Shutdown broadcast manager."""
        await self.message_batcher.shutdown()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get broadcast statistics."""
        batch_stats = self.message_batcher.get_metrics()
        return self._combine_stats(batch_stats)
    
    def _combine_stats(self, batch_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Combine broadcast and batching statistics."""
        return {
            **self._stats,
            "batching": batch_stats
        }