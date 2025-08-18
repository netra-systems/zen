"""Enhanced WebSocket message handler with comprehensive reliability features.

Main entry point for reliable message handling functionality.
"""

from typing import Dict, Any, Optional, Callable, Awaitable

from app.websocket.message_handler_config import MessageHandlerConfig
from app.websocket.message_handler_pipeline import MessageProcessingPipeline
from app.websocket.message_handler_response import MessageHandlerResponseManager
from app.websocket.validation import MessageValidator
from app.websocket.error_handler import WebSocketErrorHandler
from app.websocket.connection import ConnectionInfo


class ReliableMessageHandler:
    """Reliable WebSocket message handler with comprehensive error recovery."""
    
    def __init__(
        self,
        validator: Optional[MessageValidator] = None,
        error_handler: Optional[WebSocketErrorHandler] = None
    ):
        self.config = MessageHandlerConfig(validator, error_handler)
        self.pipeline = MessageProcessingPipeline(self.config)
        self.response_manager = MessageHandlerResponseManager(self.config)

    async def handle_message(
        self,
        raw_message: str,
        conn_info: ConnectionInfo,
        message_processor: Callable[[Dict[str, Any], ConnectionInfo], Awaitable[Any]]
    ) -> bool:
        """Handle incoming WebSocket message with full reliability protection."""
        return await self.pipeline.process_message(raw_message, conn_info, message_processor)

    def get_stats(self) -> Dict[str, Any]:
        """Get message handling statistics."""
        return self.response_manager.get_stats()

    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status."""
        return self.response_manager.get_health_status()