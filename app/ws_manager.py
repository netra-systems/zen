"""Refactored WebSocket Manager - Main orchestration layer.

Main WebSocket manager that orchestrates connection, messaging, and core operations
using modular components. Maintains singleton pattern and provides a clean API.
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

# Import new modular components
from app.ws_manager_core import WebSocketManagerCore
from app.ws_manager_connections import WebSocketConnectionManager
from app.ws_manager_messaging import WebSocketMessagingManager
from app.ws_manager_broadcasting import WebSocketBroadcastingManager
# Test compatibility mixin moved to app/tests/helpers/

logger = central_logger.get_logger(__name__)


class WebSocketManager:
    """Enhanced WebSocket manager using modular components."""
    _instance: Optional['WebSocketManager'] = None
    _initialized = False

    def __new__(cls) -> 'WebSocketManager':
        """Singleton pattern delegating to core."""
        if cls._instance is None:
            cls._instance = super(WebSocketManager, cls).__new__(cls)
            cls._instance._initialize_managers()
        return cls._instance

    def _initialize_managers(self) -> None:
        """Initialize all manager components."""
        if self._initialized:
            return
        self.core = WebSocketManagerCore()
        self._connection_manager = WebSocketConnectionManager(self.core)
        self.messaging = WebSocketMessagingManager(self.core)
        self.broadcasting = WebSocketBroadcastingManager(self.core)
        # Connection tracking now handled by core components
        self._initialized = True


    async def connect_user(self, user_id: str, websocket: WebSocket) -> ConnectionInfo:
        """Establish and register a new WebSocket connection for a user."""
        return await self._connection_manager.establish_connection(user_id, websocket)

    async def disconnect_user(self, user_id: str, websocket: WebSocket, 
                       code: int = 1000, reason: str = "Normal closure") -> None:
        """Properly disconnect and clean up a WebSocket connection for a user."""
        await self._connection_manager.terminate_connection(user_id, websocket, code, reason)

    def validate_message(self, message: Dict[str, Any]) -> Union[bool, WebSocketValidationError]:
        """Validate incoming WebSocket message."""
        return self.messaging.validate_incoming_message(message)

    def sanitize_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize message content."""
        return self.messaging.sanitize_message_content(message)

    async def send_message_to_user(self, user_id: str, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]], 
                                  retry: bool = True) -> bool:
        """Send a message to all connections for a user.
        
        Returns:
            bool: True if message was sent to at least one connection.
        """
        return await self.messaging.send_to_user(user_id, message, retry)

    async def send_to_thread(self, thread_id: str, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> bool:
        """Send a message to all users in a specific thread.
        
        Returns:
            bool: True if message was sent successfully
        """
        return await self.broadcasting.send_to_thread(thread_id, message)

    async def broadcast_to_job(self, job_id: str, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> bool:
        """Send a message to all users connected to a specific job.
        
        Args:
            job_id: The job identifier 
            message: Message to send
            
        Returns:
            bool: True if message was sent successfully
        """
        return await self.broadcasting.broadcast_to_job(job_id, message)

    async def connect_to_job(self, websocket: WebSocket, job_id: str) -> ConnectionInfo:
        """Connect a websocket to a specific job/room.
        
        This method supports the job-based connection pattern expected by tests.
        """
        user_id = f"job_{job_id}_{id(websocket)}"
        connection_info = await self.connect_user(user_id, websocket)
        self.core.room_manager.join_room(connection_info.connection_id, job_id)
        return connection_info

    async def disconnect_from_job(self, job_id: str, websocket: WebSocket = None) -> None:
        """Disconnect from a specific job/room."""
        if websocket:
            user_id = f"job_{job_id}_{id(websocket)}"
            await self.disconnect_user(user_id, websocket)
        else:
            # For job disconnection, remove all connections in the room
            room_connections = self.core.room_manager.get_room_connections(job_id)
            for conn_id in room_connections:
                self.core.room_manager.leave_all_rooms(conn_id)

    async def broadcast_to_all_users(self, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> BroadcastResult:
        """Broadcast a message to all connected users."""
        return await self.broadcasting.broadcast_to_all(message)

    async def handle_message(self, user_id: str, websocket: WebSocket, message: Dict[str, Any]) -> bool:
        """Handle incoming WebSocket message with rate limiting and validation."""
        return await self.messaging.handle_incoming_message(user_id, websocket, message)

    async def handle_pong(self, user_id: str, websocket: WebSocket) -> None:
        """Handle pong response from client."""
        await self.connections.handle_pong_response(user_id, websocket)

    # Original convenience methods for existing API
    async def send_error_to_user(self, user_id: str, error_message: str, sub_agent_name: str = "System") -> bool:
        """Send an error message to a specific user."""
        return await self.messaging.send_error_message(user_id, error_message, sub_agent_name)

    async def send_agent_log(self, user_id: str, log_level: Literal["debug", "info", "warning", "error", "critical"], 
                           message: str, sub_agent_name: Optional[str] = None) -> None:
        """Send agent log messages for real-time monitoring."""
        await self.messaging.send_agent_log(user_id, log_level, message, sub_agent_name)

    async def send_tool_call(self, user_id: str, tool_name: str, tool_args: Dict[str, Any], 
                           sub_agent_name: Optional[str] = None) -> None:
        """Send tool call updates."""
        await self.messaging.send_tool_call(user_id, tool_name, tool_args, sub_agent_name)

    async def send_tool_result(self, user_id: str, tool_name: str, result: Union[str, Dict[str, Any], List[Any]], 
                             sub_agent_name: Optional[str] = None) -> None:
        """Send tool result updates."""
        await self.messaging.send_tool_result(user_id, tool_name, result, sub_agent_name)
    
    async def send_sub_agent_update(self, user_id: str, sub_agent_name: str, state: Dict[str, Any]) -> None:
        """Send sub-agent status updates."""
        await self.messaging.send_sub_agent_update(user_id, sub_agent_name, state)

    async def shutdown(self) -> None:
        """Gracefully shutdown all components."""
        await self.core.shutdown_core()

    def get_stats(self) -> WebSocketStats:
        """Get comprehensive WebSocket manager statistics."""
        return self._build_stats_from_components()

    def _build_stats_from_components(self) -> WebSocketStats:
        """Build statistics from all manager components."""
        conn_stats = self.core.connection_manager.get_stats()
        heartbeat_stats = self.core.heartbeat_manager.get_stats()
        broadcast_stats = self.core.broadcast_manager.get_stats()
        error_stats = self.core.error_handler.get_error_stats()
        core_stats = self.core.get_stats_dict()
        return self._create_stats_object(conn_stats, broadcast_stats, error_stats, core_stats)

    def _create_stats_object(self, conn_stats: Dict[str, Any], broadcast_stats: Dict[str, Any], 
                           error_stats: Dict[str, Any], core_stats: Dict[str, int]) -> WebSocketStats:
        """Create WebSocketStats object from component statistics."""
        rate_limit_info = self._create_rate_limit_info()
        return self._build_websocket_stats(conn_stats, broadcast_stats, error_stats, core_stats, rate_limit_info)

    def _create_rate_limit_info(self) -> RateLimitInfo:
        """Create rate limit info from core settings."""
        from datetime import datetime, timezone
        return RateLimitInfo(
            max_requests=self.core.rate_limiter.max_requests,
            window_seconds=self.core.rate_limiter.window_seconds,
            current_count=0, window_start=datetime.now(timezone.utc), is_limited=False
        )

    def _build_websocket_stats(self, conn_stats: Dict[str, Any], broadcast_stats: Dict[str, Any],
                             error_stats: Dict[str, Any], core_stats: Dict[str, int], 
                             rate_limit_info: RateLimitInfo) -> WebSocketStats:
        """Build final WebSocketStats object."""
        stats_params = self._prepare_stats_parameters(conn_stats, broadcast_stats, error_stats, core_stats)
        return WebSocketStats(**stats_params, rate_limit_settings=rate_limit_info)

    def _prepare_stats_parameters(self, conn_stats: Dict[str, Any], broadcast_stats: Dict[str, Any],
                                error_stats: Dict[str, Any], core_stats: Dict[str, int]) -> Dict[str, Any]:
        """Prepare parameters for WebSocketStats construction."""
        base_params = self._get_base_stats_params(conn_stats, core_stats)
        message_params = self._get_message_stats_params(broadcast_stats, error_stats, core_stats)
        return {**base_params, **message_params, "connections_by_user": conn_stats["connections_by_user"]}

    def _get_base_stats_params(self, conn_stats: Dict[str, Any], core_stats: Dict[str, int]) -> Dict[str, Any]:
        """Get base connection statistics parameters."""
        connection_params = {k: conn_stats[k] for k in ["total_connections", "active_connections", "active_users", "connection_failures"]}
        return {**connection_params, "rate_limited_requests": core_stats["rate_limited_requests"]}

    def _get_message_stats_params(self, broadcast_stats: Dict[str, Any], 
                                error_stats: Dict[str, Any], core_stats: Dict[str, int]) -> Dict[str, Any]:
        """Get message and error statistics parameters."""
        return {
            "total_messages_sent": core_stats["total_messages_sent"] + broadcast_stats["successful_sends"],
            "total_messages_received": core_stats["total_messages_received"],
            "total_errors": core_stats["total_errors"] + error_stats["total_errors"]
        }

    def get_connection_info(self, user_id: str) -> List[Dict[str, Any]]:
        """Get detailed information about a user's connections."""
        return self.connections.get_user_connection_info(user_id)

    @property
    def active_connections(self) -> Dict[str, Any]:
        """Get active connections for job-based operations."""
        room_stats = self.core.room_manager.get_stats()
        room_connections = room_stats.get("room_connections", {})
        # Filter out rooms with 0 connections (job disconnected)
        return {job_id: count for job_id, count in room_connections.items() if count > 0}

    def get_queue_size(self, job_id: str) -> int:
        """Get message queue size for a job."""
        return getattr(self.core.queue_manager, 'get_queue_size', lambda x: 0)(job_id)

    # Legacy method names for backward compatibility
    async def connect(self, websocket: WebSocket, job_id: str) -> ConnectionInfo:
        """Connect to a job - alias for connect_to_job."""
        return await self.connect_to_job(websocket, job_id)

    async def disconnect(self, job_id: str) -> None:
        """Disconnect from a job - alias for disconnect_from_job."""
        await self.disconnect_from_job(job_id)


# Global manager instance
manager = WebSocketManager()
ws_manager = manager  # Alias for compatibility