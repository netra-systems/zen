"""WebSocket Message Handlers and Processing.

Handles message validation, processing, and specialized message types
for agent communication and tool interactions.
"""

import time
from typing import Dict, Any, Union, Optional, List, Literal
from fastapi import WebSocket
from starlette.websockets import WebSocketState

from app.logging_config import central_logger
from app.schemas.websocket_message_types import WebSocketValidationError
from app.core.json_utils import prepare_websocket_message
from app.websocket.connection import ConnectionInfo
from app.websocket.validation import MessageValidator

logger = central_logger.get_logger(__name__)


class MessageHandler:
    """Handles message validation and processing operations."""
    
    def __init__(self, manager):
        self.manager = manager
        self.validator = MessageValidator()
    
    def validate_message(self, message: Dict[str, Any]) -> Union[bool, WebSocketValidationError]:
        """Validate message structure and content."""
        return self.validator.validate_message(message)
    
    def sanitize_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize message content for security."""
        return self.validator.sanitize_message(message)
    
    def prepare_and_validate_message(self, message: Union[Dict[str, Any], Any]) -> Optional[Dict[str, Any]]:
        """Prepare and validate message for sending."""
        if isinstance(message, dict):
            validation_result = self.validate_message(message)
            if isinstance(validation_result, WebSocketValidationError):
                logger.error(f"Message validation failed: {validation_result.message}")
                return None
            message = self.sanitize_message(message)
        return self._ensure_timestamp(message)
    
    def _ensure_timestamp(self, message: Any) -> Dict[str, Any]:
        """Ensure message has timestamp for tracking."""
        if isinstance(message, dict) and "timestamp" not in message:
            message["timestamp"] = time.time()
        return message if isinstance(message, dict) else {"data": message, "timestamp": time.time()}
    
    async def send_to_single_connection(self, conn_info: ConnectionInfo, message: Dict[str, Any]) -> bool:
        """Send message to single connection with error handling."""
        try:
            if conn_info.websocket.client_state == WebSocketState.CONNECTED:
                prepared = prepare_websocket_message(message)
                await conn_info.websocket.send_json(prepared)
                return True
        except Exception as e:
            await self._handle_connection_send_error(conn_info, e)
        return False
    
    async def _handle_connection_send_error(self, conn_info: ConnectionInfo, error: Exception) -> None:
        """Handle connection send errors with appropriate cleanup."""
        if "Cannot call" in str(error) or "close" in str(error).lower():
            logger.debug(f"Connection {conn_info.connection_id} closed during send")
        else:
            logger.error(f"Send error for connection {conn_info.connection_id}: {error}")
    
    def is_ping_message(self, message: Dict[str, Any]) -> bool:
        """Check if message is a ping message."""
        return isinstance(message, dict) and message.get("type") == "ping"
    
    async def handle_ping_message(self, websocket: WebSocket) -> None:
        """Handle ping message with pong response."""
        pong_response = {"type": "pong", "timestamp": time.time()}
        await websocket.send_json(pong_response)


class AgentMessageBuilder:
    """Builds specialized messages for agent and tool communication."""
    
    @staticmethod
    def create_error_message(error_message: str, sub_agent_name: str = "System") -> Dict[str, Any]:
        """Create error message structure."""
        return {
            "type": "error",
            "payload": {"error": error_message, "sub_agent_name": sub_agent_name},
            "displayed_to_user": True, "timestamp": time.time()
        }
    
    @staticmethod
    def create_agent_log_message(log_level: Literal["debug", "info", "warning", "error", "critical"], 
                               message: str, sub_agent_name: Optional[str] = None) -> Dict[str, Any]:
        """Create agent log message structure."""
        return {
            "type": "agent_log",
            "payload": {
                "level": log_level, "message": message, "sub_agent_name": sub_agent_name,
                "timestamp": time.time()
            },
            "displayed_to_user": True
        }
    
    @staticmethod
    def create_tool_call_message(tool_name: str, tool_args: Dict[str, Any], 
                               sub_agent_name: Optional[str] = None) -> Dict[str, Any]:
        """Create tool call message structure."""
        return {
            "type": "tool_call",
            "payload": {
                "tool_name": tool_name, "tool_args": tool_args, "sub_agent_name": sub_agent_name,
                "timestamp": time.time()
            },
            "displayed_to_user": True
        }
    
    @staticmethod
    def create_tool_result_message(tool_name: str, result: Union[str, Dict[str, Any], List[Any]], 
                                 sub_agent_name: Optional[str] = None) -> Dict[str, Any]:
        """Create tool result message structure."""
        return {
            "type": "tool_result",
            "payload": {
                "tool_name": tool_name, "result": result, "sub_agent_name": sub_agent_name,
                "timestamp": time.time()
            },
            "displayed_to_user": True
        }
    
    @staticmethod
    def create_sub_agent_update_message(sub_agent_name: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create sub-agent update message structure."""
        return {
            "type": "sub_agent_update",
            "payload": {"sub_agent_name": sub_agent_name, "state": state, "timestamp": time.time()},
            "displayed_to_user": True
        }
    
    @staticmethod
    def create_rate_limit_error_message() -> Dict[str, Any]:
        """Create rate limit error message."""
        return {
            "type": "error",
            "payload": {"error": "Rate limit exceeded", "code": "RATE_LIMIT_EXCEEDED"},
            "timestamp": time.time(), "system": True
        }


