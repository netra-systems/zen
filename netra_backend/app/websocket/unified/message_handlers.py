"""WebSocket Message Handlers and Processing.

Handles message validation, processing, and specialized message types
for agent communication and tool interactions.
"""

import time
from typing import Dict, Any, Union, Optional, List, Literal
from fastapi import WebSocket
from starlette.websockets import WebSocketState

from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.websocket_message_types import WebSocketValidationError
from netra_backend.app.core.json_utils import prepare_websocket_message
from netra_backend.app.websocket.connection import ConnectionInfo
from netra_backend.app.websocket.validation import MessageValidator
from netra_backend.app.websocket.state_synchronization_manager import StateSynchronizationManager

logger = central_logger.get_logger(__name__)


class MessageHandler:
    """Handles message validation and processing operations."""
    
    def __init__(self, manager):
        self.manager = manager
        self.validator = MessageValidator()
        self.state_sync = StateSynchronizationManager()
    
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
    
    async def handle_state_sync_message(self, user_id: str, connection_id: str, 
                                      websocket: WebSocket, message: Dict[str, Any]) -> bool:
        """Handle state synchronization messages."""
        message_type = message.get("type")
        payload = message.get("payload", {})
        
        if message_type == "get_current_state":
            session_id = payload.get("session_id", "")
            await self.state_sync.handle_get_current_state(user_id, session_id, websocket)
        elif message_type == "state_update":
            await self.state_sync.handle_state_update(user_id, payload)
        elif message_type == "partial_state_update":
            await self.state_sync.handle_partial_state_update(user_id, payload)
        elif message_type == "client_state_update":
            await self.state_sync.handle_state_update(user_id, payload)
        else:
            logger.warning(f"Unknown state sync message type: {message_type}")
            return False
        
        return True
    
    async def handle_new_connection_state_sync(self, user_id: str, connection_id: str, websocket: WebSocket) -> None:
        """Handle state synchronization for new connections."""
        await self.state_sync.handle_new_connection(user_id, connection_id, websocket)
    
    async def handle_reconnection_state_sync(self, user_id: str, connection_id: str, websocket: WebSocket) -> None:
        """Handle state synchronization for reconnections."""
        await self.state_sync.handle_reconnection(user_id, connection_id, websocket)
    
    async def handle_disconnection_state_sync(self, user_id: str, connection_id: str) -> None:
        """Handle state synchronization cleanup for disconnections."""
        await self.state_sync.handle_disconnection(user_id, connection_id)


