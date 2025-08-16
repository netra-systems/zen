"""Enhanced WebSocket message handler with comprehensive reliability features.

This module provides a reliable message handling system with circuit breakers,
retry logic, validation, and comprehensive error recovery.
"""

import json
from typing import Dict, Any, Optional, Callable, Awaitable
from datetime import datetime, UTC

from app.logging_config import central_logger
from app.core.reliability import (
    get_reliability_wrapper, CircuitBreakerConfig, RetryConfig
)
from app.core.json_utils import prepare_websocket_message
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
        self._initialize_handlers(validator, error_handler)
        self._initialize_reliability_wrapper()
        self._initialize_stats()

    def _initialize_handlers(self, validator: Optional[MessageValidator], error_handler: Optional[WebSocketErrorHandler]) -> None:
        """Initialize validator and error handler with defaults."""
        self.validator = validator or default_message_validator
        self.error_handler = error_handler or default_error_handler

    def _initialize_reliability_wrapper(self) -> None:
        """Initialize reliability wrapper for message handling."""
        circuit_config = self._create_circuit_breaker_config()
        retry_config = self._create_retry_config()
        self.reliability = get_reliability_wrapper(
            "WebSocketMessageHandler", circuit_config, retry_config
        )

    def _create_circuit_breaker_config(self) -> CircuitBreakerConfig:
        """Create circuit breaker configuration."""
        return CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=30.0,
            name="WebSocketMessageHandler"
        )

    def _create_retry_config(self) -> RetryConfig:
        """Create retry configuration."""
        return RetryConfig(
            max_retries=2,
            base_delay=0.5,
            max_delay=5.0
        )

    def _initialize_stats(self) -> None:
        """Initialize message processing statistics."""
        self.stats = self._create_default_stats()

    def _create_default_stats(self) -> Dict[str, int]:
        """Create default statistics dictionary."""
        return {
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
        """Handle incoming WebSocket message with full reliability protection."""
        return await self._execute_message_handling_pipeline(
            raw_message, conn_info, message_processor
        )

    async def _execute_message_handling_pipeline(
        self, raw_message: str, conn_info: ConnectionInfo, message_processor
    ) -> bool:
        """Execute complete message handling pipeline with error protection."""
        process_func = self._create_process_message_func(raw_message, conn_info, message_processor)
        fallback_func = self._create_fallback_message_func(conn_info)
        return await self._try_process_message_with_fallback(process_func, fallback_func, conn_info)

    async def _try_process_message_with_fallback(
        self, process_func, fallback_func, conn_info: ConnectionInfo
    ) -> bool:
        """Try processing message with fallback on exception."""
        try:
            success = await self._execute_message_processing(process_func, fallback_func)
            self._update_failure_stats(success)
            return success
        except Exception as e:
            return await self._handle_message_exception(conn_info, e)

    def _create_process_message_func(self, raw_message: str, conn_info: ConnectionInfo, message_processor):
        """Create message processing function."""
        async def _process_message():
            return await self._process_message_steps(raw_message, conn_info, message_processor)
        return _process_message

    async def _process_message_steps(self, raw_message: str, conn_info: ConnectionInfo, message_processor) -> bool:
        """Execute message processing steps."""
        message_data = await self._parse_json_message(raw_message, conn_info)
        if not await self._handle_parse_result(message_data):
            return False
        validated_message = await self._validate_and_sanitize_message(message_data, conn_info)
        if not await self._handle_validation_result(validated_message):
            return False
        return await self._execute_message_processor(validated_message, conn_info, message_processor)

    async def _handle_parse_result(self, message_data) -> bool:
        """Handle parse result validation."""
        return message_data is not None

    async def _handle_validation_result(self, validated_message) -> bool:
        """Handle validation result validation."""
        return validated_message is not None

    def _create_fallback_message_func(self, conn_info: ConnectionInfo):
        """Create fallback message handling function."""
        async def _fallback_message_handling():
            return await self._execute_fallback_handling(conn_info)
        return _fallback_message_handling

    async def _execute_fallback_handling(self, conn_info: ConnectionInfo) -> bool:
        """Execute fallback message handling steps."""
        logger.warning(f"Using fallback message handling for connection {conn_info.connection_id}")
        await self._send_error_response(
            conn_info, "MESSAGE_PROCESSING_FAILED", 
            "Message could not be processed. Please try again."
        )
        self.stats["fallback_used"] += 1
        return False

    async def _execute_message_processing(self, process_func, fallback_func) -> bool:
        """Execute message processing with reliability protection."""
        return await self.reliability.execute_safely(
            process_func,
            "handle_message",
            fallback=fallback_func,
            timeout=10.0
        )

    def _update_failure_stats(self, success: bool) -> None:
        """Update failure statistics if processing failed."""
        if not success:
            self.stats["messages_failed"] += 1

    async def _handle_message_exception(self, conn_info: ConnectionInfo, error: Exception) -> bool:
        """Handle unexpected exceptions during message handling."""
        logger.error(f"Unexpected error handling message from {conn_info.connection_id}: {error}")
        await self._handle_unexpected_error(conn_info, error)
        return False

    async def _parse_json_message(self, raw_message: str, conn_info: ConnectionInfo):
        """Parse JSON message with error handling."""
        try:
            return json.loads(raw_message)
        except json.JSONDecodeError as e:
            await self._handle_parse_error(raw_message, conn_info, str(e))
            return None

    async def _validate_and_sanitize_message(self, message_data: Dict[str, Any], conn_info: ConnectionInfo):
        """Validate and sanitize message data."""
        validation_result = self.validator.validate_message(message_data)
        if validation_result is not True:
            await self._handle_validation_error(message_data, conn_info, validation_result)
            return None
        return self.validator.sanitize_message(message_data)

    async def _execute_message_processor(self, sanitized_message: Dict[str, Any], conn_info: ConnectionInfo, message_processor) -> bool:
        """Execute message processor and update statistics."""
        await message_processor(sanitized_message, conn_info)
        self.stats["messages_processed"] += 1
        conn_info.message_count += 1
        return True

    async def _handle_parse_error(
        self, raw_message: str, conn_info: ConnectionInfo, error_msg: str
    ):
        """Handle JSON parsing errors."""
        logger.warning(f"JSON parse error from {conn_info.connection_id}: {error_msg}")
        await self._log_parse_error_to_handler(raw_message, conn_info, error_msg)
        await self._send_parse_error_response(conn_info)

    async def _log_parse_error_to_handler(
        self, raw_message: str, conn_info: ConnectionInfo, error_msg: str
    ):
        """Log parse error to error handler."""
        error_context = self._create_parse_error_context(raw_message, error_msg)
        await self.error_handler.handle_validation_error(
            conn_info.user_id or "unknown", f"Invalid JSON: {error_msg}", error_context
        )

    async def _send_parse_error_response(self, conn_info: ConnectionInfo):
        """Send parse error response to client."""
        await self._send_error_response(
            conn_info, "INVALID_JSON", "Message must be valid JSON"
        )

    def _create_parse_error_context(self, raw_message: str, error_msg: str) -> Dict[str, Any]:
        """Create error context for parse errors."""
        return {
            "raw_message_length": len(raw_message),
            "raw_message_sample": raw_message[:100] if len(raw_message) > 100 else raw_message,
            "error": error_msg
        }

    async def _handle_validation_error(
        self, message_data: Dict[str, Any], conn_info: ConnectionInfo, validation_error: Any
    ):
        """Handle message validation errors."""
        self._increment_validation_failure_stats()
        logger.warning(f"Message validation failed from {conn_info.connection_id}: {validation_error.message}")
        await self._log_validation_error_to_handler(message_data, conn_info, validation_error)
        await self._send_validation_error_response(conn_info, validation_error)

    def _increment_validation_failure_stats(self):
        """Increment validation failure statistics."""
        self.stats["validation_failures"] += 1

    async def _log_validation_error_to_handler(
        self, message_data: Dict[str, Any], conn_info: ConnectionInfo, validation_error: Any
    ):
        """Log validation error to error handler."""
        error_context = self._create_validation_error_context(validation_error, message_data)
        await self.error_handler.handle_validation_error(
            conn_info.user_id or "unknown", validation_error.message, error_context
        )

    async def _send_validation_error_response(self, conn_info: ConnectionInfo, validation_error: Any):
        """Send validation error response to client."""
        await self._send_error_response(
            conn_info, "VALIDATION_ERROR", validation_error.message
        )

    def _create_validation_error_context(self, validation_error: Any, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create error context for validation errors."""
        return {
            "error_type": validation_error.error_type,
            "field": getattr(validation_error, 'field', None),
            "message_type": message_data.get("type", "unknown")
        }

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
        self, conn_info: ConnectionInfo, error_code: str, error_message: str
    ):
        """Send error response to client."""
        try:
            error_response = self._create_error_response(error_code, error_message)
            await self._send_error_if_connected(conn_info, error_response)
        except Exception as e:
            logger.error(f"Failed to send error response to {conn_info.connection_id}: {e}")

    def _create_error_response(self, error_code: str, error_message: str) -> Dict[str, Any]:
        """Create error response structure."""
        return {
            "type": "error",
            "payload": {
                "error_code": error_code,
                "message": error_message,
                "timestamp": datetime.now(UTC).isoformat()
            },
            "sender": "system"
        }

    async def _send_error_if_connected(self, conn_info: ConnectionInfo, error_response: Dict[str, Any]) -> None:
        """Send error response if connection is still open."""
        from starlette.websockets import WebSocketState
        if conn_info.websocket.client_state == WebSocketState.CONNECTED:
            prepared_message = prepare_websocket_message(error_response)
            await conn_info.websocket.send_json(prepared_message)
        else:
            logger.debug(f"Cannot send error response to {conn_info.connection_id}: connection closed")

    def get_stats(self) -> Dict[str, Any]:
        """Get message handling statistics."""
        reliability_stats = self.reliability.get_health_status()
        message_handler_stats = self._build_message_handler_stats()
        error_handler_stats = self.error_handler.get_error_stats()
        return self._combine_stats(message_handler_stats, reliability_stats, error_handler_stats)

    def _combine_stats(self, message_stats, reliability_stats, error_stats) -> Dict[str, Any]:
        """Combine all statistics into single dict."""
        return {
            "message_handler": message_stats,
            "reliability": reliability_stats,
            "error_handler": error_stats
        }

    def _build_message_handler_stats(self) -> Dict[str, Any]:
        """Build message handler statistics."""
        success_rate = self._calculate_success_rate()
        return {
            "messages_processed": self.stats["messages_processed"],
            "messages_failed": self.stats["messages_failed"],
            "validation_failures": self.stats["validation_failures"],
            "fallback_used": self.stats["fallback_used"],
            "success_rate": success_rate
        }

    def _calculate_success_rate(self) -> float:
        """Calculate message processing success rate."""
        total_attempts = self.stats["messages_processed"] + self.stats["messages_failed"]
        return self.stats["messages_processed"] / max(1, total_attempts)

    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status."""
        stats = self.get_stats()
        overall_health = self._calculate_overall_health(stats)
        status = self._determine_health_status(overall_health)
        return self._build_health_status_response(overall_health, status, stats)

    def _build_health_status_response(self, overall_health: float, status: str, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Build health status response dictionary."""
        return {
            "overall_health": overall_health,
            "status": status,
            "message_processing": stats["message_handler"],
            "circuit_breaker_status": self.reliability.circuit_breaker.get_status(),
            "validation_status": self._build_validation_status(stats)
        }

    def _calculate_overall_health(self, stats: Dict[str, Any]) -> float:
        """Calculate overall health score."""
        success_rate = stats["message_handler"]["success_rate"]
        reliability_health = stats["reliability"]["health_score"]
        return (success_rate + reliability_health) / 2

    def _determine_health_status(self, overall_health: float) -> str:
        """Determine health status from score."""
        if overall_health > 0.8:
            return "healthy"
        elif overall_health > 0.5:
            return "degraded"
        else:
            return "unhealthy"

    def _build_validation_status(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Build validation status information."""
        return {
            "validation_failures": stats["message_handler"]["validation_failures"],
            "validator_limits": {
                "max_message_size": self.validator.max_message_size,
                "max_text_length": self.validator.max_text_length
            }
        }