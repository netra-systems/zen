"""WebSocket Message Router

Provides message routing functionality with handler registration, 
middleware support, and metrics tracking.
"""

import asyncio
import time
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.websocket.message_handler import BaseMessageHandler

logger = central_logger.get_logger(__name__)


class MessageRouter:
    """Routes WebSocket messages to registered handlers with middleware support."""
    
    def __init__(self):
        self.handlers: Dict[str, BaseMessageHandler] = {}
        self.middleware: List[Callable] = []
        self.routing_metrics = self._init_metrics()
    
    def _init_metrics(self) -> Dict[str, Any]:
        """Initialize routing metrics tracking."""
        return {
            'messages_routed': 0,
            'routing_errors': 0,
            'handler_execution_times': defaultdict(list)
        }
    
    def register_handler(self, handler: BaseMessageHandler) -> None:
        """Register a message handler for routing."""
        message_type = handler.get_message_type()
        self._validate_handler_registration(message_type)
        self._store_handler(message_type, handler)
    
    def _validate_handler_registration(self, message_type: str) -> None:
        """Validate handler registration requirements."""
        if message_type in self.handlers:
            raise NetraException(f"Handler for {message_type} already registered")
    
    def _store_handler(self, message_type: str, handler: BaseMessageHandler) -> None:
        """Store handler in registry with logging."""
        self.handlers[message_type] = handler
        logger.info(f"Registered handler for message type: {message_type}")
    
    def unregister_handler(self, message_type: str) -> None:
        """Unregister a message handler."""
        if message_type in self.handlers:
            del self.handlers[message_type]
            logger.info(f"Unregistered handler for: {message_type}")
    
    async def route_message(self, user_id: str, message_type: str, payload: Dict[str, Any]) -> bool:
        """Route message to appropriate handler with middleware processing."""
        try:
            handler = self._get_handler(message_type)
            processed_payload = await self._process_middleware(user_id, message_type, payload)
            result = await self._execute_handler(user_id, handler, processed_payload, message_type)
            self._record_success()
            return result
        except Exception as e:
            self._record_error()
            raise NetraException(f"Message routing failed: {str(e)}")
    
    def _get_handler(self, message_type: str) -> BaseMessageHandler:
        """Get handler for message type with validation."""
        if message_type not in self.handlers:
            raise NetraException(f"No handler registered for message type: {message_type}")
        return self.handlers[message_type]
    
    async def _process_middleware(self, user_id: str, message_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process payload through middleware pipeline."""
        current_payload = payload
        for middleware_func in self.middleware:
            current_payload = await middleware_func(user_id, message_type, current_payload)
        return current_payload
    
    async def _execute_handler(self, user_id: str, handler: BaseMessageHandler, payload: Dict[str, Any], message_type: str) -> bool:
        """Execute handler with performance tracking."""
        start_time = time.time()
        await handler.handle(user_id, payload)
        execution_time = time.time() - start_time
        self._record_execution_time(message_type, execution_time)
        return True
    
    def _record_execution_time(self, message_type: str, execution_time: float) -> None:
        """Record handler execution time metrics."""
        self.routing_metrics['handler_execution_times'][message_type].append(execution_time)
    
    def _record_success(self) -> None:
        """Record successful message routing."""
        self.routing_metrics['messages_routed'] += 1
    
    def _record_error(self) -> None:
        """Record routing error in metrics."""
        self.routing_metrics['routing_errors'] += 1
    
    def add_middleware(self, middleware_func: Callable) -> None:
        """Add middleware function to processing pipeline."""
        self.middleware.append(middleware_func)
        logger.info(f"Added middleware: {middleware_func.__name__}")
    
    def clear_middleware(self) -> None:
        """Clear all middleware from pipeline."""
        self.middleware.clear()
        logger.info("Cleared all middleware")
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get current routing statistics."""
        return {
            'total_handlers': len(self.handlers),
            'registered_types': list(self.handlers.keys()),
            'middleware_count': len(self.middleware),
            'metrics': self.routing_metrics
        }
    
    def reset_metrics(self) -> None:
        """Reset routing metrics to initial state."""
        self.routing_metrics = self._init_metrics()
        logger.info("Reset routing metrics")