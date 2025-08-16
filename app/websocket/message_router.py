"""WebSocket message type routing functionality.

Routes messages to appropriate handlers based on message type.
"""

import asyncio
from typing import Dict, Any, Optional, Callable, Awaitable

from app.logging_config import central_logger
from .connection import ConnectionInfo

logger = central_logger.get_logger(__name__)


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
            return await self._route_to_registered_handler(message_type, message, conn_info)
        elif self.fallback_handler:
            return await self._route_to_fallback_handler(message_type, message, conn_info)
        else:
            return self._handle_no_handler_available(message_type)

    async def _route_to_registered_handler(self, message_type: str, message: Dict[str, Any], conn_info: ConnectionInfo) -> Any:
        """Route message to registered handler."""
        handler = self.handlers[message_type]
        logger.debug(f"Routing {message_type} message to registered handler")
        return await handler(message, conn_info)

    async def _route_to_fallback_handler(self, message_type: str, message: Dict[str, Any], conn_info: ConnectionInfo) -> Any:
        """Route message to fallback handler."""
        logger.debug(f"Routing unknown message type {message_type} to fallback handler")
        return await self.fallback_handler(message, conn_info)

    def _handle_no_handler_available(self, message_type: str):
        """Handle case when no handler is available."""
        logger.warning(f"No handler registered for message type: {message_type}")
        raise ValueError(f"No handler available for message type: {message_type}")

    def get_registered_types(self) -> list:
        """Get list of registered message types."""
        return list(self.handlers.keys())