class MessageProcessor:
    """Processes incoming and outgoing WebSocket messages."""
    
    def __init__(self, manager, handler: MessageHandler):
        self.manager = manager
        self.handler = handler
        self.message_stats = {"sent": 0, "received": 0, "failed": 0, "validated": 0}
    
    async def process_with_rate_limiting(self, conn_info: ConnectionInfo, message: Dict[str, Any]) -> bool:
        """Process message with rate limiting checks."""
        if self.manager.rate_limiter.is_rate_limited(conn_info):
            await self._handle_rate_limit_exceeded(conn_info)
            return False
        return await self._validate_and_process_message(conn_info, message)
    
    async def _handle_rate_limit_exceeded(self, conn_info: ConnectionInfo) -> None:
        """Handle rate limit exceeded with error response."""
        rate_info = self.manager.rate_limiter.get_rate_limit_info(conn_info)
        await self.manager.error_handler.handle_rate_limit_error(conn_info, rate_info)
        error_msg = AgentMessageBuilder.create_rate_limit_error_message()
        await self._send_system_message(conn_info, error_msg)
    
    async def _validate_and_process_message(self, conn_info: ConnectionInfo, message: Dict[str, Any]) -> bool:
        """Validate and process incoming message."""
        if self.handler.is_ping_message(message):
            await self.handler.handle_ping_message(conn_info.websocket)
            return True
        return await self._validate_message_and_update_stats(message)
    
    async def _validate_message_and_update_stats(self, message: Dict[str, Any]) -> bool:
        """Validate message and update statistics."""
        validation_result = self.handler.validate_message(message)
        if isinstance(validation_result, WebSocketValidationError):
            logger.warning(f"Message validation failed: {validation_result.message}")
            return False
        self.message_stats["received"] += 1
        self.message_stats["validated"] += 1
        return True
    
    async def _send_system_message(self, conn_info: ConnectionInfo, message: Dict[str, Any]) -> None:
        """Send system message to connection."""
        message["system"] = True
        await self.handler.send_to_single_connection(conn_info, message)
    
    def update_send_stats(self, success: bool) -> None:
        """Update message send statistics."""
        if success:
            self.message_stats["sent"] += 1
        else:
            self.message_stats["failed"] += 1
    
    def get_stats(self) -> Dict[str, int]:
        """Get message processing statistics."""
        return self.message_stats.copy()