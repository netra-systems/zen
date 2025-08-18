"""WebSocket Message Handler Pipeline.

Core message processing pipeline with validation and error handling.
"""

import json
from typing import Dict, Any, Optional, Callable, Awaitable

from app.logging_config import central_logger
from app.websocket.connection import ConnectionInfo
from app.websocket.message_handler_config import MessageHandlerConfig

logger = central_logger.get_logger(__name__)


class MessageProcessingPipeline:
    """Core message processing pipeline with validation."""
    
    def __init__(self, config: MessageHandlerConfig):
        self.config = config

    async def process_message(
        self,
        raw_message: str,
        conn_info: ConnectionInfo,
        message_processor: Callable[[Dict[str, Any], ConnectionInfo], Awaitable[Any]]
    ) -> bool:
        """Process message through complete pipeline."""
        process_func = self._create_process_func(raw_message, conn_info, message_processor)
        fallback_func = self._create_fallback_func(conn_info)
        return await self._execute_with_reliability(process_func, fallback_func, conn_info)

    def _create_process_func(self, raw_message: str, conn_info: ConnectionInfo, message_processor):
        """Create message processing function."""
        async def _process_message():
            return await self._execute_processing_steps(raw_message, conn_info, message_processor)
        return _process_message

    async def _execute_processing_steps(self, raw_message: str, conn_info: ConnectionInfo, message_processor) -> bool:
        """Execute message processing steps."""
        message_data = await self._parse_json_message(raw_message, conn_info)
        if not message_data:
            return False
        validated_message = await self._validate_message(message_data, conn_info)
        if not validated_message:
            return False
        return await self._run_message_processor(validated_message, conn_info, message_processor)

    async def _parse_json_message(self, raw_message: str, conn_info: ConnectionInfo):
        """Parse JSON message with error handling."""
        try:
            return json.loads(raw_message)
        except json.JSONDecodeError as e:
            await self._handle_parse_error(raw_message, conn_info, str(e))
            return None

    async def _handle_parse_error(self, raw_message: str, conn_info: ConnectionInfo, error_msg: str):
        """Handle JSON parsing errors."""
        logger.warning(f"JSON parse error from {conn_info.connection_id}: {error_msg}")
        error_context = self._create_parse_error_context(raw_message, error_msg)
        await self.config.error_handler.handle_validation_error(
            conn_info.user_id or "unknown", f"Invalid JSON: {error_msg}", error_context
        )

    def _create_parse_error_context(self, raw_message: str, error_msg: str) -> Dict[str, Any]:
        """Create error context for parse errors."""
        sample_length = min(len(raw_message), 100)
        return {
            "raw_message_length": len(raw_message),
            "raw_message_sample": raw_message[:sample_length],
            "error": error_msg
        }

    async def _validate_message(self, message_data: Dict[str, Any], conn_info: ConnectionInfo):
        """Validate and sanitize message data."""
        validation_result = self.config.validator.validate_message(message_data)
        if validation_result is not True:
            await self._handle_validation_error(message_data, conn_info, validation_result)
            return None
        return self.config.validator.sanitize_message(message_data)

    async def _handle_validation_error(
        self, message_data: Dict[str, Any], conn_info: ConnectionInfo, validation_error: Any
    ):
        """Handle message validation errors."""
        self.config.stats["validation_failures"] += 1
        logger.warning(f"Message validation failed from {conn_info.connection_id}: {validation_error.message}")
        error_context = self._create_validation_error_context(validation_error, message_data)
        await self.config.error_handler.handle_validation_error(
            conn_info.user_id or "unknown", validation_error.message, error_context
        )

    def _create_validation_error_context(self, validation_error: Any, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create error context for validation errors."""
        return {
            "error_type": validation_error.error_type,
            "field": getattr(validation_error, 'field', None),
            "message_type": message_data.get("type", "unknown")
        }

    async def _run_message_processor(self, sanitized_message: Dict[str, Any], conn_info: ConnectionInfo, message_processor) -> bool:
        """Execute message processor and update statistics."""
        await message_processor(sanitized_message, conn_info)
        self.config.stats["messages_processed"] += 1
        conn_info.message_count += 1
        return True

    def _create_fallback_func(self, conn_info: ConnectionInfo):
        """Create fallback message handling function."""
        async def _fallback_message_handling():
            return await self._execute_fallback_handling(conn_info)
        return _fallback_message_handling

    async def _execute_fallback_handling(self, conn_info: ConnectionInfo) -> bool:
        """Execute fallback message handling steps."""
        logger.warning(f"Using fallback message handling for connection {conn_info.connection_id}")
        self.config.stats["fallback_used"] += 1
        return False

    async def _execute_with_reliability(self, process_func, fallback_func, conn_info: ConnectionInfo) -> bool:
        """Execute message processing with reliability protection."""
        try:
            success = await self.config.reliability.execute_safely(
                process_func,
                "handle_message",
                fallback=fallback_func,
                timeout=10.0
            )
            if not success:
                self.config.stats["messages_failed"] += 1
            return success
        except Exception as e:
            logger.error(f"Unexpected error handling message from {conn_info.connection_id}: {error}")
            return False