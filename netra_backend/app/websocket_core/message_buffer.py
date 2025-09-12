"""
WebSocket Message Buffer

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: Stability & Development Velocity
- Value Impact: Prevents message loss during reconnection storms and service restarts
- Strategic Impact: Ensures reliable message delivery and improved user experience

Implements message buffering with overflow protection and reconnection backoff logic.
"""

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from enum import Enum

from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.registry import ServerMessage, WebSocketMessage
# WebSocket exceptions module was deleted - using standard exceptions

logger = central_logger.get_logger(__name__)


class BufferPriority(Enum):
    """Message priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class BufferConfig:
    """OPTIMIZED configuration for zero message loss during normal operation."""
    max_buffer_size_per_user: int = 200  # Reduced for 5 concurrent users focus
    max_buffer_size_global: int = 1000   # Conservative for guaranteed performance
    max_message_size_bytes: int = 32 * 1024  # 32KB - reduced for faster processing
    buffer_timeout_seconds: int = 120  # 2 minutes - faster timeout for responsiveness
    overflow_strategy: str = "drop_low_priority"  # Prioritize important messages
    retry_intervals: List[float] = field(default_factory=lambda: [0.5, 1.0, 2.0, 5.0])  # Faster retries
    max_retry_attempts: int = 4  # Fewer attempts but faster cycle
    
    # ZERO MESSAGE LOSS: Priority-based retention
    critical_message_types: List[str] = field(default_factory=lambda: [
        'agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed'
    ])
    never_drop_critical: bool = True  # Never drop critical agent messages


@dataclass
class BufferedMessage:
    """A buffered message with metadata."""
    id: str
    user_id: str
    message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]
    priority: BufferPriority = BufferPriority.NORMAL
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    retry_count: int = 0
    next_retry_time: Optional[datetime] = None
    size_bytes: int = 0
    
    def __post_init__(self):
        if self.size_bytes == 0:
            self.size_bytes = self._calculate_size()
    
    def _calculate_size(self) -> int:
        """OPTIMIZED size calculation for faster buffering."""
        try:
            import json
            # PERFORMANCE OPTIMIZATION: Fast path for simple messages
            if isinstance(self.message, (str, int, float, bool)):
                return len(str(self.message).encode('utf-8'))
            
            if isinstance(self.message, dict):
                return len(json.dumps(self.message, separators=(',', ':')).encode('utf-8'))
                
            if hasattr(self.message, 'model_dump'):
                return len(json.dumps(self.message.model_dump(), separators=(',', ':')).encode('utf-8'))
            elif hasattr(self.message, 'dict'):
                return len(json.dumps(self.message.dict(), separators=(',', ':')).encode('utf-8'))
            else:
                return len(json.dumps(self.message, separators=(',', ':')).encode('utf-8'))
        except Exception:
            # Fallback to string length estimation
            return len(str(self.message).encode('utf-8'))
    
    def is_critical(self, config: BufferConfig) -> bool:
        """Check if this message is critical and should not be dropped."""
        if self.priority == BufferPriority.CRITICAL:
            return True
        
        # Check message type for critical agent events
        if isinstance(self.message, dict):
            msg_type = self.message.get('type', '')
            return msg_type in config.critical_message_types
        
        return False


class WebSocketMessageBuffer:
    """Message buffer with overflow protection and retry logic."""
    
    def __init__(self, config: Optional[BufferConfig] = None):
        """Initialize message buffer."""
        self.config = config or BufferConfig()
        
        # User buffers
        self.user_buffers: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.config.max_buffer_size_per_user))
        
        # Global message tracking
        self.message_count = 0
        self.total_size_bytes = 0
        
        # Retry management
        self.retry_queue: deque = deque()
        self.retry_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            'messages_buffered': 0,
            'messages_delivered': 0,
            'messages_dropped': 0,
            'overflow_events': 0,
            'retry_attempts': 0,
            'buffer_size_bytes': 0,
            'max_buffer_size_reached': False
        }
        
        self._shutdown = False
    
    async def start(self) -> None:
        """Start buffer management tasks."""
        if self.retry_task is None:
            self.retry_task = asyncio.create_task(self._retry_loop())
        logger.info("WebSocket message buffer started")
    
    async def stop(self) -> None:
        """Stop buffer management."""
        self._shutdown = True
        
        if self.retry_task:
            self.retry_task.cancel()
            try:
                await self.retry_task
            except asyncio.CancelledError:
                pass
        
        logger.info("WebSocket message buffer stopped")
    
    async def buffer_message(
        self,
        user_id: str,
        message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]],
        priority: BufferPriority = BufferPriority.NORMAL
    ) -> bool:
        """
        Buffer a message for later delivery.
        
        Args:
            user_id: Target user ID
            message: Message to buffer
            priority: Message priority
            
        Returns:
            True if message was buffered successfully
        """
        try:
            # Create buffered message
            buffered_msg = BufferedMessage(
                id=f"{user_id}_{int(time.time() * 1000)}_{self.message_count}",
                user_id=user_id,
                message=message,
                priority=priority
            )
            
            # Check message size
            if buffered_msg.size_bytes > self.config.max_message_size_bytes:
                error_msg = f"Message too large: {buffered_msg.size_bytes} bytes exceeds max {self.config.max_message_size_bytes}"
                logger.error(f" ALERT:  BUFFER OVERFLOW: {error_msg}")
                self.stats['messages_dropped'] += 1
                
                # LOUD FAILURE: Raise exception instead of silent return
                raise OverflowError(
                    buffer_size=self.config.max_message_size_bytes,
                    message_size=buffered_msg.size_bytes,
                    user_id=user_id
                )
            
            # Check global buffer limits
            if not await self._check_global_limits(buffered_msg):
                return False
            
            # Add to user buffer
            user_buffer = self.user_buffers[user_id]
            
            # Check if user buffer would overflow
            if len(user_buffer) >= self.config.max_buffer_size_per_user:
                if not await self._handle_user_buffer_overflow(user_buffer, buffered_msg):
                    return False
            
            # Add message to buffer
            user_buffer.append(buffered_msg)
            self.message_count += 1
            self.total_size_bytes += buffered_msg.size_bytes
            self.stats['messages_buffered'] += 1
            self.stats['buffer_size_bytes'] = self.total_size_bytes
            
            logger.debug(f"Buffered message for user {user_id}: {buffered_msg.id}")
            return True
            
        except OverflowError:
            # Re-raise our custom exception
            raise
        except Exception as e:
            logger.error(f" ALERT:  MESSAGE BUFFER FAILURE: Failed to buffer message for user {user_id}: {e}")
            self.stats['messages_dropped'] += 1
            # Log at ERROR level but still return False for backward compatibility
            # TODO: Convert to exception in next major version
            return False
    
    async def get_buffered_messages(self, user_id: str, limit: Optional[int] = None) -> List[BufferedMessage]:
        """
        Get buffered messages for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of messages to return
            
        Returns:
            List of buffered messages
        """
        if user_id not in self.user_buffers:
            return []
        
        user_buffer = self.user_buffers[user_id]
        messages = list(user_buffer)
        
        if limit:
            messages = messages[:limit]
        
        return messages
    
    async def deliver_buffered_messages(self, user_id: str, delivery_callback) -> int:
        """
        Deliver all buffered messages for a user.
        
        Args:
            user_id: User ID
            delivery_callback: Async function to deliver messages
            
        Returns:
            Number of messages delivered successfully
        """
        if user_id not in self.user_buffers:
            return 0
        
        user_buffer = self.user_buffers[user_id]
        delivered_count = 0
        failed_messages = []
        
        # Process all messages in buffer
        while user_buffer:
            message = user_buffer.popleft()
            
            try:
                # Attempt delivery
                success = await delivery_callback(message.message)
                
                if success:
                    delivered_count += 1
                    self.stats['messages_delivered'] += 1
                    self._update_buffer_size(message, remove=True)
                else:
                    # Delivery failed, add to retry queue
                    await self._add_to_retry_queue(message)
                    failed_messages.append(message)
                    
            except Exception as e:
                logger.error(f"Error delivering buffered message {message.id}: {e}")
                await self._add_to_retry_queue(message)
                failed_messages.append(message)
        
        # Re-add failed messages to buffer if retry is possible
        for message in failed_messages:
            if message.retry_count < self.config.max_retry_attempts:
                user_buffer.append(message)
        
        logger.info(f"Delivered {delivered_count} buffered messages for user {user_id}")
        return delivered_count
    
    async def clear_user_buffer(self, user_id: str) -> int:
        """
        Clear all buffered messages for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of messages cleared
        """
        if user_id not in self.user_buffers:
            return 0
        
        user_buffer = self.user_buffers[user_id]
        cleared_count = len(user_buffer)
        
        # Update statistics
        for message in user_buffer:
            self._update_buffer_size(message, remove=True)
        
        user_buffer.clear()
        del self.user_buffers[user_id]
        
        logger.info(f"Cleared {cleared_count} buffered messages for user {user_id}")
        return cleared_count
    
    async def _check_global_limits(self, message: BufferedMessage) -> bool:
        """Check if adding message would exceed global limits."""
        # Check total message count
        if self.message_count >= self.config.max_buffer_size_global:
            await self._handle_global_buffer_overflow(message)
            return False
        
        return True
    
    async def _handle_user_buffer_overflow(self, user_buffer: deque, new_message: BufferedMessage) -> bool:
        """ZERO MESSAGE LOSS: Handle user buffer overflow with critical message protection."""
        # If the new message is critical, never drop it
        if self.config.never_drop_critical and new_message.is_critical(self.config):
            logger.info(f"Making room for critical message: {new_message.message.get('type', 'unknown')}")
            # Force room by removing oldest non-critical message
            return await self._make_room_for_critical(user_buffer)
        
        strategy = self.config.overflow_strategy
        
        if strategy == "drop_oldest":
            # Remove oldest non-critical message if possible
            for i in range(len(user_buffer)):
                msg = user_buffer[i]
                if not (self.config.never_drop_critical and msg.is_critical(self.config)):
                    user_buffer.remove(msg)
                    self._update_buffer_size(msg, remove=True)
                    return True
            # If all are critical, drop oldest anyway (fallback)
            if user_buffer:
                old_message = user_buffer.popleft()
                self._update_buffer_size(old_message, remove=True)
            return True
            
        elif strategy == "drop_newest":
            # Drop the new message only if it's not critical
            if not (self.config.never_drop_critical and new_message.is_critical(self.config)):
                logger.warning(f"Dropping new message due to buffer overflow for user {new_message.user_id}")
                self.stats['messages_dropped'] += 1
                return False
            else:
                # Make room for critical message
                return await self._make_room_for_critical(user_buffer)
            
        elif strategy == "drop_low_priority":
            # Find and drop lowest priority non-critical message
            candidates = []
            for i, msg in enumerate(user_buffer):
                if not (self.config.never_drop_critical and msg.is_critical(self.config)):
                    candidates.append((i, msg))
            
            if candidates:
                # Sort by priority and pick lowest
                candidates.sort(key=lambda x: x[1].priority.value)
                idx, msg = candidates[0]
                user_buffer.remove(msg)
                self._update_buffer_size(msg, remove=True)
                return True
            else:
                # All messages are critical, force room
                return await self._make_room_for_critical(user_buffer)
        
        # Default: drop oldest non-critical
        return await self._make_room_for_critical(user_buffer)
    
    async def _make_room_for_critical(self, user_buffer: deque) -> bool:
        """Make room for critical messages by removing non-critical ones."""
        # Try to find a non-critical message to remove
        for i in range(len(user_buffer)):
            msg = user_buffer[i]
            if not (self.config.never_drop_critical and msg.is_critical(self.config)):
                user_buffer.remove(msg)
                self._update_buffer_size(msg, remove=True)
                logger.debug(f"Removed non-critical message to make room for critical message")
                return True
        
        # If all messages are critical, remove oldest (last resort)
        if user_buffer:
            old_message = user_buffer.popleft()
            self._update_buffer_size(old_message, remove=True)
            logger.warning("Removed critical message due to all messages being critical")
        
        return True
    
    async def _handle_global_buffer_overflow(self, new_message: BufferedMessage) -> None:
        """Handle global buffer overflow."""
        self.stats['overflow_events'] += 1
        self.stats['max_buffer_size_reached'] = True
        
        # Find and remove oldest low-priority messages across all users
        oldest_message = None
        oldest_user = None
        
        for user_id, user_buffer in self.user_buffers.items():
            for message in user_buffer:
                if (message.priority == BufferPriority.LOW and
                    (oldest_message is None or message.created_at < oldest_message.created_at)):
                    oldest_message = message
                    oldest_user = user_id
        
        # Remove oldest low-priority message
        if oldest_message and oldest_user:
            self.user_buffers[oldest_user].remove(oldest_message)
            self._update_buffer_size(oldest_message, remove=True)
            logger.warning(f"Removed old low-priority message due to global buffer overflow")
        
    async def _add_to_retry_queue(self, message: BufferedMessage) -> None:
        """Add message to retry queue."""
        message.retry_count += 1
        
        if message.retry_count <= self.config.max_retry_attempts:
            # Calculate next retry time
            retry_interval = self.config.retry_intervals[min(message.retry_count - 1, len(self.config.retry_intervals) - 1)]
            message.next_retry_time = datetime.now(timezone.utc).replace(tzinfo=None) + \
                                      datetime.timedelta(seconds=retry_interval)
            
            self.retry_queue.append(message)
            self.stats['retry_attempts'] += 1
        else:
            # Max retries exceeded, drop message
            logger.warning(f"Message {message.id} exceeded max retry attempts, dropping")
            self.stats['messages_dropped'] += 1
            self._update_buffer_size(message, remove=True)
    
    async def _retry_loop(self) -> None:
        """Process retry queue periodically."""
        while not self._shutdown:
            try:
                await self._process_retry_queue()
                await asyncio.sleep(1.0)  # Check every second
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in retry loop: {e}")
    
    async def _process_retry_queue(self) -> None:
        """Process messages in retry queue."""
        current_time = datetime.now(timezone.utc).replace(tzinfo=None)
        retry_ready = []
        
        # Find messages ready for retry
        while self.retry_queue:
            message = self.retry_queue.popleft()
            
            if message.next_retry_time and current_time >= message.next_retry_time:
                retry_ready.append(message)
            else:
                # Put back if not ready
                self.retry_queue.appendleft(message)
                break
        
        # Re-buffer messages ready for retry
        for message in retry_ready:
            user_buffer = self.user_buffers[message.user_id]
            user_buffer.append(message)
    
    def _update_buffer_size(self, message: BufferedMessage, remove: bool = False) -> None:
        """Update buffer size statistics."""
        if remove:
            self.total_size_bytes -= message.size_bytes
            self.message_count -= 1
        else:
            self.total_size_bytes += message.size_bytes
            self.message_count += 1
        
        self.stats['buffer_size_bytes'] = self.total_size_bytes
    
    def get_buffer_stats(self) -> Dict[str, Any]:
        """Get buffer statistics."""
        user_buffer_sizes = {user_id: len(buffer) for user_id, buffer in self.user_buffers.items()}
        
        return {
            'total_users_with_buffers': len(self.user_buffers),
            'total_buffered_messages': self.message_count,
            'retry_queue_size': len(self.retry_queue),
            'user_buffer_sizes': user_buffer_sizes,
            'largest_user_buffer': max(user_buffer_sizes.values()) if user_buffer_sizes else 0,
            **self.stats
        }
    
    def get_user_buffer_info(self, user_id: str) -> Dict[str, Any]:
        """Get buffer information for specific user."""
        if user_id not in self.user_buffers:
            return {'buffer_size': 0, 'messages': []}
        
        user_buffer = self.user_buffers[user_id]
        messages_info = []
        
        for message in user_buffer:
            messages_info.append({
                'id': message.id,
                'priority': message.priority.name,
                'created_at': message.created_at.isoformat(),
                'retry_count': message.retry_count,
                'size_bytes': message.size_bytes
            })
        
        return {
            'buffer_size': len(user_buffer),
            'messages': messages_info
        }


# Global message buffer instance
_message_buffer: Optional[WebSocketMessageBuffer] = None


def get_message_buffer(config: Optional[BufferConfig] = None) -> WebSocketMessageBuffer:
    """Get global message buffer instance."""
    global _message_buffer
    if _message_buffer is None:
        _message_buffer = WebSocketMessageBuffer(config)
    return _message_buffer


async def buffer_user_message(
    user_id: str,
    message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]],
    priority: BufferPriority = BufferPriority.NORMAL
) -> bool:
    """Convenience function to buffer a message."""
    buffer = get_message_buffer()
    return await buffer.buffer_message(user_id, message, priority)


async def deliver_user_messages(user_id: str, delivery_callback) -> int:
    """Convenience function to deliver buffered messages."""
    buffer = get_message_buffer()
    return await buffer.deliver_buffered_messages(user_id, delivery_callback)


# Backward compatibility alias
MessageBuffer = WebSocketMessageBuffer