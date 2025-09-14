"""
Message Router Module - DEPRECATED Compatibility Layer

⚠️ DEPRECATION WARNING: This module is deprecated as of Phase 2 SSOT consolidation.
Please use the canonical MessageRouter from: netra_backend.app.websocket_core.handlers

MIGRATION PATH:
- OLD: from netra_backend.app.core.message_router import MessageRouter
- NEW: from netra_backend.app.websocket_core.handlers import MessageRouter

This module provides a compatibility layer for integration tests that expect
a message router implementation. This is a minimal implementation for test compatibility.

CRITICAL ARCHITECTURAL COMPLIANCE:
- This is a COMPATIBILITY LAYER for integration tests
- Provides minimal implementation for test collection compatibility
- DO NOT use in production - this is test infrastructure only

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Test Infrastructure Stability
- Value Impact: Enables integration test collection and execution
- Strategic Impact: Maintains test coverage during system evolution
"""

from typing import Any, Dict, List, Optional, Union, Callable
import asyncio
import uuid
import time
import warnings
from enum import Enum
from dataclasses import dataclass

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class MessageType(Enum):
    """Message types for routing."""
    REQUEST = "request"
    RESPONSE = "response"
    EVENT = "event"
    COMMAND = "command"


@dataclass
class Message:
    """Message for routing."""
    id: str
    type: MessageType
    source: str
    destination: str
    payload: Dict[str, Any]
    timestamp: float
    headers: Dict[str, str] = None

    def __post_init__(self):
        if self.headers is None:
            self.headers = {}


class MessageRouter:
    """
    Simple message router for test compatibility.

    ⚠️ DEPRECATED: Use netra_backend.app.websocket_core.handlers.MessageRouter instead
    This is a minimal implementation to satisfy integration test imports.
    Not intended for production use.
    """

    def __init__(self):
        """Initialize message router with deprecation warning."""
        # Issue deprecation warning
        warnings.warn(
            "MessageRouter from netra_backend.app.core.message_router is deprecated. "
            "Use 'from netra_backend.app.websocket_core.handlers import MessageRouter' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        self.routes: Dict[str, List[Callable]] = {}
        self.middleware: List[Callable] = []
        self.message_history: List[Message] = []
        self.active = False

        logger.warning("DEPRECATED: Message router initialized (test compatibility mode) - "
                      "Use netra_backend.app.websocket_core.handlers.MessageRouter instead")

    def add_route(self, pattern: str, handler: Callable):
        """Add a route handler."""
        if pattern not in self.routes:
            self.routes[pattern] = []
        self.routes[pattern].append(handler)

        logger.debug(f"Added route handler for pattern: {pattern}")

    def add_middleware(self, middleware: Callable):
        """Add middleware to processing pipeline."""
        self.middleware.append(middleware)
        logger.debug(f"Added middleware: {middleware.__name__}")

    async def route_message(self, message: Message) -> Optional[Any]:
        """Route a message to appropriate handler."""
        try:
            self.message_history.append(message)

            # Apply middleware
            for middleware in self.middleware:
                message = await self._apply_middleware(middleware, message)
                if message is None:
                    return None

            # Find matching routes
            handlers = self.routes.get(message.destination, [])

            if not handlers:
                logger.warning(f"No handlers found for destination: {message.destination}")
                return None

            # Execute handlers
            results = []
            for handler in handlers:
                try:
                    result = await self._execute_handler(handler, message)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Handler execution failed: {e}")

            return results[0] if len(results) == 1 else results

        except Exception as e:
            logger.error(f"Message routing failed: {e}")
            return None

    async def _apply_middleware(self, middleware: Callable, message: Message) -> Optional[Message]:
        """Apply middleware to message."""
        try:
            if asyncio.iscoroutinefunction(middleware):
                return await middleware(message)
            else:
                return middleware(message)
        except Exception as e:
            logger.error(f"Middleware application failed: {e}")
            return None

    async def _execute_handler(self, handler: Callable, message: Message) -> Any:
        """Execute message handler."""
        if asyncio.iscoroutinefunction(handler):
            return await handler(message)
        else:
            return handler(message)

    def start(self):
        """Start the message router."""
        self.active = True
        logger.info("Message router started")

    def stop(self):
        """Stop the message router."""
        self.active = False
        logger.info("Message router stopped")

    def get_statistics(self) -> Dict[str, Any]:
        """Get routing statistics."""
        return {
            "total_messages": len(self.message_history),
            "active_routes": len(self.routes),
            "middleware_count": len(self.middleware),
            "active": self.active
        }


# Global instance for compatibility
message_router = MessageRouter()

__all__ = [
    "MessageRouter",
    "Message",
    "MessageType",
    "message_router"
]