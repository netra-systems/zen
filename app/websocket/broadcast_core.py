"""Core WebSocket broadcasting functionality - Modernized.

Backward-compatible entry point that delegates to the modern WebSocketBroadcastExecutor
while maintaining all existing API contracts for seamless migration.

Business Value: Zero-disruption migration to modern reliability patterns.
"""

from typing import Dict, List, Any, Union, Optional

from app.logging_config import central_logger
from app.schemas.registry import WebSocketMessage
from app.schemas.websocket_message_types import ServerMessage, BroadcastResult
from app.websocket.connection import ConnectionInfo, ConnectionManager
from app.websocket.room_manager import RoomManager
from app.websocket.websocket_broadcast_executor import (
    WebSocketBroadcastExecutor, BroadcastContext, BroadcastOperation
)
from app.websocket import broadcast_utils as utils

logger = central_logger.get_logger(__name__)


class BroadcastManager:
    """Backward-compatible WebSocket broadcast manager.
    
    Delegates to modern WebSocketBroadcastExecutor while maintaining
    exact API compatibility for existing code.
    """
    
    def __init__(self, connection_manager: ConnectionManager, 
                 room_manager: RoomManager = None,
                 reliability_config: Optional[Dict[str, Any]] = None):
        """Initialize broadcast manager with modern agent delegation."""
        self.connection_manager = connection_manager
        self._initialize_modern_agent(connection_manager, room_manager, reliability_config)
        self._setup_legacy_compatibility()
    
    def _initialize_modern_agent(self, connection_manager: ConnectionManager, 
                               room_manager: RoomManager, 
                               reliability_config: Optional[Dict[str, Any]]) -> None:
        """Initialize the modern agent instance."""
        self._modern_agent = self._init_modern_agent(
            connection_manager, room_manager, reliability_config
        )
    
    def _setup_legacy_compatibility(self) -> None:
        """Setup legacy property compatibility."""
        self.room_manager = self._modern_agent.room_manager
        self.executor = self._modern_agent.executor
    
    def _init_modern_agent(self, connection_manager: ConnectionManager,
                          room_manager: RoomManager,
                          reliability_config: Optional[Dict[str, Any]]) -> WebSocketBroadcastExecutor:
        """Initialize modern WebSocket broadcast executor."""
        agent_params = self._get_agent_init_params(
            connection_manager, room_manager, reliability_config
        )
        return WebSocketBroadcastExecutor(**agent_params)
    
    def _get_agent_init_params(self, connection_manager: ConnectionManager,
                              room_manager: RoomManager,
                              reliability_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Get parameters for agent initialization."""
        params = self._build_base_agent_params(connection_manager, room_manager)
        params["reliability_config"] = reliability_config
        return params
    
    def _build_base_agent_params(self, connection_manager: ConnectionManager,
                               room_manager: RoomManager) -> Dict[str, Any]:
        """Build base agent parameters."""
        return {
            "connection_manager": connection_manager,
            "room_manager": room_manager
        }

    async def broadcast_to_all(self, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> BroadcastResult:
        """Broadcast a message to all connected users with modern reliability."""
        broadcast_ctx = self._create_all_broadcast_context(message)
        execution_result = await self._modern_agent.execute_with_reliability(broadcast_ctx)
        return self._extract_broadcast_result(execution_result)
    
    def _create_all_broadcast_context(self, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> BroadcastContext:
        """Create broadcast context for all connections operation."""
        return BroadcastContext(
            operation=BroadcastOperation.ALL_CONNECTIONS,
            message=message
        )
    
    def _extract_broadcast_result(self, execution_result) -> BroadcastResult:
        """Extract BroadcastResult from modern execution result."""
        if execution_result.success and execution_result.result:
            return execution_result.result.get("broadcast_result")
        return utils.create_empty_room_broadcast_result()

    async def broadcast_to_user(self, user_id: str, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> bool:
        """Broadcast a message to all connections for a specific user with modern reliability."""
        broadcast_ctx = self._create_user_broadcast_context(user_id, message)
        execution_result = await self._modern_agent.execute_with_reliability(broadcast_ctx)
        return self._extract_user_broadcast_success(execution_result)
    
    def _create_user_broadcast_context(self, user_id: str, 
                                      message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> BroadcastContext:
        """Create broadcast context for user connections operation."""
        return BroadcastContext(
            operation=BroadcastOperation.USER_CONNECTIONS,
            message=message,
            user_id=user_id
        )
    
    def _extract_user_broadcast_success(self, execution_result) -> bool:
        """Extract success status from user broadcast execution result."""
        if execution_result.success and execution_result.result:
            successful_sends = execution_result.result.get("successful_sends", 0)
            return successful_sends > 0
        return False

    async def broadcast_to_room(self, room_id: str, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> BroadcastResult:
        """Broadcast a message to all connections in a room with modern reliability."""
        broadcast_ctx = self._create_room_broadcast_context(room_id, message)
        execution_result = await self._modern_agent.execute_with_reliability(broadcast_ctx)
        return self._extract_room_broadcast_result(execution_result)
    
    def _create_room_broadcast_context(self, room_id: str, 
                                      message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> BroadcastContext:
        """Create broadcast context for room connections operation."""
        return BroadcastContext(
            operation=BroadcastOperation.ROOM_CONNECTIONS,
            message=message,
            room_id=room_id
        )
    
    def _extract_room_broadcast_result(self, execution_result) -> BroadcastResult:
        """Extract BroadcastResult from room broadcast execution result."""
        if execution_result.success and execution_result.result:
            return execution_result.result.get("broadcast_result")
        return utils.create_empty_room_broadcast_result()

    # Modern agent delegation methods (maintain exact API compatibility)

    def create_room(self, room_id: str) -> bool:
        """Create a new room via modern agent."""
        return self._modern_agent.create_room(room_id)

    def delete_room(self, room_id: str) -> bool:
        """Delete a room via modern agent."""
        return self._modern_agent.delete_room(room_id)

    def join_room(self, connection_id: str, room_id: str) -> bool:
        """Add a connection to a room via modern agent."""
        return self._modern_agent.join_room(connection_id, room_id)

    def leave_room(self, connection_id: str, room_id: str) -> bool:
        """Remove a connection from a room via modern agent."""
        return self._modern_agent.leave_room(connection_id, room_id)

    def leave_all_rooms(self, connection_id: str):
        """Remove a connection from all rooms via modern agent."""
        self._modern_agent.leave_all_rooms(connection_id)

    def get_room_connections(self, room_id: str):
        """Get connections in a room via modern agent."""
        return self._modern_agent.get_room_connections(room_id)

    def get_connection_rooms(self, connection_id: str):
        """Get rooms for a connection via modern agent."""
        return self._modern_agent.get_connection_rooms(connection_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive broadcast statistics with modern reliability metrics."""
        return self._modern_agent.get_stats()
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status from modern agent."""
        return self._modern_agent.get_health_status()
    
    @property
    def _stats(self) -> Dict[str, int]:
        """Get legacy stats from modern agent for backward compatibility."""
        modern_stats = self._modern_agent.get_stats()
        return {
            "total_broadcasts": modern_stats.get("total_broadcasts", 0),
            "successful_sends": modern_stats.get("successful_sends", 0),
            "failed_sends": modern_stats.get("failed_sends", 0)
        }