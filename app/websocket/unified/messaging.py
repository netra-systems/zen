"""Unified WebSocket Messaging - Message processing, validation, and sending.

Consolidates all message handling into a unified system with:
- Zero-loss message queuing with retry logic
- Comprehensive message validation and sanitization  
- Rate limiting with graceful degradation
- Real-time message tracking and telemetry
- Agent and tool communication support

Business Value: Ensures reliable message delivery for superior UX
All functions ≤8 lines as per CLAUDE.md requirements.
"""

import asyncio
from typing import Dict, Any, Union, Optional, List, Literal
from fastapi import WebSocket

from app.logging_config import central_logger
from app.schemas.registry import WebSocketMessage
from app.schemas.websocket_message_types import ServerMessage
from app.websocket.connection import ConnectionInfo
from .message_queue import MessageQueue
from .message_handlers import MessageHandler, MessageBuilder, MessageProcessor

logger = central_logger.get_logger(__name__)


class UnifiedMessagingManager:
    """Unified messaging manager with zero-loss guarantee."""
    
    def __init__(self, manager) -> None:
        """Initialize with reference to unified manager."""
        self.manager = manager
        self.user_queues: Dict[str, MessageQueue] = {}
        self._queue_processor_started = False
        self._init_message_components()
    
    def _init_message_components(self) -> None:
        """Initialize message handling components."""
        self.message_handler = MessageHandler(self.manager)
        self.message_processor = MessageProcessor(self.manager, self.message_handler)
        self.message_builder = MessageBuilder()
    
    def _ensure_queue_processor_started(self) -> None:
        """Lazily start queue processor when first needed."""
        if not self._queue_processor_started:
            try:
                asyncio.create_task(self._process_queues_continuously())
                self._queue_processor_started = True
            except RuntimeError:
                # No event loop running yet, will start later
                pass

    async def _process_queues_continuously(self) -> None:
        """Continuously process message queues for reliable delivery."""
        while True:
            await self._process_all_user_queues()
            await asyncio.sleep(0.1)  # 100ms processing interval

    async def _process_all_user_queues(self) -> None:
        """Process queues for all users."""
        for user_id, queue in list(self.user_queues.items()):
            await self._process_user_queue(user_id, queue)

    async def _process_user_queue(self, user_id: str, queue: MessageQueue) -> None:
        """Process messages in user's queue."""
        message = queue.get_next_message()
        if message:
            success = await self._attempt_direct_send(user_id, message)
            if not success:
                queue.add_failed_message(message)

    async def send_to_user(self, user_id: str, 
                          message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]], 
                          retry: bool = True) -> bool:
        """Send message to user with zero-loss guarantee."""
        self._ensure_queue_processor_started()
        validated_message = self.message_handler.prepare_and_validate_message(message)
        if not validated_message:
            return False
        return await self._send_with_queue_fallback(user_id, validated_message, retry)

    async def _send_with_queue_fallback(self, user_id: str, message: Dict[str, Any], retry: bool) -> bool:
        """Send message with queue fallback for zero-loss delivery."""
        direct_success = await self._attempt_direct_send(user_id, message)
        if direct_success:
            self.message_processor.update_send_stats(True)
            return True
        if retry:
            self._queue_message_for_retry(user_id, message)
        self.message_processor.update_send_stats(False)
        return False

    async def _attempt_direct_send(self, user_id: str, message: Dict[str, Any]) -> bool:
        """Attempt direct message delivery to user connections."""
        connections = self.manager.connection_manager.get_user_connections(user_id)
        if not connections:
            return False
        return await self._send_to_all_user_connections(connections, message)

    async def _send_to_all_user_connections(self, connections: List[ConnectionInfo], message: Dict[str, Any]) -> bool:
        """Send message to all user connections."""
        success_count = 0
        for conn_info in connections:
            if await self.message_handler.send_to_single_connection(conn_info, message):
                success_count += 1
        return success_count > 0

    def _queue_message_for_retry(self, user_id: str, message: Dict[str, Any]) -> None:
        """Queue message for retry delivery."""
        if user_id not in self.user_queues:
            self.user_queues[user_id] = MessageQueue()
        self.user_queues[user_id].add_message(message)

    async def handle_incoming_message(self, user_id: str, websocket: WebSocket, 
                                    message: Dict[str, Any]) -> bool:
        """Handle incoming WebSocket message with rate limiting."""
        conn_info = await self.manager.connection_manager.find_connection(user_id, websocket)
        if not conn_info:
            logger.warning(f"Connection not found for user {user_id}")
            return False
        return await self.message_processor.process_with_rate_limiting(conn_info, message)

    # Agent and tool communication methods
    async def send_error_message(self, user_id: str, error_message: str, 
                               sub_agent_name: str = "System") -> bool:
        """Send error message to user."""
        error_msg = self.message_builder.create_error_message(error_message, sub_agent_name)
        return await self.send_to_user(user_id, error_msg)

    async def send_agent_log(self, user_id: str, log_level: Literal["debug", "info", "warning", "error", "critical"], 
                           message: str, sub_agent_name: Optional[str] = None) -> None:
        """Send agent log message for real-time monitoring."""
        log_msg = self.message_builder.create_agent_log_message(log_level, message, sub_agent_name)
        await self.send_to_user(user_id, log_msg)

    async def send_tool_call(self, user_id: str, tool_name: str, tool_args: Dict[str, Any], 
                           sub_agent_name: Optional[str] = None) -> None:
        """Send tool call update message."""
        tool_msg = self.message_builder.create_tool_call_message(tool_name, tool_args, sub_agent_name)
        await self.send_to_user(user_id, tool_msg)

    async def send_tool_result(self, user_id: str, tool_name: str, 
                             result: Union[str, Dict[str, Any], List[Any]], 
                             sub_agent_name: Optional[str] = None) -> None:
        """Send tool result update message."""
        result_msg = self.message_builder.create_tool_result_message(tool_name, result, sub_agent_name)
        await self.send_to_user(user_id, result_msg)

    async def send_sub_agent_update(self, user_id: str, sub_agent_name: str, state: Dict[str, Any]) -> None:
        """Send sub-agent status update message."""
        update_msg = self.message_builder.create_sub_agent_update_message(sub_agent_name, state)
        await self.send_to_user(user_id, update_msg)

    def get_messaging_stats(self) -> Dict[str, Any]:
        """Get comprehensive messaging statistics."""
        queue_stats = self._get_all_queue_stats()
        return {
            "message_stats": self.message_processor.get_stats(),
            "queue_stats": queue_stats, "active_users": len(self.user_queues)
        }

    def _get_all_queue_stats(self) -> Dict[str, Any]:
        """Get statistics for all user queues."""
        total_stats = {"total_queued": 0, "total_failed": 0, "users_with_queues": 0}
        for user_id, queue in self.user_queues.items():
            stats = queue.get_stats()
            total_stats["total_queued"] += stats["total_queued"]
            total_stats["total_failed"] += stats["failed_queue_size"]
            if stats["total_queued"] > 0:
                total_stats["users_with_queues"] += 1
        return total_stats


# Re-export classes for backward compatibility
from .message_queue import MessageQueue
from .message_handlers import MessageHandler, MessageBuilder, MessageProcessor

__all__ = [
    "UnifiedMessagingManager", "MessageQueue", "MessageHandler", 
    "MessageBuilder", "MessageProcessor"
]