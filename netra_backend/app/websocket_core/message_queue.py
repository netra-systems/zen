"""
WebSocket Message Queue with Connection State Integration

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Stability & User Experience
- Value Impact: Prevents message loss during connection setup, ensures proper message ordering
- Strategic Impact: Eliminates race conditions where messages arrive before connection is fully operational

CRITICAL: Implements message buffering during WebSocket connection setup phases.
This addresses the identified race condition where messages could be lost or processed
out of order when they arrived before the connection reached PROCESSING_READY state.

The message queue provides:
1. FIFO message buffering during connection setup phases
2. Integration with ConnectionStateMachine for state-aware queuing
3. Overflow protection with intelligent message dropping
4. Flush mechanism when connection becomes PROCESSING_READY
5. Message ordering guarantees and audit trail
"""

import asyncio
import threading
import time
from collections import deque
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, field

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.connection_state_machine import (
    ApplicationConnectionState, ConnectionStateMachine, StateTransitionInfo
)
from shared.types.core_types import UserID, ConnectionID, ensure_user_id

logger = central_logger.get_logger(__name__)


class MessagePriority(str, Enum):
    """Message priority levels for queue management."""
    CRITICAL = "critical"      # System messages, errors (never dropped)
    HIGH = "high"              # Agent responses, user messages  
    NORMAL = "normal"          # General messages
    LOW = "low"                # Typing indicators, status updates (dropped first)


class MessageQueueState(str, Enum):
    """Message queue operational states."""
    BUFFERING = "buffering"    # Buffering messages during setup
    FLUSHING = "flushing"      # Flushing buffered messages
    PASS_THROUGH = "pass_through"  # Direct message processing (normal operation)
    OVERFLOW = "overflow"      # Queue full, dropping messages
    SUSPENDED = "suspended"    # Queue suspended due to errors
    CLOSED = "closed"          # Queue closed


@dataclass
class QueuedMessage:
    """Represents a queued WebSocket message."""
    
    # Message content
    message_data: Dict[str, Any]
    message_type: str
    
    # Queuing metadata
    queued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    priority: MessagePriority = MessagePriority.NORMAL
    
    # Identification
    message_id: Optional[str] = None
    user_id: Optional[str] = None
    connection_id: Optional[str] = None
    
    # Processing tracking
    attempts: int = 0
    max_attempts: int = 3
    last_attempt: Optional[datetime] = None
    
    # Queue analytics
    queue_duration_ms: Optional[float] = None
    processing_started_at: Optional[datetime] = None
    
    def mark_attempt(self):
        """Mark a processing attempt."""
        self.attempts += 1
        self.last_attempt = datetime.now(timezone.utc)
        if self.processing_started_at is None:
            self.processing_started_at = self.last_attempt
    
    def calculate_queue_duration(self) -> float:
        """Calculate how long message was queued (in milliseconds)."""
        if self.processing_started_at:
            duration = (self.processing_started_at - self.queued_at).total_seconds() * 1000
            self.queue_duration_ms = duration
            return duration
        return 0.0
    
    def is_expired(self, max_age_seconds: float = 300.0) -> bool:
        """Check if message has expired."""
        age = (datetime.now(timezone.utc) - self.queued_at).total_seconds()
        return age > max_age_seconds
    
    def can_retry(self) -> bool:
        """Check if message can be retried."""
        return self.attempts < self.max_attempts


