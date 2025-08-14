"""Enhanced WebSocket message handler with comprehensive reliability features.

This module provides a reliable message handling system with circuit breakers,
retry logic, validation, and comprehensive error recovery.
"""

import asyncio
import json
from typing import Dict, Any, Optional, Callable, Awaitable
from datetime import datetime

from app.logging_config import central_logger
from app.core.reliability import (
    get_reliability_wrapper, CircuitBreakerConfig, RetryConfig
)
from app.core.json_utils import prepare_websocket_message, safe_json_dumps
from .validation import MessageValidator, default_message_validator
from .error_handler import WebSocketErrorHandler, default_error_handler
from .connection import ConnectionInfo

logger = central_logger.get_logger(__name__)


class ReliableMessageHandler:
    """Reliable WebSocket message handler with comprehensive error recovery."""
    
    def __init__(
        self,
        validator: Optional[MessageValidator] = None,
        error_handler: Optional[WebSocketErrorHandler] = None
    ):
        self.validator = validator or default_message_validator
        self.error_handler = error_handler or default_error_handler
        
        # Initialize reliability wrapper for message handling
        self.reliability = get_reliability_wrapper(
            "WebSocketMessageHandler",
            CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=30.0,
                name="WebSocketMessageHandler"
            ),
            RetryConfig(
                max_retries=2,
                base_delay=0.5,
                max_delay=5.0
            )
        )
        
        # Message processing statistics
        self.stats = {
            "messages_processed": 0,
            "messages_failed": 0,
            "validation_failures": 0,
            "circuit_breaker_opens": 0,
            "fallback_used": 0
        }
    
    async def handle_message(
        self,
        raw_message: str,
        conn_info: ConnectionInfo,
        message_processor: Callable[[Dict[str, Any], ConnectionInfo], Awaitable[Any]]
    ) -> bool:
        """Handle incoming WebSocket message with full reliability protection.
        
        Args:
            raw_message: Raw message string from WebSocket
            conn_info: Connection information
            message_processor: Function to process validated message
            
        Returns:
            True if message was handled successfully
        """
        async def _process_message():
            # Parse JSON
            try:
                message_data = json.loads(raw_message)
            except json.JSONDecodeError as e:
                await self._handle_parse_error(raw_message, conn_info, str(e))
                return False
            
            # Validate message
            validation_result = self.validator.validate_message(message_data)
            if validation_result is not True:
                await self._handle_validation_error(message_data, conn_info, validation_result)
                return False
            
            # Sanitize message
            sanitized_message = self.validator.sanitize_message(message_data)
            
            # Process message
            await message_processor(sanitized_message, conn_info)
            
            # Update statistics
            self.stats["messages_processed"] += 1
            conn_info.message_count += 1
            
            return True
        
        async def _fallback_message_handling():
            """Fallback when primary message handling fails."""
            logger.warning(f"Using fallback message handling for connection {conn_info.connection_id}")
            
            # Send error response to client
            await self._send_error_response(
                conn_info,
                "MESSAGE_PROCESSING_FAILED",
                "Message could not be processed. Please try again."
            )
            
            self.stats["fallback_used"] += 1
            return False
        
        try:
            # Execute with reliability protection
            success = await self.reliability.execute_safely(
                _process_message,
                "handle_message",
                fallback=_fallback_message_handling,
                timeout=10.0
            )
            
            if not success:
                self.stats["messages_failed"] += 1
            
            return success
            
        except Exception as e:
            logger.error(f"Unexpected error handling message from {conn_info.connection_id}: {e}")
            await self._handle_unexpected_error(conn_info, e)
            return False
    
    async def _handle_parse_error(
        self, 
        raw_message: str, 
        conn_info: ConnectionInfo, 
        error_msg: str
    ):
        """Handle JSON parsing errors."""
        logger.warning(f"JSON parse error from {conn_info.connection_id}: {error_msg}")
        
        # Log the error with the error handler
        await self.error_handler.handle_validation_error(
            conn_info.user_id or "unknown",
            f"Invalid JSON: {error_msg}",
            {
                "raw_message_length": len(raw_message),
                "raw_message_sample": raw_message[:100] if len(raw_message) > 100 else raw_message,
                "error": error_msg
            }
        )
        
        # Send error response
        await self._send_error_response(
            conn_info,
            "INVALID_JSON",
            "Message must be valid JSON"
        )
    
    async def _handle_validation_error(
        self, 
        message_data: Dict[str, Any], 
        conn_info: ConnectionInfo, 
        validation_error: Any
    ):
        """Handle message validation errors."""
        self.stats["validation_failures"] += 1
        
        logger.warning(f"Message validation failed from {conn_info.connection_id}: {validation_error.message}")
        
        # Log the error with the error handler
        await self.error_handler.handle_validation_error(
            conn_info.user_id or "unknown",
            validation_error.message,
            {
                "error_type": validation_error.error_type,
                "field": getattr(validation_error, 'field', None),
                "message_type": message_data.get("type", "unknown")
            }
        )
        
        # Send error response
        await self._send_error_response(
            conn_info,
            "VALIDATION_ERROR",
            validation_error.message
        )
    
    async def _handle_unexpected_error(self, conn_info: ConnectionInfo, error: Exception):
        """Handle unexpected errors during message processing."""
        await self.error_handler.handle_connection_error(
            conn_info,
            f"Unexpected error during message processing: {str(error)}",
            "unexpected_error"
        )
        
        # Send generic error response
        await self._send_error_response(
            conn_info,
            "INTERNAL_ERROR",
            "An unexpected error occurred. Please try again."
        )
    
    async def _send_error_response(
        self, 
        conn_info: ConnectionInfo, 
        error_code: str, 
        error_message: str
    ):
        """Send error response to client."""
        try:
            error_response = {
                "type": "error",
                "payload": {
                    "error_code": error_code,
                    "message": error_message,
                    "timestamp": datetime.utcnow().isoformat()
                },
                "sender": "system"
            }
            
            # Check if connection is still open
            from starlette.websockets import WebSocketState
            if conn_info.websocket.client_state == WebSocketState.CONNECTED:
                prepared_message = prepare_websocket_message(error_response)
                await conn_info.websocket.send_text(safe_json_dumps(prepared_message))
            else:
                logger.debug(f"Cannot send error response to {conn_info.connection_id}: connection closed")
                
        except Exception as e:
            logger.error(f"Failed to send error response to {conn_info.connection_id}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get message handling statistics."""
        reliability_stats = self.reliability.get_health_status()
        
        return {
            "message_handler": {
                "messages_processed": self.stats["messages_processed"],
                "messages_failed": self.stats["messages_failed"],
                "validation_failures": self.stats["validation_failures"],
                "fallback_used": self.stats["fallback_used"],
                "success_rate": (
                    self.stats["messages_processed"] / 
                    max(1, self.stats["messages_processed"] + self.stats["messages_failed"])
                )
            },
            "reliability": reliability_stats,
            "error_handler": self.error_handler.get_error_stats()
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status."""
        stats = self.get_stats()
        
        # Calculate health score
        success_rate = stats["message_handler"]["success_rate"]
        reliability_health = stats["reliability"]["health_score"]
        
        overall_health = (success_rate + reliability_health) / 2
        
        return {
            "overall_health": overall_health,
            "status": "healthy" if overall_health > 0.8 else "degraded" if overall_health > 0.5 else "unhealthy",
            "message_processing": stats["message_handler"],
            "circuit_breaker_status": self.reliability.circuit_breaker.get_status(),
            "validation_status": {
                "validation_failures": stats["message_handler"]["validation_failures"],
                "validator_limits": {
                    "max_message_size": self.validator.max_message_size,
                    "max_text_length": self.validator.max_text_length
                }
            }
        }


class MessageTypeRouter:
    """Routes messages to appropriate handlers based on message type."""
    
    def __init__(self):
        self.handlers: Dict[str, Callable[[Dict[str, Any], ConnectionInfo], Awaitable[Any]]] = {}
        self.fallback_handler: Optional[Callable[[Dict[str, Any], ConnectionInfo], Awaitable[Any]]] = None
    
    def register_handler(
        self, 
        message_type: str, 
        handler: Callable[[Dict[str, Any], ConnectionInfo], Awaitable[Any]]
    ):
        """Register a handler for a specific message type."""
        self.handlers[message_type] = handler
        logger.debug(f"Registered handler for message type: {message_type}")
    
    def register_fallback_handler(
        self, 
        handler: Callable[[Dict[str, Any], ConnectionInfo], Awaitable[Any]]
    ):
        """Register a fallback handler for unknown message types."""
        self.fallback_handler = handler
        logger.debug("Registered fallback message handler")
    
    async def route_message(self, message: Dict[str, Any], conn_info: ConnectionInfo) -> Any:
        """Route message to appropriate handler."""
        message_type = message.get("type", "unknown")
        
        if message_type in self.handlers:
            handler = self.handlers[message_type]
            logger.debug(f"Routing {message_type} message to registered handler")
            return await handler(message, conn_info)
        
        elif self.fallback_handler:
            logger.debug(f"Routing unknown message type {message_type} to fallback handler")
            return await self.fallback_handler(message, conn_info)
        
        else:
            logger.warning(f"No handler registered for message type: {message_type}")
            raise ValueError(f"No handler available for message type: {message_type}")
    
    def get_registered_types(self) -> list:
        """Get list of registered message types."""
        return list(self.handlers.keys())


# Global instances
default_reliable_handler = ReliableMessageHandler()
default_message_router = MessageTypeRouter()