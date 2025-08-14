"""Refactored WebSocket Manager using modular components.

Main WebSocket manager that orchestrates the various WebSocket components:
connection management, heartbeat monitoring, message validation, broadcasting,
rate limiting, and error handling.
"""

import time
import asyncio
import threading
from typing import Dict, Any, Union, List, Optional, Literal

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from app.logging_config import central_logger
from app.schemas.websocket_unified import (
    WebSocketMessage,
    WebSocketMessageType
)
from app.schemas.websocket_message_types import (
    WebSocketValidationError,
    ServerMessage,
    WebSocketStats,
    RateLimitInfo,
    BroadcastResult
)
from app.schemas.websocket_types import WebSocketMessageOut

# Import refactored modules
from app.websocket.connection import ConnectionInfo, ConnectionManager
from app.websocket.rate_limiter import RateLimiter
from app.websocket.validation import MessageValidator
from app.websocket.broadcast import BroadcastManager
from app.websocket.heartbeat import HeartbeatManager
from app.websocket.error_handler import ErrorHandler

logger = central_logger.get_logger(__name__)


class WebSocketManager:
    """Enhanced WebSocket manager using modular components."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(WebSocketManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if not self._initialized:
            # Initialize component managers
            self.connection_manager = ConnectionManager()
            self.rate_limiter = RateLimiter(max_requests=60, window_seconds=60)
            self.message_validator = MessageValidator()
            self.error_handler = ErrorHandler()
            self.broadcast_manager = BroadcastManager(self.connection_manager)
            self.heartbeat_manager = HeartbeatManager(self.connection_manager, self.error_handler)
            
            # Configuration constants
            self.MAX_RETRY_ATTEMPTS = 3
            self.RETRY_DELAY = 1  # seconds
            
            self._stats = {
                "total_messages_sent": 0,
                "total_messages_received": 0,
                "total_errors": 0,
                "rate_limited_requests": 0
            }
            self._initialized = True

    async def connect(self, user_id: str, websocket: WebSocket) -> ConnectionInfo:
        """Establish and register a new WebSocket connection."""
        conn_info = await self.connection_manager.connect(user_id, websocket)
        
        # Start heartbeat monitoring
        await self.heartbeat_manager.start_heartbeat_for_connection(conn_info)
        
        # Send initial connection success message
        await self._send_system_message(conn_info, {
            "type": "connection_established",
            "connection_id": conn_info.connection_id,
            "timestamp": time.time()
        })
        
        return conn_info

    async def disconnect(self, user_id: str, websocket: WebSocket, code: int = 1000, reason: str = "Normal closure") -> None:
        """Properly disconnect and clean up a WebSocket connection."""
        # Find connection info
        conn_info = await self.connection_manager.find_connection(user_id, websocket)
        if conn_info:
            # Stop heartbeat monitoring
            await self.heartbeat_manager.stop_heartbeat_for_connection(conn_info.connection_id)
            
            # Remove from broadcast rooms
            self.broadcast_manager.leave_all_rooms(conn_info.connection_id)
        
        # Disconnect the connection
        await self.connection_manager.disconnect(user_id, websocket, code, reason)

    def validate_message(self, message: Dict[str, Any]) -> Union[bool, WebSocketValidationError]:
        """Validate incoming WebSocket message."""
        return self.message_validator.validate_message(message)

    def sanitize_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize message content."""
        return self.message_validator.sanitize_message(message)

    async def send_message(self, user_id: str, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]], retry: bool = True) -> bool:
        """Send a message to all connections for a user.
        
        Returns:
            bool: True if message was sent to at least one connection.
        """
        # Validate and sanitize message
        if isinstance(message, dict):
            validation_result = self.validate_message(message)
            if isinstance(validation_result, WebSocketValidationError):
                logger.error(f"Message validation failed for user {user_id}: {validation_result.message}")
                return False
            message = self.sanitize_message(message)

        # Add timestamp if not present
        if isinstance(message, dict) and "timestamp" not in message:
            message["timestamp"] = time.time()

        success = await self.broadcast_manager.broadcast_to_user(user_id, message)
        if success:
            self._stats["total_messages_sent"] += 1

        return success

    async def send_to_thread(self, thread_id: str, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> bool:
        """Send a message to all users in a specific thread.
        
        Args:
            thread_id: The thread/conversation ID
            message: The message to send
            
        Returns:
            bool: True if message was sent successfully
        """
        # For now, thread_id maps to user_id for WebSocket routing
        # This can be enhanced to support multiple users per thread
        return await self.send_message(thread_id, message)

    async def broadcast(self, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> BroadcastResult:
        """Broadcast a message to all connected users."""
        # Validate and sanitize message if it's a dict
        if isinstance(message, dict):
            validation_result = self.validate_message(message)
            if isinstance(validation_result, WebSocketValidationError):
                logger.error(f"Broadcast message validation failed: {validation_result.message}")
                return BroadcastResult(successful=0, failed=0, total_connections=0, message_type="invalid")
            message = self.sanitize_message(message)

        result = await self.broadcast_manager.broadcast_to_all(message)
        self._stats["total_messages_sent"] += result.successful
        return result

    async def handle_message(self, user_id: str, websocket: WebSocket, message: Dict[str, Any]) -> bool:
        """Handle incoming WebSocket message with rate limiting and validation."""
        # Find connection info
        conn_info = await self.connection_manager.find_connection(user_id, websocket)
        if not conn_info:
            logger.warning(f"Connection not found for user {user_id}")
            return False

        # Check rate limiting
        if self.rate_limiter.is_rate_limited(conn_info):
            self._stats["rate_limited_requests"] += 1
            await self.error_handler.handle_rate_limit_error(
                conn_info, 
                self.rate_limiter.get_rate_limit_info(conn_info)
            )
            await self._send_rate_limit_error(conn_info)
            return False

        # Validate message
        validation_result = self.validate_message(message)
        if isinstance(validation_result, WebSocketValidationError):
            await self.error_handler.handle_validation_error(user_id, validation_result.message, message)
            await self._send_system_message(conn_info, {
                "type": "error",
                "payload": {
                    "error": "Invalid message format",
                    "code": "INVALID_MESSAGE"
                },
                "timestamp": time.time()
            })
            return False

        # Update statistics
        self._stats["total_messages_received"] += 1
        return True

    async def handle_pong(self, user_id: str, websocket: WebSocket) -> None:
        """Handle pong response from client."""
        conn_info = await self.connection_manager.find_connection(user_id, websocket)
        if conn_info:
            await self.heartbeat_manager.handle_pong(conn_info)

    async def _send_system_message(self, conn_info: ConnectionInfo, message: Dict[str, Any]) -> None:
        """Send a system message to a specific connection."""
        message["system"] = True
        await self._send_to_connection(conn_info, message, retry=False)

    async def _send_to_connection(self, conn_info: ConnectionInfo, message: Union[Dict[str, Any], Any], retry: bool = True) -> bool:
        """Send a message to a specific connection with retry logic."""
        attempts = self.MAX_RETRY_ATTEMPTS if retry else 1
        
        for attempt in range(attempts):
            try:
                if conn_info.websocket.client_state == WebSocketState.CONNECTED:
                    await conn_info.websocket.send_json(message)
                    return True
                else:
                    logger.debug(f"Connection {conn_info.connection_id} not in CONNECTED state")
                    return False
                    
            except (RuntimeError, ConnectionError) as e:
                if "Cannot call" in str(e) or "close" in str(e).lower():
                    logger.debug(f"Connection {conn_info.connection_id} closed: {e}")
                    return False
                    
                conn_info.error_count += 1
                self._stats["total_errors"] += 1
                
                if attempt < attempts - 1:
                    await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                    logger.warning(f"Retrying send to {conn_info.connection_id} (attempt {attempt + 2}/{attempts})")
                else:
                    logger.error(f"Failed to send message to {conn_info.connection_id} after {attempts} attempts: {e}")
                    return False
                    
            except Exception as e:
                conn_info.error_count += 1
                self._stats["total_errors"] += 1
                logger.error(f"Unexpected error sending to {conn_info.connection_id}: {e}", exc_info=True)
                return False
        
        return False

    async def _send_rate_limit_error(self, conn_info: ConnectionInfo) -> None:
        """Send rate limit error to connection."""
        await self._send_system_message(conn_info, {
            "type": "error",
            "payload": {
                "error": "Rate limit exceeded",
                "code": "RATE_LIMIT_EXCEEDED",
                "details": self.rate_limiter.get_rate_limit_info(conn_info)
            },
            "timestamp": time.time()
        })

    # Convenience methods for sending specific message types
    async def send_error(self, user_id: str, error_message: str, sub_agent_name: str = "System") -> bool:
        """Send an error message to a specific user."""
        return await self.send_message(user_id, {
            "type": "error",
            "payload": {"error": error_message, "sub_agent_name": sub_agent_name},
            "displayed_to_user": True
        })

    async def send_agent_log(self, user_id: str, log_level: Literal["debug", "info", "warning", "error", "critical"], message: str, sub_agent_name: Optional[str] = None) -> None:
        """Send agent log messages for real-time monitoring."""
        await self.send_message(user_id, {
            "type": "agent_log",
            "payload": {"level": log_level, "message": message, "sub_agent_name": sub_agent_name, "timestamp": time.time()},
            "displayed_to_user": True
        })

    async def send_tool_call(self, user_id: str, tool_name: str, tool_args: Dict[str, Any], sub_agent_name: Optional[str] = None) -> None:
        """Send tool call updates."""
        await self.send_message(user_id, {
            "type": "tool_call",
            "payload": {"tool_name": tool_name, "tool_args": tool_args, "sub_agent_name": sub_agent_name, "timestamp": time.time()},
            "displayed_to_user": True
        })

    async def send_tool_result(self, user_id: str, tool_name: str, result: Union[str, Dict[str, Any], List[Any]], sub_agent_name: str = None) -> None:
        """Send tool result updates."""
        await self.send_message(user_id, {
            "type": "tool_result",
            "payload": {"tool_name": tool_name, "result": result, "sub_agent_name": sub_agent_name, "timestamp": time.time()},
            "displayed_to_user": True
        })
    
    async def send_sub_agent_update(self, user_id: str, sub_agent_name: str, state: Dict[str, Any]) -> None:
        """Send sub-agent status updates."""
        await self.send_message(user_id, {
            "type": "sub_agent_update",
            "payload": {"sub_agent_name": sub_agent_name, "state": state, "timestamp": time.time()},
            "displayed_to_user": True
        })

    async def shutdown(self) -> None:
        """Gracefully shutdown all components."""
        logger.info("Starting WebSocket manager shutdown...")
        
        # Shutdown heartbeat monitoring
        await self.heartbeat_manager.shutdown_all_heartbeats()
        
        # Shutdown connection manager
        await self.connection_manager.shutdown()
        
        logger.info(f"WebSocket manager shutdown complete. Final stats: {self.get_stats()}")

    def get_stats(self) -> WebSocketStats:
        """Get comprehensive WebSocket manager statistics."""
        conn_stats = self.connection_manager.get_stats()
        heartbeat_stats = self.heartbeat_manager.get_stats()
        broadcast_stats = self.broadcast_manager.get_stats()
        error_stats = self.error_handler.get_error_stats()
        
        from datetime import datetime, timezone
        rate_limit_info = RateLimitInfo(
            max_requests=self.rate_limiter.max_requests,
            window_seconds=self.rate_limiter.window_seconds,
            current_count=0,
            window_start=datetime.now(timezone.utc),
            is_limited=False
        )
        
        return WebSocketStats(
            total_connections=conn_stats["total_connections"],
            active_connections=conn_stats["active_connections"],
            active_users=conn_stats["active_users"],
            total_messages_sent=self._stats["total_messages_sent"] + broadcast_stats["successful_sends"],
            total_messages_received=self._stats["total_messages_received"],
            total_errors=self._stats["total_errors"] + error_stats["total_errors"],
            connection_failures=conn_stats["connection_failures"],
            rate_limited_requests=self._stats["rate_limited_requests"],
            rate_limit_settings=rate_limit_info,
            connections_by_user=conn_stats["connections_by_user"]
        )

    def get_connection_info(self, user_id: str) -> List[Dict[str, Any]]:
        """Get detailed information about a user's connections."""
        return self.connection_manager.get_connection_info(user_id)


# Global manager instance
manager = WebSocketManager()
ws_manager = manager  # Alias for compatibility