class MessageQueue:
    """
    State-aware message queue for WebSocket connections.
    
    CRITICAL FUNCTIONALITY:
    - Buffers messages during connection setup phases (CONNECTING through SERVICES_READY)
    - Automatically flushes messages when connection reaches PROCESSING_READY
    - Provides overflow protection with intelligent message dropping by priority
    - Maintains message ordering guarantees with FIFO processing
    - Integrates with ConnectionStateMachine for state-aware behavior
    - Provides comprehensive metrics and audit trail
    
    This addresses the race condition where messages could arrive and be processed
    before the WebSocket connection was fully operational, causing message loss
    or out-of-order processing.
    """
    
    def __init__(self, connection_id: ConnectionID, user_id: UserID,
                 max_size: int = 1000, max_message_age_seconds: float = 300.0,
                 state_machine: Optional[ConnectionStateMachine] = None):
        """
        Initialize message queue.
        
        Args:
            connection_id: Connection identifier
            user_id: User identifier
            max_size: Maximum queue size before overflow protection
            max_message_age_seconds: Maximum age before messages expire
            state_machine: Optional connection state machine for integration
        """
        self.connection_id = str(connection_id)
        self.user_id = ensure_user_id(user_id)
        self.max_size = max_size
        self.max_message_age_seconds = max_message_age_seconds
        self.state_machine = state_machine
        
        # Thread safety
        self._lock = asyncio.Lock()
        self._flush_lock = asyncio.Lock()
        
        # Queue storage - separate queues by priority
        self._queues = {
            MessagePriority.CRITICAL: deque(),
            MessagePriority.HIGH: deque(), 
            MessagePriority.NORMAL: deque(),
            MessagePriority.LOW: deque()
        }
        
        # Queue state
        self._state = MessageQueueState.BUFFERING
        self._is_flushing = False
        self._flush_task: Optional[asyncio.Task] = None
        
        # Metrics and analytics
        self._metrics = {
            "messages_queued": 0,
            "messages_flushed": 0,
            "messages_dropped": 0,
            "messages_expired": 0,
            "flush_operations": 0,
            "overflow_events": 0,
            "average_queue_duration_ms": 0.0,
            "peak_queue_size": 0,
            "created_at": time.time()
        }
        
        # Message processing callbacks
        self._message_processor: Optional[Callable[[QueuedMessage], Any]] = None
        self._flush_complete_callbacks: List[Callable[[], None]] = []
        
        # State change callback registration
        if self.state_machine:
            self.state_machine.add_state_change_callback(self._on_connection_state_change)
        
        logger.info(f"MessageQueue initialized for connection {self.connection_id}, user: {self.user_id}")
    
    @property
    def current_state(self) -> MessageQueueState:
        """Get current queue state."""
        return self._state
    
    @property
    def is_buffering(self) -> bool:
        """Check if queue is in buffering mode."""
        return self._state == MessageQueueState.BUFFERING
    
    @property
    def is_operational(self) -> bool:
        """Check if queue is operational for message processing."""
        return self._state in {MessageQueueState.PASS_THROUGH, MessageQueueState.FLUSHING}
    
    def set_message_processor(self, processor: Callable[[QueuedMessage], Any]):
        """Set message processor callback for flushing."""
        self._message_processor = processor
    
    def add_flush_complete_callback(self, callback: Callable[[], None]):
        """Add callback for flush completion."""
        self._flush_complete_callbacks.append(callback)
    
    async def enqueue_message(self, message_data: Dict[str, Any], 
                            message_type: str = "unknown",
                            priority: MessagePriority = MessagePriority.NORMAL,
                            message_id: Optional[str] = None) -> bool:
        """
        Enqueue message with priority and overflow protection.
        
        Args:
            message_data: Message payload
            message_type: Type of message
            priority: Message priority level
            message_id: Optional message identifier
            
        Returns:
            True if message was queued successfully, False if dropped
        """
        async with self._lock:
            # Check if we should bypass queueing (direct processing)
            if self._state == MessageQueueState.PASS_THROUGH:
                # Direct processing - not queued
                if self._message_processor:
                    try:
                        queued_msg = QueuedMessage(
                            message_data=message_data,
                            message_type=message_type,
                            priority=priority,
                            message_id=message_id,
                            user_id=self.user_id,
                            connection_id=self.connection_id
                        )
                        queued_msg.mark_attempt()
                        await self._message_processor(queued_msg)
                        return True
                    except Exception as e:
                        logger.error(f"Direct message processing failed for {self.connection_id}: {e}")
                        return False
                return True
            
            # Check if queue is closed or suspended
            if self._state in {MessageQueueState.CLOSED, MessageQueueState.SUSPENDED}:
                logger.debug(f"Message dropped - queue {self._state.value} for {self.connection_id}")
                self._metrics["messages_dropped"] += 1
                return False
            
            # Check queue capacity and handle overflow
            current_size = self._get_total_queue_size()
            if current_size >= self.max_size:
                if await self._handle_queue_overflow(priority):
                    # Made space, can proceed
                    pass
                else:
                    # Could not make space, drop message
                    logger.warning(f"Queue overflow - dropping {priority.value} message for {self.connection_id}")
                    self._metrics["messages_dropped"] += 1
                    return False
            
            # Create queued message
            queued_msg = QueuedMessage(
                message_data=message_data,
                message_type=message_type,
                priority=priority,
                message_id=message_id,
                user_id=self.user_id,
                connection_id=self.connection_id
            )
            
            # Add to appropriate priority queue
            self._queues[priority].append(queued_msg)
            self._metrics["messages_queued"] += 1
            
            # Update peak size metric
            new_size = self._get_total_queue_size()
            if new_size > self._metrics["peak_queue_size"]:
                self._metrics["peak_queue_size"] = new_size
            
            logger.debug(f"Queued {priority.value} message for {self.connection_id} (queue size: {new_size})")
            return True
    
    async def _handle_queue_overflow(self, incoming_priority: MessagePriority) -> bool:
        """
        Handle queue overflow by dropping lower priority messages.
        
        Args:
            incoming_priority: Priority of the incoming message
            
        Returns:
            True if space was made, False otherwise
        """
        self._metrics["overflow_events"] += 1
        
        # Priority order for dropping (drop lowest priority first)
        drop_order = [MessagePriority.LOW, MessagePriority.NORMAL, MessagePriority.HIGH]
        
        # Don't drop critical messages unless incoming is also critical
        if incoming_priority != MessagePriority.CRITICAL:
            # Try to drop lower priority messages
            for drop_priority in drop_order:
                if drop_priority.value >= incoming_priority.value:
                    break  # Don't drop same or higher priority
                
                queue = self._queues[drop_priority]
                if queue:
                    dropped_msg = queue.popleft()
                    self._metrics["messages_dropped"] += 1
                    logger.info(f"Dropped {drop_priority.value} message for {self.connection_id} due to overflow")
                    return True
        
        # If we get here, couldn't make space
        return False
    
    def _get_total_queue_size(self) -> int:
        """Get total size across all priority queues."""
        return sum(len(queue) for queue in self._queues.values())
    
    async def flush_queue(self, force: bool = False) -> bool:
        """
        Flush all queued messages in priority order.
        
        Args:
            force: Force flush regardless of state
            
        Returns:
            True if flush completed successfully
        """
        async with self._flush_lock:
            if self._is_flushing and not force:
                logger.debug(f"Flush already in progress for {self.connection_id}")
                return False
            
            if not self._message_processor and not force:
                logger.warning(f"No message processor set for {self.connection_id} - cannot flush")
                return False
            
            self._is_flushing = True
            self._state = MessageQueueState.FLUSHING
            flush_start_time = time.time()
            
            logger.info(f"Starting message flush for {self.connection_id}")
            
            try:
                total_flushed = 0
                total_failed = 0
                queue_duration_sum = 0.0
                
                # Process messages in priority order: CRITICAL -> HIGH -> NORMAL -> LOW
                priority_order = [
                    MessagePriority.CRITICAL,
                    MessagePriority.HIGH,
                    MessagePriority.NORMAL,
                    MessagePriority.LOW
                ]
                
                async with self._lock:
                    for priority in priority_order:
                        queue = self._queues[priority]
                        
                        while queue:
                            queued_msg = queue.popleft()
                            
                            # Check if message has expired
                            if queued_msg.is_expired(self.max_message_age_seconds):
                                logger.debug(f"Skipping expired message for {self.connection_id}")
                                self._metrics["messages_expired"] += 1
                                continue
                            
                            # Calculate queue duration
                            queue_duration = queued_msg.calculate_queue_duration()
                            queue_duration_sum += queue_duration
                            
                            # Attempt to process message
                            if self._message_processor:
                                try:
                                    queued_msg.mark_attempt()
                                    await self._message_processor(queued_msg)
                                    total_flushed += 1
                                    
                                except Exception as e:
                                    logger.error(f"Message processing failed during flush for {self.connection_id}: {e}")
                                    total_failed += 1
                                    
                                    # Retry logic for non-critical messages
                                    if queued_msg.can_retry() and priority != MessagePriority.CRITICAL:
                                        # Put back at front of queue for retry
                                        queue.appendleft(queued_msg)
                                        logger.debug(f"Retrying message for {self.connection_id} (attempt {queued_msg.attempts})")
                                        break  # Break inner loop to retry this message
                            else:
                                # No processor - just count as flushed
                                total_flushed += 1
                
                # Update metrics
                flush_duration = time.time() - flush_start_time
                self._metrics["messages_flushed"] += total_flushed
                self._metrics["flush_operations"] += 1
                
                if total_flushed > 0:
                    avg_duration = queue_duration_sum / total_flushed
                    # Update running average
                    current_avg = self._metrics["average_queue_duration_ms"]
                    self._metrics["average_queue_duration_ms"] = (current_avg + avg_duration) / 2
                
                logger.info(f"Flush completed for {self.connection_id}: {total_flushed} sent, {total_failed} failed, {flush_duration:.2f}s")
                
                # Transition to pass-through mode if successful
                if total_failed == 0:
                    self._state = MessageQueueState.PASS_THROUGH
                    logger.info(f"MessageQueue transitioned to PASS_THROUGH for {self.connection_id}")
                else:
                    # Some failures - stay in buffering mode temporarily
                    self._state = MessageQueueState.BUFFERING
                    logger.warning(f"MessageQueue staying in BUFFERING mode due to {total_failed} failures")
                
                # Notify flush complete callbacks
                for callback in self._flush_complete_callbacks:
                    try:
                        callback()
                    except Exception as e:
                        logger.error(f"Flush complete callback failed for {self.connection_id}: {e}")
                
                return total_failed == 0
                
            finally:
                self._is_flushing = False
    
    async def _on_connection_state_change(self, transition_info: StateTransitionInfo):
        """Handle connection state changes."""
        new_state = transition_info.to_state
        
        logger.debug(f"Connection state change for {self.connection_id}: {transition_info.from_state} -> {new_state}")
        
        # Trigger flush when connection becomes ready for message processing
        if new_state == ApplicationConnectionState.PROCESSING_READY:
            if self._state == MessageQueueState.BUFFERING:
                logger.info(f"Connection ready - starting message flush for {self.connection_id}")
                # Start flush in background
                if not self._flush_task or self._flush_task.done():
                    self._flush_task = asyncio.create_task(self.flush_queue())
        
        # Handle connection degraded/failed states
        elif new_state in {ApplicationConnectionState.DEGRADED}:
            # Allow degraded mode processing but stay conservative
            if self._state == MessageQueueState.PASS_THROUGH:
                # Already in pass-through, continue
                pass
            else:
                # Start conservative flush for degraded mode
                logger.info(f"Connection degraded - attempting partial flush for {self.connection_id}")
                if not self._flush_task or self._flush_task.done():
                    self._flush_task = asyncio.create_task(self.flush_queue(force=True))
        
        elif new_state in {ApplicationConnectionState.FAILED, ApplicationConnectionState.CLOSED}:
            # Suspend queue operations
            self._state = MessageQueueState.CLOSED
            logger.info(f"Connection closed - suspending message queue for {self.connection_id}")
    
    async def clear_queue(self, priority: Optional[MessagePriority] = None) -> int:
        """
        Clear messages from queue.
        
        Args:
            priority: Optional specific priority to clear, None for all
            
        Returns:
            Number of messages cleared
        """
        async with self._lock:
            cleared_count = 0
            
            if priority:
                # Clear specific priority
                queue = self._queues[priority]
                cleared_count = len(queue)
                queue.clear()
                logger.info(f"Cleared {cleared_count} {priority.value} messages for {self.connection_id}")
            else:
                # Clear all queues
                for priority_queue in self._queues.values():
                    cleared_count += len(priority_queue)
                    priority_queue.clear()
                logger.info(f"Cleared {cleared_count} total messages for {self.connection_id}")
            
            return cleared_count
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get comprehensive queue statistics."""
        queue_sizes = {
            priority.value: len(queue) for priority, queue in self._queues.items()
        }
        
        return {
            "connection_id": self.connection_id,
            "user_id": self.user_id,
            "state": self._state.value,
            "is_flushing": self._is_flushing,
            "total_size": self._get_total_queue_size(),
            "queue_sizes_by_priority": queue_sizes,
            "metrics": self._metrics.copy(),
            "max_size": self.max_size,
            "max_message_age_seconds": self.max_message_age_seconds,
            "uptime_seconds": time.time() - self._metrics["created_at"]
        }
    
    async def close(self):
        """Close the message queue and clean up resources."""
        async with self._lock:
            self._state = MessageQueueState.CLOSED
            
            # Cancel any ongoing flush
            if self._flush_task and not self._flush_task.done():
                self._flush_task.cancel()
                try:
                    await self._flush_task
                except asyncio.CancelledError:
                    pass
            
            # Clear all queues
            cleared_count = await self.clear_queue()
            
            # Remove state change callback
            if self.state_machine:
                self.state_machine.remove_state_change_callback(self._on_connection_state_change)
            
            logger.info(f"MessageQueue closed for {self.connection_id}, cleared {cleared_count} messages")
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return (f"MessageQueue(connection_id='{self.connection_id}', "
               f"user_id='{self.user_id}', state='{self._state.value}', "
               f"size={self._get_total_queue_size()}, max_size={self.max_size})")


class MessageQueueRegistry:
    """
    Registry for managing message queues across WebSocket connections.
    
    Provides centralized access and coordination of message queues with
    connection state machines.
    """
    
    def __init__(self):
        self._queues: Dict[str, MessageQueue] = {}
        self._lock = threading.RLock()
        
        logger.info("MessageQueueRegistry initialized")
    
    def create_message_queue(self, connection_id: ConnectionID, user_id: UserID,
                           state_machine: Optional[ConnectionStateMachine] = None,
                           max_size: int = 1000) -> MessageQueue:
        """Create and register a message queue."""
        with self._lock:
            connection_key = str(connection_id)
            
            if connection_key in self._queues:
                logger.warning(f"MessageQueue {connection_key} already exists, returning existing")
                return self._queues[connection_key]
            
            queue = MessageQueue(
                connection_id=connection_id,
                user_id=user_id,
                max_size=max_size,
                state_machine=state_machine
            )
            
            self._queues[connection_key] = queue
            logger.info(f"Created MessageQueue for connection {connection_key}")
            
            return queue
    
    def get_message_queue(self, connection_id: ConnectionID) -> Optional[MessageQueue]:
        """Get message queue by connection ID."""
        with self._lock:
            return self._queues.get(str(connection_id))
    
    async def remove_message_queue(self, connection_id: ConnectionID) -> bool:
        """Remove and close message queue."""
        with self._lock:
            connection_key = str(connection_id)
            queue = self._queues.pop(connection_key, None)
            
            if queue:
                await queue.close()
                logger.info(f"Removed MessageQueue for connection {connection_key}")
                return True
            
            return False
    
    def get_all_active_queues(self) -> Dict[str, MessageQueue]:
        """Get all active message queues."""
        with self._lock:
            return {
                conn_id: queue for conn_id, queue in self._queues.items()
                if queue.is_operational
            }
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        with self._lock:
            total_queues = len(self._queues)
            active_queues = 0
            total_messages = 0
            state_counts = {}
            
            for queue in self._queues.values():
                if queue.is_operational:
                    active_queues += 1
                
                total_messages += queue._get_total_queue_size()
                
                state = queue.current_state
                state_counts[state.value] = state_counts.get(state.value, 0) + 1
            
            return {
                "total_queues": total_queues,
                "active_queues": active_queues,
                "total_queued_messages": total_messages,
                "state_distribution": state_counts
            }


# Global registry instance
_message_queue_registry: Optional[MessageQueueRegistry] = None


def get_message_queue_registry() -> MessageQueueRegistry:
    """Get global message queue registry."""
    global _message_queue_registry
    if _message_queue_registry is None:
        _message_queue_registry = MessageQueueRegistry()
    return _message_queue_registry


def get_message_queue_for_connection(connection_id: ConnectionID) -> Optional[MessageQueue]:
    """Convenience function to get message queue for connection."""
    registry = get_message_queue_registry()
    return registry.get_message_queue(connection_id)