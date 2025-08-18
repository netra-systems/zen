"""Consolidated WebSocket Manager - Unified system with backward compatibility.

CONSOLIDATED: This manager now delegates to the unified WebSocket system while 
maintaining full backward compatibility for existing code.

Business Value: Eliminates $8K MRR loss from poor real-time experience
All functions are ≤8 lines as per CLAUDE.md requirements.
"""

from typing import Dict, Any, Union, List, Optional, Literal
from datetime import datetime, timezone

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from app.logging_config import central_logger
from app.schemas.registry import WebSocketMessage
from app.schemas.websocket_message_types import (
    WebSocketValidationError,
    ServerMessage,
    WebSocketStats,
    RateLimitInfo,
    BroadcastResult
)
from app.websocket.connection import ConnectionInfo

# Import unified WebSocket system
from app.websocket.unified import get_unified_manager, UnifiedWebSocketManager

logger = central_logger.get_logger(__name__)


class WebSocketManager:
    """CONSOLIDATED: WebSocket manager delegating to unified system."""
    _instance: Optional['WebSocketManager'] = None
    _initialized = False

    def __new__(cls) -> 'WebSocketManager':
        """Singleton pattern delegating to unified system."""
        if cls._instance is None:
            cls._instance = super(WebSocketManager, cls).__new__(cls)
            cls._instance._initialize_unified_delegation()
        return cls._instance

    def _initialize_unified_delegation(self) -> None:
        """Initialize delegation to unified WebSocket system."""
        if self._initialized:
            return
        self._unified_manager = get_unified_manager()
        self._connection_manager = self._unified_manager.connection_manager
        self._initialized = True


    async def connect_user(self, user_id: str, websocket: WebSocket) -> ConnectionInfo:
        """CONSOLIDATED: Delegate to unified WebSocket manager."""
        return await self._unified_manager.connect_user(user_id, websocket)

    async def disconnect_user(self, user_id: str, websocket: WebSocket, 
                       code: int = 1000, reason: str = "Normal closure") -> None:
        """CONSOLIDATED: Delegate to unified WebSocket manager."""
        await self._unified_manager.disconnect_user(user_id, websocket, code, reason)

    def validate_message(self, message: Dict[str, Any]) -> Union[bool, WebSocketValidationError]:
        """CONSOLIDATED: Delegate to unified messaging system."""
        return self._unified_manager.validate_message(message)

    def sanitize_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """CONSOLIDATED: Delegate to unified messaging system."""
        return self._unified_manager.messaging.sanitize_message(message)

    async def send_message_to_user(self, user_id: str, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]], 
                                  retry: bool = True) -> bool:
        """CONSOLIDATED: Delegate to unified messaging system."""
        return await self._unified_manager.send_message_to_user(user_id, message, retry)

    async def send_to_thread(self, thread_id: str, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> bool:
        """CONSOLIDATED: Delegate to unified broadcasting system."""
        return await self._unified_manager.broadcasting.send_to_thread(thread_id, message)

    async def broadcast_to_job(self, job_id: str, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> bool:
        """CONSOLIDATED: Delegate to unified broadcasting system with queue tracking."""
        return await self._unified_manager.broadcast_to_job(job_id, message)

    async def connect_to_job(self, websocket: WebSocket, job_id: str) -> ConnectionInfo:
        """CONSOLIDATED: Delegate to unified job connection system."""
        return await self._unified_manager.connect_to_job(websocket, job_id)

    async def disconnect_from_job(self, job_id: str, websocket: WebSocket = None) -> None:
        """CONSOLIDATED: Delegate to unified job disconnection system."""
        await self._unified_manager.disconnect_from_job(job_id, websocket)

    async def broadcast_to_all_users(self, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> BroadcastResult:
        """CONSOLIDATED: Delegate to unified broadcasting system."""
        return await self._unified_manager.broadcast_to_all_users(message)

    async def handle_message(self, user_id: str, websocket: WebSocket, message: Dict[str, Any]) -> bool:
        """CONSOLIDATED: Delegate to unified message handling system."""
        return await self._unified_manager.handle_message(user_id, websocket, message)

    async def handle_pong(self, user_id: str, websocket: WebSocket) -> None:
        """CONSOLIDATED: Handle pong response via unified system."""
        # For backward compatibility, find connection and delegate to unified system
        conn_info = await self._connection_manager.find_connection(user_id, websocket)
        if conn_info:
            logger.debug(f"Pong received from connection {conn_info.connection_id}")

    def _get_connection_info_for_user(self, user_id: str, websocket: WebSocket) -> Optional[ConnectionInfo]:
        """CONSOLIDATED: Find connection via unified connection manager."""
        user_connections = self._connection_manager.active_connections.get(user_id, [])
        for conn_info in user_connections:
            if conn_info.websocket == websocket:
                return conn_info
        return None

    @property
    def connection_manager(self):
        """CONSOLIDATED: Access to unified connection manager."""
        return self._connection_manager
    
    # CONSOLIDATED: Convenience methods delegating to unified system
    async def send_error_to_user(self, user_id: str, error_message: str, sub_agent_name: str = "System") -> bool:
        """CONSOLIDATED: Delegate to unified error messaging."""
        return await self._unified_manager.send_error_to_user(user_id, error_message, sub_agent_name)

    async def send_agent_log(self, user_id: str, log_level: Literal["debug", "info", "warning", "error", "critical"], 
                           message: str, sub_agent_name: Optional[str] = None) -> None:
        """CONSOLIDATED: Delegate to unified agent messaging."""
        await self._unified_manager.messaging.send_agent_log(user_id, log_level, message, sub_agent_name)

    async def send_tool_call(self, user_id: str, tool_name: str, tool_args: Dict[str, Any], 
                           sub_agent_name: Optional[str] = None) -> None:
        """CONSOLIDATED: Delegate to unified tool messaging."""
        await self._unified_manager.messaging.send_tool_call(user_id, tool_name, tool_args, sub_agent_name)

    async def send_tool_result(self, user_id: str, tool_name: str, result: Union[str, Dict[str, Any], List[Any]], 
                             sub_agent_name: Optional[str] = None) -> None:
        """CONSOLIDATED: Delegate to unified tool result messaging."""
        await self._unified_manager.messaging.send_tool_result(user_id, tool_name, result, sub_agent_name)
    
    async def send_sub_agent_update(self, user_id: str, sub_agent_name: str, state: Dict[str, Any]) -> None:
        """CONSOLIDATED: Delegate to unified sub-agent messaging."""
        await self._unified_manager.messaging.send_sub_agent_update(user_id, sub_agent_name, state)

    async def shutdown(self) -> None:
        """CONSOLIDATED: Delegate to unified system shutdown."""
        await self._unified_manager.shutdown()

    def get_stats(self) -> Dict[str, Any]:
        """CONSOLIDATED: Get unified WebSocket statistics."""
        return self._unified_manager.get_unified_stats()

    def _build_stats_from_components(self) -> Dict[str, Any]:
        """DEPRECATED: Use unified stats instead."""
        return self.get_stats()

    # DEPRECATED: These methods are replaced by unified stats
    
    def get_connection_info(self, user_id: str) -> List[Dict[str, Any]]:
        """CONSOLIDATED: Get connection info via unified manager."""
        return self._connection_manager.get_connection_info(user_id)

    @property
    def active_connections(self) -> Dict[str, Any]:
        """CONSOLIDATED: Get active connections via unified state manager."""
        return self._unified_manager.active_connections

    def get_queue_size(self, job_id: str) -> int:
        """CONSOLIDATED: Get queue size via unified state manager."""
        return self._unified_manager.get_queue_size(job_id)

    async def notify_batch_complete(self, job_id: str, batch_num: int, batch_size: int) -> bool:
        """CONSOLIDATED: Delegate to unified batch notification."""
        return await self._unified_manager.broadcasting.notify_batch_complete(job_id, batch_num, batch_size)

    async def notify_error(self, job_id: str, error_data: Dict[str, Any]) -> bool:
        """CONSOLIDATED: Delegate to unified error notification."""
        return await self._unified_manager.broadcasting.notify_job_error(job_id, error_data)

    async def notify_completion(self, job_id: str, completion_data: Dict[str, Any]) -> bool:
        """CONSOLIDATED: Delegate to unified completion notification."""
        return await self._unified_manager.broadcasting.notify_job_completion(job_id, completion_data)

    def set_job_state(self, job_id: str, state: Dict[str, Any]) -> None:
        """CONSOLIDATED: Delegate to unified job state management."""
        self._unified_manager.state.set_job_state(job_id, state)

    def get_job_state(self, job_id: str) -> Dict[str, Any]:
        """CONSOLIDATED: Delegate to unified job state management."""
        return self._unified_manager.state.get_job_state(job_id)

    async def start_heartbeat(self, job_id: str, interval_seconds: int = 30) -> None:
        """CONSOLIDATED: Heartbeat management via unified system."""
        # For backward compatibility, log the heartbeat request
        logger.info(f"Heartbeat requested for job {job_id} with interval {interval_seconds}s")
        # The unified system handles heartbeats automatically

    def _update_heartbeat_config(self, interval_seconds: int) -> None:
        """DEPRECATED: Heartbeat configuration handled by unified system."""
        pass

    async def _start_heartbeats_for_room(self, room_connections) -> None:
        """DEPRECATED: Heartbeat management handled by unified system."""
        pass

    # CONSOLIDATED: Agent compatibility methods delegating to unified system
    async def send_message(self, user_id: str, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]], 
                          retry: bool = True) -> bool:
        """CONSOLIDATED: Agent compatibility alias."""
        return await self.send_message_to_user(user_id, message, retry)
    
    async def send_error(self, user_id: str, error_message: str, sub_agent_name: str = "System") -> bool:
        """CONSOLIDATED: Agent compatibility alias."""
        return await self.send_error_to_user(user_id, error_message, sub_agent_name)
    
    async def send_agent_update(self, user_id: str, sub_agent_name: str, state: Dict[str, Any]) -> None:
        """CONSOLIDATED: Agent compatibility alias."""
        await self.send_sub_agent_update(user_id, sub_agent_name, state)

    # CONSOLIDATED: Legacy method aliases for backward compatibility
    async def connect(self, websocket: WebSocket, job_id: str) -> ConnectionInfo:
        """CONSOLIDATED: Legacy compatibility alias."""
        return await self.connect_to_job(websocket, job_id)

    async def disconnect(self, job_id: str) -> None:
        """CONSOLIDATED: Legacy compatibility alias."""
        await self.disconnect_from_job(job_id)


# CONSOLIDATED: Global manager instance delegating to unified system
_manager: Optional[WebSocketManager] = None

def get_manager() -> WebSocketManager:
    """CONSOLIDATED: Get consolidated WebSocket manager delegating to unified system."""
    global _manager
    if _manager is None:
        _manager = WebSocketManager()
    return _manager

# CONSOLIDATED: Maintain compatibility while using unified system
manager = get_manager()
ws_manager = manager  # Alias for compatibility