class MessageBuilder:
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
        self._last_validation_error = None
    
    async def process_with_rate_limiting(self, conn_info: ConnectionInfo, message: Dict[str, Any]) -> bool:
        """Process message with rate limiting checks."""
        logger.info(f"[CRITICAL ENTRY] process_with_rate_limiting called with message type: {message.get('type')}")
        logger.info(f"[CRITICAL ENTRY] Connection info: {conn_info.connection_id}, metadata: {conn_info.metadata}")
        
        if self.manager.rate_limiter.is_rate_limited(conn_info):
            logger.warning(f"[CRITICAL] Rate limited for connection {conn_info.connection_id}")
            await self._handle_rate_limit_exceeded(conn_info)
            return False
        
        logger.info(f"[CRITICAL] Not rate limited, proceeding to validate and process")
        return await self._validate_and_process_message(conn_info, message)
    
    async def _handle_rate_limit_exceeded(self, conn_info: ConnectionInfo) -> None:
        """Handle rate limit exceeded with error response."""
        rate_info = self.manager.rate_limiter.get_rate_limit_info(conn_info)
        await self.manager.error_handler.handle_rate_limit_error(conn_info, rate_info)
        error_msg = MessageBuilder.create_rate_limit_error_message()
        await self._send_system_message(conn_info, error_msg)
    
    async def _validate_and_process_message(self, conn_info: ConnectionInfo, message: Dict[str, Any]) -> bool:
        """Validate and process incoming message."""
        if self.handler.is_ping_message(message):
            await self.handler.handle_ping_message(conn_info.websocket)
            return True
        
        # First validate the message and send error if validation fails
        validation_result = await self._validate_message_and_update_stats(message)
        if not validation_result:
            # Send validation error response to client
            await self._send_validation_error_response(conn_info, message)
            return True  # Keep connection alive after validation error
        
        # CRITICAL: Actually process the message through agent service
        return await self._forward_to_agent_service(conn_info, message)
    
    async def _forward_to_agent_service(self, conn_info: ConnectionInfo, message: Dict[str, Any]) -> bool:
        """Forward validated message to agent service for processing."""
        import json
        
        logger.info(f"[CRITICAL DEBUG] Attempting to forward message type: {message.get('type')}")
        logger.info(f"[CRITICAL DEBUG] Connection metadata: {conn_info.metadata}")
        
        try:
            # Get user_id from connection metadata
            user_id = conn_info.metadata.get("user_id")
            if not user_id:
                logger.error(f"[CRITICAL] No user_id found in metadata for connection {conn_info.connection_id}")
                logger.error(f"[CRITICAL] Available metadata keys: {list(conn_info.metadata.keys())}")
                return False
            
            logger.info(f"[CRITICAL DEBUG] Found user_id: {user_id}")
            
            # Get agent service from app state
            app = conn_info.websocket.app
            if not hasattr(app, 'state'):
                logger.error("[CRITICAL] WebSocket app has no state attribute!")
                return False
                
            if not hasattr(app.state, 'agent_service'):
                logger.error("[CRITICAL] Agent service not found in app.state!")
                logger.error(f"[CRITICAL] Available app.state attributes: {dir(app.state)}")
                return False
            
            agent_service = app.state.agent_service
            logger.info(f"[CRITICAL DEBUG] Found agent service: {agent_service}")
            
            # Forward message to agent service as JSON string
            message_str = json.dumps(message)
            
            logger.info(f"[CRITICAL] Forwarding message to agent service for user {user_id}: {message.get('type')}")
            logger.info(f"[CRITICAL] Message payload: {message.get('payload')}")
            
            # Process through agent service (this will handle the message routing)
            from netra_backend.app.db.postgres import get_async_db
            async with get_async_db() as db_session:
                logger.info(f"[CRITICAL] Calling agent_service.handle_websocket_message")
                await agent_service.handle_websocket_message(user_id, message_str, db_session)
                logger.info(f"[CRITICAL] Successfully called agent_service.handle_websocket_message")
            
            return True
            
        except Exception as e:
            logger.error(f"[CRITICAL ERROR] Failed to forward message to agent service: {e}", exc_info=True)
            return False
    
    async def _validate_message_and_update_stats(self, message: Dict[str, Any]) -> bool:
        """Validate message and update statistics."""
        validation_result = self.handler.validate_message(message)
        if isinstance(validation_result, WebSocketValidationError):
            logger.warning(f"Message validation failed: {validation_result.message}")
            # Store validation error for detailed error response
            self._last_validation_error = validation_result
            return False
        self.message_stats["received"] += 1
        self.message_stats["validated"] += 1
        self._last_validation_error = None
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
    
    async def _send_validation_error_response(self, conn_info: ConnectionInfo, message: Dict[str, Any]) -> None:
        """Send detailed validation error response to client."""
        error_response = self._create_validation_error_response(message)
        await self._send_system_message(conn_info, error_response)
    
    def _create_validation_error_response(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Create detailed validation error response."""
        validation_error = self._last_validation_error
        error_details = {
            "type": "error",
            "error": validation_error.message if validation_error else "Validation failed",
            "error_type": validation_error.error_type if validation_error else "validation_error",
            "code": "VALIDATION_ERROR",
            "timestamp": time.time(),
            "recoverable": True,
            "details": self._get_validation_error_details(validation_error, message)
        }
        return error_details
    
    def _get_validation_error_details(self, validation_error, message: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed validation error information."""
        details = {"received_message_type": type(message).__name__}
        if validation_error:
            if hasattr(validation_error, 'field') and validation_error.field:
                details["invalid_field"] = validation_error.field
            if hasattr(validation_error, 'error_type'):
                details["validation_type"] = validation_error.error_type
        if isinstance(message, dict) and "type" in message:
            details["message_type"] = message["type"]
        return details
    
    def get_stats(self) -> Dict[str, int]:
        """Get message processing statistics."""
        return self.message_stats.copy()