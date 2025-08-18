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
        """Handle incoming WebSocket message with rate limiting and validation."""
        return await self.messaging.handle_incoming_message(user_id, websocket, message)

    async def handle_pong(self, user_id: str, websocket: WebSocket) -> None:
        """Handle pong response from client."""
        # Get connection info and pass to heartbeat manager
        conn_info = self._get_connection_info_for_user(user_id, websocket)
        if conn_info:
            await self.core.heartbeat_manager.handle_pong_response(conn_info.connection_id, websocket)

    def _get_connection_info_for_user(self, user_id: str, websocket: WebSocket) -> Optional[ConnectionInfo]:
        """Find connection info for user and websocket."""
        user_connections = self.core.connection_manager.active_connections.get(user_id, [])
        for conn_info in user_connections:
            if conn_info.websocket == websocket:
                return conn_info
        return None

    @property
    def connection_manager(self) -> ConnectionManager:
        """Public access to connection manager for compatibility."""
        return self._connection_manager
    
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
        return self._connection_manager.get_connection_info(user_id)

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

    async def notify_batch_complete(self, job_id: str, batch_num: int, batch_size: int) -> bool:
        """Send batch completion notification to job connections."""
        message = {
            "type": "batch_complete",
            "job_id": job_id,
            "batch_num": batch_num,
            "batch_size": batch_size
        }
        return await self.broadcast_to_job(job_id, message)

    async def notify_error(self, job_id: str, error_data: Dict[str, Any]) -> bool:
        """Send error notification to job connections."""
        return await self.broadcast_to_job(job_id, error_data)

    async def notify_completion(self, job_id: str, completion_data: Dict[str, Any]) -> bool:
        """Send completion notification to job connections."""
        return await self.broadcast_to_job(job_id, completion_data)

    def set_job_state(self, job_id: str, state: Dict[str, Any]) -> None:
        """Store job state."""
        if not hasattr(self.core, 'job_states'):
            self.core.job_states = {}
        self.core.job_states[job_id] = state

    def get_job_state(self, job_id: str) -> Dict[str, Any]:
        """Retrieve job state."""
        return getattr(self.core, 'job_states', {}).get(job_id, {})

    async def start_heartbeat(self, job_id: str, interval_seconds: int = 30) -> None:
        """Start heartbeat for job connections."""
        self._update_heartbeat_config(interval_seconds)
        room_connections = self.core.room_manager.get_room_connections(job_id)
        await self._start_heartbeats_for_room(room_connections)

    def _update_heartbeat_config(self, interval_seconds: int) -> None:
        """Update heartbeat configuration if needed."""
        if interval_seconds != self.core.heartbeat_manager.config.interval_seconds:
            self.core.heartbeat_manager.config.interval_seconds = interval_seconds

    async def _start_heartbeats_for_room(self, room_connections) -> None:
        """Start heartbeats for all connections in room."""
        for user_id in room_connections:
            user_connections = self.core.connection_manager.get_user_connections(user_id)
            for conn_info in user_connections:
                await self.core.heartbeat_manager.start_heartbeat_for_connection(conn_info)

    # Agent compatibility methods (required by BaseAgent)
    async def send_message(self, user_id: str, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]], 
                          retry: bool = True) -> bool:
        """Send message - alias for send_message_to_user (agent compatibility)."""
        return await self.send_message_to_user(user_id, message, retry)
    
    async def send_error(self, user_id: str, error_message: str, sub_agent_name: str = "System") -> bool:
        """Send error - alias for send_error_to_user (agent compatibility)."""
        return await self.send_error_to_user(user_id, error_message, sub_agent_name)
    
    async def send_agent_update(self, user_id: str, sub_agent_name: str, state: Dict[str, Any]) -> None:
        """Send agent update - alias for send_sub_agent_update (agent compatibility)."""
        await self.send_sub_agent_update(user_id, sub_agent_name, state)

    # Legacy method names for backward compatibility
    async def connect(self, websocket: WebSocket, job_id: str) -> ConnectionInfo:
        """Connect to a job - alias for connect_to_job."""
        return await self.connect_to_job(websocket, job_id)

    async def disconnect(self, job_id: str) -> None:
        """Disconnect from a job - alias for disconnect_from_job."""
        await self.disconnect_from_job(job_id)


# Global manager instance with lazy initialization
_manager: Optional[WebSocketManager] = None

def get_manager() -> WebSocketManager:
    """Get WebSocket manager instance with lazy initialization."""
    global _manager
    if _manager is None:
        _manager = WebSocketManager()
    return _manager

# Initialize on first access to maintain compatibility
manager = get_manager()
ws_manager = manager  # Alias for compatibility