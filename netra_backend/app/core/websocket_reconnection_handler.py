"""WebSocket reconnection handling logic.

Provides automatic reconnection with exponential backoff,
state management, and recovery coordination.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Callable, List

from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.websocket_recovery_types import ReconnectionReason, ReconnectionConfig, MessageState

logger = central_logger.get_logger(__name__)


class WebSocketReconnectionHandler:
    """Handles WebSocket reconnection logic and state management."""
    
    def __init__(self, connection_id: str, config: ReconnectionConfig):
        """Initialize reconnection handler."""
        self.connection_id = connection_id
        self.config = config
        self.reconnect_attempts = 0
        self.last_reconnect_time: Optional[datetime] = None
        self.reconnect_task: Optional[asyncio.Task] = None
        self.on_reconnect_success: Optional[Callable] = None
        self.on_reconnect_failure: Optional[Callable] = None
    
    async def start_reconnection(self, reason: ReconnectionReason, connect_func: Callable) -> None:
        """Start reconnection process."""
        if self.reconnect_task and not self.reconnect_task.done():
            return
        self.reconnect_task = asyncio.create_task(
            self._reconnection_loop(reason, connect_func)
        )
    
    def cancel_reconnection(self) -> None:
        """Cancel ongoing reconnection."""
        if self.reconnect_task:
            self.reconnect_task.cancel()
    
    async def _reconnection_loop(self, reason: ReconnectionReason, connect_func: Callable) -> None:
        """Reconnection loop with exponential backoff."""
        logger.info(f"Starting reconnection: {self.connection_id} ({reason.value})")
        while self._should_continue_reconnecting():
            delay = self._calculate_reconnection_delay()
            logger.info(
                f"Reconnection attempt {self.reconnect_attempts + 1} "
                f"in {delay:.1f}s: {self.connection_id}"
            )
            await asyncio.sleep(delay)
            success = await self._execute_reconnection_attempt(connect_func)
            if success:
                logger.info(f"Reconnection successful: {self.connection_id}")
                if self.on_reconnect_success:
                    await self.on_reconnect_success()
                return
        logger.error(f"Reconnection failed after {self.reconnect_attempts} attempts: {self.connection_id}")
        if self.on_reconnect_failure:
            await self.on_reconnect_failure()
    
    def _should_continue_reconnecting(self) -> bool:
        """Check if reconnection should continue."""
        return self.reconnect_attempts < self.config.max_attempts
    
    def _calculate_reconnection_delay(self) -> float:
        """Calculate delay for next reconnection attempt."""
        delay = min(
            self.config.initial_delay * (
                self.config.backoff_multiplier ** self.reconnect_attempts
            ),
            self.config.max_delay
        )
        if self.config.jitter:
            delay = self._add_jitter_to_delay(delay)
        return delay
    
    def _add_jitter_to_delay(self, delay: float) -> float:
        """Add jitter to reconnection delay."""
        import random
        return delay * (0.5 + random.random() * 0.5)
    
    async def _execute_reconnection_attempt(self, connect_func: Callable) -> bool:
        """Execute a single reconnection attempt."""
        self.reconnect_attempts += 1
        self.last_reconnect_time = datetime.now()
        return await connect_func()
    
    def reset_attempts(self) -> None:
        """Reset reconnection attempt counter."""
        self.reconnect_attempts = 0
    
    def get_attempts(self) -> int:
        """Get current reconnection attempt count."""
        return self.reconnect_attempts
    
    def is_within_limits(self) -> bool:
        """Check if reconnection is within attempt limits."""
        return self.reconnect_attempts < self.config.max_attempts


class WebSocketMessageRestorer:
    """Handles message restoration after reconnection."""
    
    def __init__(self, config: ReconnectionConfig):
        """Initialize message restorer."""
        self.config = config
    
    async def restore_pending_messages(self, pending_messages: List[MessageState], send_func: Callable) -> None:
        """Restore pending messages after reconnection."""
        if not self.config.preserve_pending_messages:
            pending_messages.clear()
            return
        cleaned_messages = self._cleanup_old_pending_messages(pending_messages)
        await self._resend_pending_messages(cleaned_messages, send_func)
    
    def _cleanup_old_pending_messages(self, pending_messages: List[MessageState]) -> List[MessageState]:
        """Clean old pending messages based on retention policy."""
        cutoff_time = datetime.now() - timedelta(hours=self.config.message_retention_hours)
        return [msg for msg in pending_messages if msg.timestamp > cutoff_time]
    
    async def _resend_pending_messages(self, messages: List[MessageState], send_func: Callable) -> None:
        """Resend all pending messages."""
        for message_state in messages:
            await send_func(message_state)
        logger.info(f"Restored {len(messages)} pending messages")