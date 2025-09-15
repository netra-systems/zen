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
import json
import threading
import time
import uuid
from collections import deque
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, field

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.connection_state_machine import (
    ApplicationConnectionState, ConnectionStateMachine, StateTransitionInfo
)
from shared.types.core_types import UserID, ConnectionID, ensure_user_id

# ISSUE #1011 REMEDIATION: Import Redis and Circuit Breaker for SSOT enhancement
try:
    from netra_backend.app.redis_manager import redis_manager
    REDIS_AVAILABLE = True
except ImportError:
    redis_manager = None
    REDIS_AVAILABLE = False

try:
    from netra_backend.app.core.circuit_breaker import (
        get_unified_circuit_breaker_manager,
        UnifiedCircuitConfig,
        CircuitBreakerOpenError
    )
    CIRCUIT_BREAKER_AVAILABLE = True
except ImportError:
    CIRCUIT_BREAKER_AVAILABLE = False

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
    # ISSUE #1011 REMEDIATION: Add states from Redis queue implementation
    RETRYING = "retrying"      # Processing retries with exponential backoff
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"  # Circuit breaker protection active
    DEAD_LETTER = "dead_letter"  # Messages moved to dead letter queue


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

    # ISSUE #1011 REMEDIATION: Add retry logic with exponential backoff from Redis implementation
    retry_count: int = 0
    max_retries: int = 5  # Increased from 3 to 5 for better resilience
    last_retry_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None
    backoff_multiplier: float = 2.0  # Exponential backoff: 1s, 2s, 4s, 8s, 16s
    base_retry_delay: int = 1  # seconds
    max_retry_delay: int = 60  # 1 minute max
    permanent_failure: bool = False
    circuit_breaker_failures: int = 0
    last_error_type: Optional[str] = None
    error_message: Optional[str] = None
    retry_history: List[datetime] = field(default_factory=list)
    
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

    # ISSUE #1011 REMEDIATION: Add retry logic methods from Redis implementation
    def calculate_next_retry_delay(self) -> int:
        """Calculate exponential backoff delay: 1s, 2s, 4s, 8s, 16s"""
        import random
        if self.retry_count == 0:
            return self.base_retry_delay

        # Exponential backoff
        base_delay = self.base_retry_delay * (self.backoff_multiplier ** (self.retry_count - 1))

        # Add jitter (0-40%) to prevent thundering herd
        delay_with_jitter = base_delay * (1 + 0.4 * random.random())

        # Apply max cap after jitter
        final_delay = min(delay_with_jitter, self.max_retry_delay)

        return max(1, int(final_delay))

    def should_retry(self) -> bool:
        """Check if message should be retried based on retry count and conditions"""
        if self.permanent_failure:
            return False
        if self.retry_count >= self.max_retries:
            return False
        return True

    def is_retry_ready(self) -> bool:
        """Check if message is ready for retry based on next_retry_at"""
        if not self.next_retry_at:
            return True
        return datetime.now(timezone.utc) >= self.next_retry_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis persistence"""
        return {
            "message_data": self.message_data,
            "message_type": self.message_type,
            "queued_at": self.queued_at.isoformat(),
            "priority": self.priority.value,
            "message_id": self.message_id,
            "user_id": self.user_id,
            "connection_id": self.connection_id,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "last_attempt": self.last_attempt.isoformat() if self.last_attempt else None,
            "queue_duration_ms": self.queue_duration_ms,
            "processing_started_at": self.processing_started_at.isoformat() if self.processing_started_at else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "last_retry_at": self.last_retry_at.isoformat() if self.last_retry_at else None,
            "next_retry_at": self.next_retry_at.isoformat() if self.next_retry_at else None,
            "backoff_multiplier": self.backoff_multiplier,
            "base_retry_delay": self.base_retry_delay,
            "max_retry_delay": self.max_retry_delay,
            "permanent_failure": self.permanent_failure,
            "circuit_breaker_failures": self.circuit_breaker_failures,
            "last_error_type": self.last_error_type,
            "error_message": self.error_message,
            "retry_history": [dt.isoformat() for dt in self.retry_history]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueuedMessage':
        """Create from dictionary for Redis persistence"""
        msg = cls(
            message_data=data.get("message_data", {}),
            message_type=data.get("message_type", ""),
            queued_at=datetime.fromisoformat(data.get("queued_at", datetime.now(timezone.utc).isoformat())),
            priority=MessagePriority(data.get("priority", "normal")),
            message_id=data.get("message_id"),
            user_id=data.get("user_id"),
            connection_id=data.get("connection_id"),
            attempts=data.get("attempts", 0),
            max_attempts=data.get("max_attempts", 3),
            last_attempt=datetime.fromisoformat(data["last_attempt"]) if data.get("last_attempt") else None,
            queue_duration_ms=data.get("queue_duration_ms"),
            processing_started_at=datetime.fromisoformat(data["processing_started_at"]) if data.get("processing_started_at") else None,
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 5),
            last_retry_at=datetime.fromisoformat(data["last_retry_at"]) if data.get("last_retry_at") else None,
            next_retry_at=datetime.fromisoformat(data["next_retry_at"]) if data.get("next_retry_at") else None,
            backoff_multiplier=data.get("backoff_multiplier", 2.0),
            base_retry_delay=data.get("base_retry_delay", 1),
            max_retry_delay=data.get("max_retry_delay", 60),
            permanent_failure=data.get("permanent_failure", False),
            circuit_breaker_failures=data.get("circuit_breaker_failures", 0),
            last_error_type=data.get("last_error_type"),
            error_message=data.get("error_message"),
            retry_history=[datetime.fromisoformat(dt) for dt in data.get("retry_history", [])]
        )
        return msg


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

        # ISSUE #1011 REMEDIATION: Add Redis persistence and circuit breaker support
        self.redis = redis_manager if REDIS_AVAILABLE else None
        self._redis_enabled = REDIS_AVAILABLE and redis_manager is not None
        self._circuit_breaker_enabled = CIRCUIT_BREAKER_AVAILABLE

        # Circuit breaker setup
        self.circuit_manager = None
        self.message_circuit = None
        self.redis_circuit = None

        if self._circuit_breaker_enabled:
            try:
                self.circuit_manager = get_unified_circuit_breaker_manager()
                self.message_circuit = self._setup_message_circuit_breaker()
                self.redis_circuit = self._setup_redis_circuit_breaker()
            except Exception as e:
                logger.warning(f"Failed to initialize circuit breakers for {self.connection_id}: {e}")
                self._circuit_breaker_enabled = False

        # Retry processing task
        self._retry_task: Optional[asyncio.Task] = None
        self._running = False

        # State change callback registration
        if self.state_machine:
            self.state_machine.add_state_change_callback(self._on_connection_state_change)

        logger.info(f"MessageQueue initialized for connection {self.connection_id}, user: {self.user_id} "
                   f"(Redis: {self._redis_enabled}, CircuitBreaker: {self._circuit_breaker_enabled})")

    def _setup_message_circuit_breaker(self):
        """Setup circuit breaker for message processing"""
        if not self._circuit_breaker_enabled:
            return None
        try:
            config = UnifiedCircuitConfig(
                name=f"websocket_message_processing_{self.connection_id}",
                failure_threshold=3,
                success_threshold=2,
                recovery_timeout=30,
                timeout_seconds=30.0
            )
            return self.circuit_manager.create_circuit_breaker(f"message_processing_{self.connection_id}", config)
        except Exception as e:
            logger.warning(f"Failed to create message circuit breaker: {e}")
            return None

    def _setup_redis_circuit_breaker(self):
        """Setup circuit breaker for Redis operations"""
        if not self._circuit_breaker_enabled:
            return None
        try:
            config = UnifiedCircuitConfig(
                name=f"websocket_redis_operations_{self.connection_id}",
                failure_threshold=5,
                success_threshold=3,
                recovery_timeout=60,
                timeout_seconds=10.0
            )
            return self.circuit_manager.create_circuit_breaker(f"redis_operations_{self.connection_id}", config)
        except Exception as e:
            logger.warning(f"Failed to create Redis circuit breaker: {e}")
            return None
    
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
                message_id=message_id or str(uuid.uuid4()),
                user_id=self.user_id,
                connection_id=self.connection_id
            )

            # ISSUE #1011 REMEDIATION: Add Redis persistence with circuit breaker protection
            redis_persisted = False
            if self._redis_enabled:
                try:
                    if self.redis_circuit and self.redis_circuit.can_execute():
                        redis_persisted = await self._persist_to_redis(queued_msg)
                    elif self.redis_circuit:
                        logger.debug(f"Redis circuit breaker open for {self.connection_id}")
                except CircuitBreakerOpenError:
                    logger.debug(f"Circuit breaker prevented Redis persistence for {self.connection_id}")
                except Exception as e:
                    logger.warning(f"Redis persistence failed for {self.connection_id}: {e}")

            # Add to appropriate priority queue (in-memory buffer)
            self._queues[priority].append(queued_msg)
            self._metrics["messages_queued"] += 1

            # Update peak size metric
            new_size = self._get_total_queue_size()
            if new_size > self._metrics["peak_queue_size"]:
                self._metrics["peak_queue_size"] = new_size

            logger.debug(f"Queued {priority.value} message for {self.connection_id} "
                        f"(queue size: {new_size}, Redis: {'✓' if redis_persisted else '✗'})")
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

                                    # ISSUE #1011 REMEDIATION: Enhanced retry logic with exponential backoff and DLQ
                                    if queued_msg.should_retry():
                                        # Schedule for retry with exponential backoff
                                        await self._schedule_retry(queued_msg, str(e))
                                        logger.debug(f"Scheduled retry for message {queued_msg.message_id} "
                                                   f"(attempt {queued_msg.retry_count}/{queued_msg.max_retries})")
                                    else:
                                        # Move to dead letter queue
                                        await self._move_to_dead_letter_queue(queued_msg, str(e))
                                        logger.error(f"Message {queued_msg.message_id} moved to DLQ after exhausting retries")

                                    # Record failure in circuit breaker if available
                                    if self.message_circuit:
                                        self.message_circuit.record_failure(type(e).__name__)
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
                    # ISSUE #1011 REMEDIATION: Start retry processor when entering operational mode
                    await self.start_retry_processor()
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
        
        stats = {
            "connection_id": self.connection_id,
            "user_id": self.user_id,
            "state": self._state.value,
            "is_flushing": self._is_flushing,
            "total_size": self._get_total_queue_size(),
            "queue_sizes_by_priority": queue_sizes,
            "metrics": self._metrics.copy(),
            "max_size": self.max_size,
            "max_message_age_seconds": self.max_message_age_seconds,
            "uptime_seconds": time.time() - self._metrics["created_at"],
            "redis_enabled": self._redis_enabled,
            "circuit_breaker_enabled": self._circuit_breaker_enabled
        }
        return stats

    # ISSUE #1011 REMEDIATION: Add Redis persistence and retry handling methods
    def _get_redis_queue_key(self, priority: MessagePriority) -> str:
        """Get Redis key for a priority queue"""
        return f"message_queue:{self.connection_id}:{priority.value}"

    def _get_redis_retry_key(self, message_id: str) -> str:
        """Get Redis key for retry queue"""
        return f"retry:{self.connection_id}:{message_id}"

    def _get_redis_dlq_key(self, message_id: str) -> str:
        """Get Redis key for dead letter queue"""
        return f"dlq:{self.connection_id}:{message_id}"

    async def _persist_to_redis(self, message: QueuedMessage) -> bool:
        """Persist message to Redis if available"""
        if not self._redis_enabled or not self.redis:
            return False

        try:
            if self.redis_circuit and not self.redis_circuit.can_execute():
                logger.debug(f"Redis circuit breaker open for {self.connection_id}")
                return False

            redis_key = self._get_redis_queue_key(message.priority)
            message_data = json.dumps(message.to_dict())
            await self.redis.lpush(redis_key, message_data)

            if self.redis_circuit:
                self.redis_circuit.record_success()

            return True
        except Exception as e:
            logger.warning(f"Failed to persist message to Redis for {self.connection_id}: {e}")
            if self.redis_circuit:
                self.redis_circuit.record_failure(type(e).__name__)
            return False

    async def _schedule_retry(self, message: QueuedMessage, error: str) -> None:
        """Schedule message for retry with exponential backoff"""
        message.retry_count += 1
        message.error_message = error
        message.last_error_type = type(Exception(error)).__name__
        message.last_retry_at = datetime.now(timezone.utc)
        message.retry_history.append(message.last_retry_at)

        # Calculate next retry delay
        retry_delay = message.calculate_next_retry_delay()
        message.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=retry_delay)

        if self._redis_enabled and self.redis:
            try:
                retry_key = self._get_redis_retry_key(message.message_id or str(uuid.uuid4()))
                await self.redis.set(
                    retry_key,
                    json.dumps(message.to_dict()),
                    ex=retry_delay + 60  # Add buffer
                )
                logger.info(f"Scheduled retry for message in {retry_delay}s for {self.connection_id}")
            except Exception as e:
                logger.warning(f"Failed to schedule retry in Redis: {e}")

    async def _move_to_dead_letter_queue(self, message: QueuedMessage, final_error: str) -> None:
        """Move permanently failed message to Dead Letter Queue"""
        message.permanent_failure = True
        message.error_message = final_error

        if self._redis_enabled and self.redis:
            try:
                dlq_key = self._get_redis_dlq_key(message.message_id or str(uuid.uuid4()))
                dlq_data = {
                    **message.to_dict(),
                    "moved_to_dlq_at": datetime.now(timezone.utc).isoformat(),
                    "final_error": final_error,
                    "total_processing_time": (
                        datetime.now(timezone.utc) - message.queued_at
                    ).total_seconds()
                }

                # Store in DLQ with 7 day retention
                await self.redis.set(
                    dlq_key,
                    json.dumps(dlq_data),
                    ex=7 * 24 * 3600
                )

                # Add to DLQ index for easier querying
                dlq_index_key = f"dlq_index:{self.connection_id}"
                await self.redis.zadd(
                    dlq_index_key,
                    {message.message_id: datetime.now(timezone.utc).timestamp()}
                )

                logger.error(f"Message moved to Dead Letter Queue for {self.connection_id}: {final_error}")
            except Exception as e:
                logger.error(f"Failed to move message to DLQ: {e}")

    async def start_retry_processor(self) -> None:
        """Start background retry processor if not already running"""
        if self._running or not self._redis_enabled:
            return

        self._running = True
        if not self._retry_task or self._retry_task.done():
            self._retry_task = asyncio.create_task(self._retry_processor_loop())
            logger.info(f"Started retry processor for {self.connection_id}")

    async def stop_retry_processor(self) -> None:
        """Stop background retry processor"""
        self._running = False
        if self._retry_task and not self._retry_task.done():
            self._retry_task.cancel()
            try:
                await self._retry_task
            except asyncio.CancelledError:
                pass
            logger.info(f"Stopped retry processor for {self.connection_id}")

    async def _retry_processor_loop(self) -> None:
        """Background loop to process retries"""
        while self._running:
            try:
                await self._process_retry_messages()
                await asyncio.sleep(30)  # Check every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in retry processor for {self.connection_id}: {e}")
                await asyncio.sleep(5)

    async def _process_retry_messages(self) -> None:
        """Process messages ready for retry"""
        if not self._redis_enabled or not self.redis:
            return

        try:
            pattern = f"retry:{self.connection_id}:*"
            keys = await self.redis.keys(pattern)

            for key in keys:
                try:
                    message_data = await self.redis.get(key)
                    if message_data:
                        message = QueuedMessage.from_dict(json.loads(message_data))
                        if message.is_retry_ready():
                            await self.redis.delete(key)
                            # Re-enqueue for processing
                            await self.enqueue_message(
                                message.message_data,
                                message.message_type,
                                message.priority,
                                message.message_id
                            )
                except Exception as e:
                    logger.warning(f"Error processing retry key {key}: {e}")
        except Exception as e:
            logger.error(f"Error processing retry messages: {e}")

    async def close(self):
        """Close the message queue and clean up resources."""
        async with self._lock:
            self._state = MessageQueueState.CLOSED

            # Stop retry processor
            await self.stop_retry_processor()

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