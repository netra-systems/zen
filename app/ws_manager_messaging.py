"""WebSocket Manager Messaging - Message processing and sending operations.

This module handles WebSocket message validation, sanitization, sending, and broadcasting
with proper error handling and rate limiting.
All functions are ≤8 lines as per CLAUDE.md requirements.
"""

import time
import asyncio
from typing import Dict, Any, Union, Optional, List, Literal

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from app.logging_config import central_logger
from app.schemas.websocket_unified import WebSocketMessage
from app.schemas.websocket_message_types import (
    ServerMessage, WebSocketValidationError, BroadcastResult
)
from app.websocket.connection import ConnectionInfo
from app.ws_manager_core import WebSocketManagerCore

logger = central_logger.get_logger(__name__)


class WebSocketMessagingManager:
    """Manages WebSocket message processing and sending operations."""

    def __init__(self, core: WebSocketManagerCore) -> None:
        """Initialize with core manager reference."""
        self.core = core

    def validate_incoming_message(self, message: Dict[str, Any]) -> Union[bool, WebSocketValidationError]:
        """Validate incoming WebSocket message format."""
        return self.core.message_validator.validate_message(message)

    def sanitize_message_content(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize message content for security."""
        return self.core.message_validator.sanitize_message(message)

    async def send_to_user(self, user_id: str, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]], 
                          retry: bool = True) -> bool:
        """Send message to all connections for a user."""
        validated_message = self._prepare_message(message)
        if validated_message is None:
            return False
        return await self._send_validated_message(user_id, validated_message)

    async def _send_validated_message(self, user_id: str, message: Dict[str, Any]) -> bool:
        """Send validated message and update statistics."""
        success = await self.core.broadcast_manager.broadcast_to_user(user_id, message)
        if success:
            self.core.increment_stat("total_messages_sent")
        return success

    def _prepare_message(self, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Prepare and validate message for sending."""
        if isinstance(message, dict):
            validated_message = self._validate_dict_message(message)
            if validated_message is None:
                return None
            message = validated_message
        return self._add_timestamp(message)

    def _validate_dict_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate and sanitize dict message."""
        validation_result = self.validate_incoming_message(message)
        if isinstance(validation_result, WebSocketValidationError):
            logger.error(f"Message validation failed: {validation_result.message}")
            return None
        return self.sanitize_message_content(message)

    def _add_timestamp(self, message: Union[Dict[str, Any], Any]) -> Dict[str, Any]:
        """Add timestamp to message if not present."""
        if isinstance(message, dict) and "timestamp" not in message:
            message["timestamp"] = time.time()
        return message

    async def send_to_thread(self, thread_id: str, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> bool:
        """Send message to all users in a specific thread."""
        return await self.send_to_user(thread_id, message)

    async def broadcast_to_all(self, message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> BroadcastResult:
        """Broadcast message to all connected users."""
        validated_message = self._prepare_message(message)
        if validated_message is None:
            return BroadcastResult(successful=0, failed=0, total_connections=0, message_type="invalid")
        result = await self.core.broadcast_manager.broadcast_to_all(validated_message)
        self.core.increment_stat("total_messages_sent", result.successful)
        return result

    async def handle_incoming_message(self, user_id: str, websocket: WebSocket, 
                                    message: Dict[str, Any]) -> bool:
        """Handle incoming WebSocket message with rate limiting and validation."""
        conn_info = await self.core.connection_manager.find_connection(user_id, websocket)
        if not conn_info:
            logger.warning(f"Connection not found for user {user_id}")
            return False
        return await self._process_message_with_limits(conn_info, message)

    async def _process_message_with_limits(self, conn_info: ConnectionInfo, message: Dict[str, Any]) -> bool:
        """Process message with rate limiting checks."""
        if self.core.rate_limiter.is_rate_limited(conn_info):
            await self._handle_rate_limit(conn_info)
            return False
        return await self._validate_and_process(conn_info, message)

    async def _handle_rate_limit(self, conn_info: ConnectionInfo) -> None:
        """Handle rate limit exceeded scenario."""
        self.core.increment_stat("rate_limited_requests")
        rate_info = self.core.rate_limiter.get_rate_limit_info(conn_info)
        await self.core.error_handler.handle_rate_limit_error(conn_info, rate_info)
        await self._send_rate_limit_error(conn_info)

    async def _validate_and_process(self, conn_info: ConnectionInfo, message: Dict[str, Any]) -> bool:
        """Validate message and process if valid."""
        validation_result = self.validate_incoming_message(message)
        if isinstance(validation_result, WebSocketValidationError):
            await self._handle_validation_error(conn_info, validation_result, message)
            return False
        self.core.increment_stat("total_messages_received")
        return True

    async def _handle_validation_error(self, conn_info: ConnectionInfo, 
                                     error: WebSocketValidationError, message: Dict[str, Any]) -> None:
        """Handle message validation errors."""
        await self.core.error_handler.handle_validation_error(conn_info.user_id, error.message, message)
        error_msg = self._create_validation_error_message()
        await self._send_system_message(conn_info, error_msg)

    def _create_validation_error_message(self) -> Dict[str, Any]:
        """Create validation error message."""
        return {
            "type": "error",
            "payload": {"error": "Invalid message format", "code": "INVALID_MESSAGE"},
            "timestamp": time.time()
        }

    async def send_to_connection(self, conn_info: ConnectionInfo, 
                               message: Union[Dict[str, Any], Any], retry: bool = True) -> bool:
        """Send message to specific connection with retry logic."""
        attempts = self.core.MAX_RETRY_ATTEMPTS if retry else 1
        for attempt in range(attempts):
            if await self._attempt_send(conn_info, message, attempt, attempts):
                return True
        return False

    async def _attempt_send(self, conn_info: ConnectionInfo, message: Union[Dict[str, Any], Any], 
                          attempt: int, total_attempts: int) -> bool:
        """Attempt to send message to connection."""
        try:
            return await self._send_if_connected(conn_info, message)
        except Exception as e:
            return await self._handle_send_error(conn_info, e, attempt, total_attempts)

    async def _send_if_connected(self, conn_info: ConnectionInfo, message: Union[Dict[str, Any], Any]) -> bool:
        """Send message if connection is active."""
        if conn_info.websocket.client_state == WebSocketState.CONNECTED:
            await conn_info.websocket.send_json(message)
            return True
        return False

    async def _handle_send_error(self, conn_info: ConnectionInfo, error: Exception, 
                               attempt: int, total_attempts: int) -> bool:
        """Handle send errors with retry logic."""
        if self._is_connection_closed_error(error):
            logger.debug(f"Connection {conn_info.connection_id} closed: {error}")
            return False
        return await self._handle_retryable_error(conn_info, attempt, total_attempts, error)

    def _is_connection_closed_error(self, error: Exception) -> bool:
        """Check if error indicates closed connection."""
        return "Cannot call" in str(error) or "close" in str(error).lower()

    async def _handle_retryable_error(self, conn_info: ConnectionInfo, attempt: int, 
                                    total_attempts: int, error: Exception) -> bool:
        """Handle retryable send errors."""
        self._increment_error_counters(conn_info)
        return await self._handle_retry_or_fail(attempt, total_attempts, error)

    async def _handle_retry_or_fail(self, attempt: int, total_attempts: int, error: Exception) -> bool:
        """Handle retry logic or final failure."""
        if attempt < total_attempts - 1:
            await asyncio.sleep(self.core.RETRY_DELAY * (attempt + 1))
            return False
        logger.error(f"Send failed after {total_attempts} attempts: {error}")
        return False

    def _increment_error_counters(self, conn_info: ConnectionInfo) -> None:
        """Increment error counters for connection and core stats."""
        conn_info.error_count += 1
        self.core.increment_stat("total_errors")

    async def _send_system_message(self, conn_info: ConnectionInfo, message: Dict[str, Any]) -> None:
        """Send system message to connection."""
        message["system"] = True
        await self.send_to_connection(conn_info, message, retry=False)

    async def _send_rate_limit_error(self, conn_info: ConnectionInfo) -> None:
        """Send rate limit error message to connection."""
        error_msg = self._create_rate_limit_error_message(conn_info)
        await self._send_system_message(conn_info, error_msg)

    def _create_rate_limit_error_message(self, conn_info: ConnectionInfo) -> Dict[str, Any]:
        """Create rate limit error message."""
        payload = self._create_rate_limit_payload(conn_info)
        return {"type": "error", "payload": payload, "timestamp": time.time()}

    def _create_rate_limit_payload(self, conn_info: ConnectionInfo) -> Dict[str, Any]:
        """Create rate limit error payload."""
        return {
            "error": "Rate limit exceeded",
            "code": "RATE_LIMIT_EXCEEDED",
            "details": self.core.rate_limiter.get_rate_limit_info(conn_info)
        }

    async def send_error_message(self, user_id: str, error_message: str, sub_agent_name: str = "System") -> bool:
        """Send error message to specific user."""
        error_msg = {
            "type": "error",
            "payload": {"error": error_message, "sub_agent_name": sub_agent_name},
            "displayed_to_user": True
        }
        return await self.send_to_user(user_id, error_msg)

    async def send_agent_log(self, user_id: str, log_level: Literal["debug", "info", "warning", "error", "critical"], 
                           message: str, sub_agent_name: Optional[str] = None) -> None:
        """Send agent log message for real-time monitoring."""
        log_msg = self._create_agent_log_message(log_level, message, sub_agent_name)
        await self.send_to_user(user_id, log_msg)

    def _create_agent_log_message(self, log_level: str, message: str, sub_agent_name: Optional[str]) -> Dict[str, Any]:
        """Create agent log message payload."""
        payload = {"level": log_level, "message": message, "sub_agent_name": sub_agent_name, "timestamp": time.time()}
        return {"type": "agent_log", "payload": payload, "displayed_to_user": True}

    async def send_tool_call(self, user_id: str, tool_name: str, tool_args: Dict[str, Any], 
                           sub_agent_name: Optional[str] = None) -> None:
        """Send tool call update message."""
        tool_msg = self._create_tool_call_message(tool_name, tool_args, sub_agent_name)
        await self.send_to_user(user_id, tool_msg)

    def _create_tool_call_message(self, tool_name: str, tool_args: Dict[str, Any], 
                                sub_agent_name: Optional[str]) -> Dict[str, Any]:
        """Create tool call message payload."""
        payload = {"tool_name": tool_name, "tool_args": tool_args, "sub_agent_name": sub_agent_name, "timestamp": time.time()}
        return {"type": "tool_call", "payload": payload, "displayed_to_user": True}

    async def send_tool_result(self, user_id: str, tool_name: str, 
                             result: Union[str, Dict[str, Any], List[Any]], 
                             sub_agent_name: Optional[str] = None) -> None:
        """Send tool result update message."""
        result_msg = self._create_tool_result_message(tool_name, result, sub_agent_name)
        await self.send_to_user(user_id, result_msg)

    def _create_tool_result_message(self, tool_name: str, result: Union[str, Dict[str, Any], List[Any]], 
                                  sub_agent_name: Optional[str]) -> Dict[str, Any]:
        """Create tool result message payload."""
        payload = {"tool_name": tool_name, "result": result, "sub_agent_name": sub_agent_name, "timestamp": time.time()}
        return {"type": "tool_result", "payload": payload, "displayed_to_user": True}

    async def send_sub_agent_update(self, user_id: str, sub_agent_name: str, state: Dict[str, Any]) -> None:
        """Send sub-agent status update message."""
        update_msg = {
            "type": "sub_agent_update",
            "payload": {"sub_agent_name": sub_agent_name, "state": state, "timestamp": time.time()},
            "displayed_to_user": True
        }
        await self.send_to_user(user_id, update_msg)