"""WebSocket Message Queue System

Implements a robust message queue with retry logic and error handling.
"""

import asyncio
import json
import random
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import redis_manager
from netra_backend.app.core.circuit_breaker import (
    get_unified_circuit_breaker_manager,
    UnifiedCircuitConfig,
    CircuitBreakerOpenError
)

logger = central_logger.get_logger(__name__)

class MessagePriority(Enum):
    """Message priority levels"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3

class MessageStatus(Enum):
    """Message processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    RECOVERABLE_FAILED = "recoverable_failed"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"
    DEAD_LETTER = "dead_letter"
    RETRY_EXHAUSTED = "retry_exhausted"

@dataclass
class QueuedMessage:
    """Represents a queued WebSocket message"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: MessagePriority = MessagePriority.NORMAL
    status: MessageStatus = MessageStatus.PENDING
    retry_count: int = 0
    max_retries: int = 5  # Increased from 3 to 5 for better resilience
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    processing_started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    
    # Enhanced retry attributes with exponential backoff
    last_retry_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None
    backoff_multiplier: float = 2.0  # Exponential backoff: 1s, 2s, 4s, 8s, 16s
    base_retry_delay: int = 1  # seconds
    max_retry_delay: int = 60  # 1 minute max
    recovery_attempts: int = 0
    max_recovery_attempts: int = 10
    permanent_failure: bool = False
    circuit_breaker_failures: int = 0
    last_error_type: Optional[str] = None
    retry_history: List[datetime] = field(default_factory=list)
    
    def calculate_next_retry_delay(self) -> int:
        """Calculate exponential backoff delay: 1s, 2s, 4s, 8s, 16s"""
        if self.retry_count == 0:
            return self.base_retry_delay
        
        # Exponential backoff
        base_delay = self.base_retry_delay * (self.backoff_multiplier ** (self.retry_count - 1))
        
        # Add jitter (0-40%) to prevent thundering herd
        # Only add positive jitter to avoid reducing delay below expected minimum
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
        if self.status in [MessageStatus.COMPLETED, MessageStatus.DEAD_LETTER]:
            return False
        return True
    
    def is_retry_ready(self) -> bool:
        """Check if message is ready for retry based on next_retry_at"""
        if not self.next_retry_at:
            return True
        return datetime.now(UTC) >= self.next_retry_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        base_data = self._get_base_dict_data()
        timestamp_data = self._get_timestamp_dict_data()
        return {**base_data, **timestamp_data, "error": self.error}

    def _get_base_dict_data(self) -> Dict[str, Any]:
        """Get basic dictionary data for serialization."""
        return {
            "id": self.id, "user_id": self.user_id, "type": self.type,
            "payload": self.payload, "priority": self.priority.value,
            "status": self.status.value, "retry_count": self.retry_count,
            "max_retries": self.max_retries
        }

    def _get_timestamp_dict_data(self) -> Dict[str, Any]:
        """Get timestamp data for serialization."""
        return {
            "created_at": self.created_at.isoformat(),
            "processing_started_at": self.processing_started_at.isoformat() if self.processing_started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueuedMessage':
        """Create from dictionary"""
        msg = cls()
        cls._set_basic_fields(msg, data)
        cls._set_timestamp_fields(msg, data)
        return msg

    @classmethod
    def _set_basic_fields(cls, msg: 'QueuedMessage', data: Dict[str, Any]) -> None:
        """Set basic message fields from dictionary data."""
        msg.id = data.get("id", str(uuid.uuid4()))
        msg.user_id = data.get("user_id", "")
        msg.type = data.get("type", "")
        msg.payload = data.get("payload", {})
        msg.priority = MessagePriority(data.get("priority", 1))
        msg.status = MessageStatus(data.get("status", "pending"))
        msg.retry_count = data.get("retry_count", 0)
        msg.max_retries = data.get("max_retries", 3)
        msg.error = data.get("error")

    @classmethod
    def _set_timestamp_fields(cls, msg: 'QueuedMessage', data: Dict[str, Any]) -> None:
        """Set timestamp fields from dictionary data."""
        msg.created_at = datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(UTC)
        msg.processing_started_at = datetime.fromisoformat(data["processing_started_at"]) if data.get("processing_started_at") else None
        msg.completed_at = datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None

class MessageQueue:
    """Manages WebSocket message queue with Redis backing"""
    
    def __init__(self):
        self.redis = redis_manager
        self.handlers: Dict[str, Callable] = {}
        self.processing_timeout = 30  # seconds
        self.retry_delay = 5  # seconds
        self._running = False
        self._workers: List[asyncio.Task] = []
        self._retry_task: Optional[asyncio.Task] = None
        
        # Circuit breaker setup
        self.circuit_manager = get_unified_circuit_breaker_manager()
        self.message_circuit = self._setup_message_circuit_breaker()
        self.redis_circuit = self._setup_redis_circuit_breaker()
    
    def _setup_message_circuit_breaker(self):
        """Setup circuit breaker for message processing"""
        config = UnifiedCircuitConfig(
            name="websocket_message_processing",
            failure_threshold=3,
            success_threshold=2,
            recovery_timeout=30,
            timeout_seconds=self.processing_timeout
        )
        return self.circuit_manager.create_circuit_breaker("message_processing", config)
    
    def _setup_redis_circuit_breaker(self):
        """Setup circuit breaker for Redis operations"""
        config = UnifiedCircuitConfig(
            name="websocket_redis_operations",
            failure_threshold=5,
            success_threshold=3,
            recovery_timeout=60,
            timeout_seconds=10.0
        )
        return self.circuit_manager.create_circuit_breaker("redis_operations", config)
    
    def register_handler(self, message_type: str, handler: Callable) -> None:
        """Register a handler for a specific message type"""
        self.handlers[message_type] = handler
        logger.info(f"Registered handler for message type: {message_type}")
    
    async def enqueue(self, message: QueuedMessage) -> bool:
        """Add message to the queue with circuit breaker protection"""
        try:
            # Use circuit breaker for Redis operations
            if not self.redis_circuit.can_execute():
                logger.warning(f"Redis circuit breaker is open, queueing message {message.id} for later")
                await self._queue_for_circuit_breaker_retry(message)
                return True
            
            await self._add_message_to_redis_queue_with_circuit_breaker(message)
            await self._update_message_status(message.id, MessageStatus.PENDING)
            self._log_enqueue_success(message)
            return True
        except CircuitBreakerOpenError:
            logger.warning(f"Circuit breaker prevented message enqueue for {message.id}")
            await self._queue_for_circuit_breaker_retry(message)
            return True
        except Exception as e:
            logger.error(f"Failed to enqueue message {message.id}: {e}", extra={"message_id": message.id, "error_type": type(e).__name__})
            self.redis_circuit.record_failure(type(e).__name__)
            return False
    
    async def _add_message_to_redis_queue_with_circuit_breaker(self, message: QueuedMessage) -> None:
        """Add message to Redis queue with circuit breaker protection"""
        try:
            await self._add_message_to_redis_queue(message)
            self.redis_circuit.record_success()
        except Exception as e:
            self.redis_circuit.record_failure(type(e).__name__)
            raise
    
    async def _queue_for_circuit_breaker_retry(self, message: QueuedMessage) -> None:
        """Queue message for retry when circuit breaker is open"""
        message.status = MessageStatus.CIRCUIT_BREAKER_OPEN
        message.circuit_breaker_failures += 1
        message.next_retry_at = datetime.now(UTC) + timedelta(seconds=30)
        
        # Store in circuit breaker retry queue
        retry_key = f"circuit_breaker_retry:{message.id}"
        await self.redis.set(
            retry_key,
            json.dumps(message.to_dict()),
            ex=3600  # 1 hour expiry
        )
        
        logger.info(f"Message {message.id} queued for circuit breaker retry")

    async def _add_message_to_redis_queue(self, message: QueuedMessage) -> None:
        """Add message to Redis queue."""
        queue_key = self._get_queue_key(message.priority)
        message_data = json.dumps(message.to_dict())
        await self.redis.lpush(queue_key, message_data)

    def _log_enqueue_success(self, message: QueuedMessage) -> None:
        """Log successful message enqueue."""
        logger.info(f"Enqueued message {message.id} of type {message.type} with priority {message.priority.name}")
    
    async def process_queue(self, worker_count: int = 3) -> None:
        """Start processing messages from the queue with retry task"""
        if self._running:
            logger.warning("Queue processing already running")
            return
        await self._start_queue_processing(worker_count)
        
        # Start background retry task
        if not self._retry_task or self._retry_task.done():
            self._retry_task = asyncio.create_task(self._background_retry_processor())
            logger.info("Started background retry processor")

    async def _start_queue_processing(self, worker_count: int) -> None:
        """Start queue processing with workers."""
        self._running = True
        logger.info(f"Starting message queue processing with {worker_count} workers")
        self._create_workers(worker_count)
        await self._run_workers_until_completion()

    def _create_workers(self, worker_count: int) -> None:
        """Create worker tasks for queue processing."""
        for i in range(worker_count):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)

    async def _run_workers_until_completion(self) -> None:
        """Run workers until completion or cancellation."""
        try:
            await asyncio.gather(*self._workers)
        except asyncio.CancelledError:
            logger.info("Queue processing cancelled")
        finally:
            self._running = False
    
    async def stop_processing(self) -> None:
        """Stop processing messages and retry task"""
        self._running = False
        
        # Cancel workers
        await self._cancel_all_workers()
        await self._wait_for_workers_completion()
        self._workers.clear()
        
        # Cancel retry task
        if self._retry_task and not self._retry_task.done():
            self._retry_task.cancel()
            try:
                await self._retry_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Message queue processing and retry task stopped")
    
    async def _cancel_all_workers(self) -> None:
        """Cancel all worker tasks."""
        for worker in self._workers:
            worker.cancel()
    
    async def _wait_for_workers_completion(self) -> None:
        """Wait for all workers to complete or be cancelled."""
        await asyncio.gather(*self._workers, return_exceptions=True)
    
    async def _worker(self, worker_id: int) -> None:
        """Worker coroutine to process messages"""
        logger.info(f"Worker {worker_id} started")
        await self._run_worker_loop(worker_id)
        logger.info(f"Worker {worker_id} stopped")

    async def _run_worker_loop(self, worker_id: int) -> None:
        """Run the main worker processing loop."""
        while self._running:
            await self._worker_iteration(worker_id)

    async def _worker_iteration(self, worker_id: int) -> None:
        """Execute one iteration of worker processing."""
        try:
            message = await self._get_next_message()
            await self._handle_worker_message(message)
        except Exception as e:
            logger.error(f"Worker {worker_id} error: {e}")
            await asyncio.sleep(1)

    async def _handle_worker_message(self, message: Optional[QueuedMessage]) -> None:
        """Handle message processing or idle state."""
        if message:
            await self._process_message(message)
        else:
            await asyncio.sleep(0.1)
    
    async def _get_next_message(self) -> Optional[QueuedMessage]:
        """Get the next message from the queue"""
        try:
            priority_message = await self._get_priority_message()
            if priority_message:
                return priority_message
            return await self._get_retry_message()
        except Exception as e:
            logger.error(f"Error getting next message: {e}")
            return None

    async def _get_priority_message(self) -> Optional[QueuedMessage]:
        """Get message from priority queues."""
        priority_order = self._get_priority_order()
        return await self._check_priority_queues(priority_order)
    
    def _get_priority_order(self) -> List[MessagePriority]:
        """Get ordered list of message priorities."""
        return [MessagePriority.CRITICAL, MessagePriority.HIGH, 
                MessagePriority.NORMAL, MessagePriority.LOW]
    
    async def _check_priority_queues(self, priorities: List[MessagePriority]) -> Optional[QueuedMessage]:
        """Check priority queues for available messages."""
        for priority in priorities:
            message = await self._get_message_from_priority_queue(priority)
            if message:
                return message
        return None
    
    async def _get_message_from_priority_queue(self, priority: MessagePriority) -> Optional[QueuedMessage]:
        """Get message from specific priority queue."""
        queue_key = self._get_queue_key(priority)
        message_data = await self.redis.rpop(queue_key)
        return QueuedMessage.from_dict(json.loads(message_data)) if message_data else None

    async def _get_retry_message(self) -> Optional[QueuedMessage]:
        """Get first available retry message."""
        retry_messages = await self._get_retry_messages()
        return retry_messages[0] if retry_messages else None
    
    async def _process_message(self, message: QueuedMessage) -> None:
        """Process a single message"""
        try:
            await self._start_message_processing(message)
            await self._execute_message_handler(message)
            await self._complete_message_processing(message)
        except asyncio.TimeoutError:
            await self._handle_failed_message(message, "Processing timeout")
        except Exception as e:
            await self._handle_failed_message(message, str(e))

    async def _start_message_processing(self, message: QueuedMessage) -> None:
        """Initialize message processing state."""
        message.status = MessageStatus.PROCESSING
        message.processing_started_at = datetime.now(UTC)
        await self._update_message_status(message.id, MessageStatus.PROCESSING)

    async def _execute_message_handler(self, message: QueuedMessage) -> None:
        """Execute the appropriate handler for the message."""
        handler = self.handlers.get(message.type)
        if not handler:
            raise ValueError(f"No handler registered for message type: {message.type}")
        await asyncio.wait_for(
            handler(message.user_id, message.payload),
            timeout=self.processing_timeout
        )

    async def _complete_message_processing(self, message: QueuedMessage) -> None:
        """Mark message as completed."""
        message.status = MessageStatus.COMPLETED
        message.completed_at = datetime.now(UTC)
        await self._update_message_status(message.id, MessageStatus.COMPLETED)
        logger.info(f"Successfully processed message {message.id}")
    
    async def _handle_failed_message(self, message: QueuedMessage, error: str) -> None:
        """Handle a failed message with comprehensive retry and recovery logic"""
        message.error = error
        message.last_error_type = type(Exception(error)).__name__
        message.retry_count += 1
        message.retry_history.append(datetime.now(UTC))
        
        # Record failure in message processing circuit breaker
        self.message_circuit.record_failure(message.last_error_type)
        
        logger.error(
            f"Message {message.id} failed (attempt {message.retry_count}/{message.max_retries}): {error}",
            extra={
                "message_id": message.id,
                "message_type": message.type,
                "retry_count": message.retry_count,
                "max_retries": message.max_retries,
                "error_type": message.last_error_type,
                "user_id": message.user_id
            }
        )
        
        if message.should_retry():
            await self._handle_retry_message(message, error)
        else:
            await self._handle_retry_exhausted(message, error)

    async def _handle_retry_message(self, message: QueuedMessage, error: str) -> None:
        """Handle message that can be retried with exponential backoff"""
        message.status = MessageStatus.RETRYING
        message.last_retry_at = datetime.now(UTC)
        
        # Calculate exponential backoff delay
        retry_delay_seconds = message.calculate_next_retry_delay()
        message.next_retry_at = datetime.now(UTC) + timedelta(seconds=retry_delay_seconds)
        
        await self._schedule_retry_with_backoff(message, retry_delay_seconds)
        
        logger.warning(
            f"Message {message.id} failed, scheduling retry {message.retry_count}/{message.max_retries} "
            f"in {retry_delay_seconds}s: {error}",
            extra={
                "message_id": message.id,
                "retry_delay": retry_delay_seconds,
                "next_retry_at": message.next_retry_at.isoformat(),
                "retry_count": message.retry_count,
                "error_type": message.last_error_type
            }
        )

    async def _handle_retry_exhausted(self, message: QueuedMessage, error: str) -> None:
        """Handle message that has exhausted all retries - move to Dead Letter Queue"""
        message.status = MessageStatus.RETRY_EXHAUSTED
        message.permanent_failure = True
        
        # Move to Dead Letter Queue for investigation
        await self._move_to_dead_letter_queue(message, error)
        
        # Send notification
        await self._send_failure_notification(message)
        
        logger.error(
            f"Message {message.id} retry exhausted after {message.max_retries} attempts, moved to DLQ: {error}",
            extra={
                "message_id": message.id,
                "message_type": message.type,
                "total_retries": message.max_retries,
                "user_id": message.user_id,
                "final_error": error,
                "retry_history_count": len(message.retry_history)
            }
        )
    
    async def _schedule_retry_with_backoff(self, message: QueuedMessage, delay_seconds: int) -> None:
        """Schedule a message for retry with exponential backoff"""
        retry_key = f"retry:{message.id}"
        
        # Store with expiration based on retry delay + buffer
        expiry_seconds = delay_seconds + 300  # 5 minute buffer
        
        await self.redis.set(
            retry_key,
            json.dumps(message.to_dict()),
            ex=expiry_seconds
        )
        
        await self._update_message_status(message.id, MessageStatus.RETRYING, message.error)
        
        logger.info(
            f"Scheduled retry for message {message.id} in {delay_seconds}s",
            extra={
                "message_id": message.id,
                "retry_delay": delay_seconds,
                "expiry_seconds": expiry_seconds
            }
        )
    
    async def _get_retry_messages(self) -> List[QueuedMessage]:
        """Get messages ready for retry"""
        try:
            return await self._collect_retry_messages()
        except Exception as e:
            logger.error(f"Error getting retry messages: {e}")
            return []
    
    async def _collect_retry_messages(self) -> List[QueuedMessage]:
        """Collect all available retry messages."""
        pattern = "retry:*"
        keys = await self.redis.keys(pattern)
        return await self._process_retry_keys(keys)
    
    async def _process_retry_keys(self, keys: List[str]) -> List[QueuedMessage]:
        """Process retry keys and extract messages."""
        retry_messages = []
        for key in keys:
            message = await self._extract_retry_message(key)
            if message:
                retry_messages.append(message)
        return retry_messages
    
    async def _extract_retry_message(self, key: str) -> Optional[QueuedMessage]:
        """Extract message from retry key."""
        message_data = await self.redis.get(key)
        if message_data:
            message = QueuedMessage.from_dict(json.loads(message_data))
            await self.redis.delete(key)
            return message
        return None
    
    async def _update_message_status(self, message_id: str, status: MessageStatus, error: Optional[str] = None) -> None:
        """Update message status in Redis"""
        status_key = f"message_status:{message_id}"
        status_data = self._build_status_data(status, error)
        await self.redis.set(status_key, json.dumps(status_data), ex=3600)
    
    def _build_status_data(self, status: MessageStatus, error: Optional[str]) -> Dict[str, Any]:
        """Build status data dictionary."""
        return {
            "status": status.value,
            "updated_at": datetime.now(UTC).isoformat(),
            "error": error
        }
    
    async def _send_failure_notification(self, message: QueuedMessage) -> None:
        """Send notification for permanently failed message"""
        try:
            await self._send_failure_message(message)
        except Exception as e:
            logger.error(f"Failed to send failure notification: {e}")
    
    async def _send_failure_message(self, message: QueuedMessage) -> None:
        """Send failure message to user."""
        try:
            from netra_backend.app.dependencies import get_user_execution_context
            from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
            
            # Use session-based context to maintain conversation continuity
            user_context = get_user_execution_context(user_id=message.user_id)
            manager = create_websocket_manager(user_context)
            await manager.send_to_user({
                "type": "error",
                "message": f"Message processing failed: {message.error}"
            })
        except Exception as e:
            # Import at top level to avoid circular import during initialization
            from netra_backend.app.logging_config import central_logger
            logger = central_logger.get_logger(__name__)
            logger.error(f"Failed to send failure message to user {message.user_id}: {e}")
    
    def _get_queue_key(self, priority: MessagePriority) -> str:
        """Get Redis key for a priority queue"""
        return f"message_queue:{priority.name.lower()}"
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        stats = self._init_empty_stats()
        try:
            await self._populate_queue_statistics(stats)
        except Exception as e:
            logger.error(f"Error getting queue stats: {e}")
        return stats
    
    async def _populate_queue_statistics(self, stats: Dict[str, Any]) -> None:
        """Populate statistics with queue and status data."""
        await self._collect_queue_stats(stats)
        await self._collect_status_stats(stats)

    def _init_empty_stats(self) -> Dict[str, Any]:
        """Initialize empty statistics dictionary."""
        return {
            "queues": {}, "total_pending": 0,
            "processing": 0, "completed": 0, "failed": 0
        }

    async def _collect_queue_stats(self, stats: Dict[str, Any]) -> None:
        """Collect queue length statistics."""
        for priority in MessagePriority:
            queue_key = self._get_queue_key(priority)
            queue_length = await self.redis.llen(queue_key)
            stats["queues"][priority.name] = queue_length
            stats["total_pending"] += queue_length

    async def _collect_status_stats(self, stats: Dict[str, Any]) -> None:
        """Collect message status statistics."""
        pattern = "message_status:*"
        keys = await self.redis.keys(pattern)
        await self._process_all_status_keys(keys, stats)
    
    async def _process_all_status_keys(self, keys: List[str], stats: Dict[str, Any]) -> None:
        """Process all status keys for statistics."""
        for key in keys:
            await self._process_status_key(key, stats)

    async def _process_status_key(self, key: str, stats: Dict[str, Any]) -> None:
        """Process individual status key for statistics."""
        status_data = await self.redis.get(key)
        if status_data:
            status = json.loads(status_data)["status"]
            self._increment_status_count(stats, status)

    def _increment_status_count(self, stats: Dict[str, Any], status: str) -> None:
        """Increment count for specific status type."""
        if status in ["processing", "completed", "failed"]:
            stats[status] += 1

    async def _move_to_dead_letter_queue(self, message: QueuedMessage, error: str) -> None:
        """Move permanently failed message to Dead Letter Queue"""
        try:
            message.status = MessageStatus.DEAD_LETTER
            dlq_key = f"dlq:{message.id}"
            
            # Enhanced DLQ data with full context
            dlq_data = {
                **message.to_dict(),
                "moved_to_dlq_at": datetime.now(UTC).isoformat(),
                "final_error": error,
                "retry_history": [dt.isoformat() for dt in message.retry_history],
                "total_processing_time": (
                    datetime.now(UTC) - message.created_at
                ).total_seconds()
            }
            
            # Store in DLQ with longer retention (7 days)
            await self.redis.set(
                dlq_key,
                json.dumps(dlq_data),
                ex=7 * 24 * 3600  # 7 days
            )
            
            # Add to DLQ index for easier querying
            dlq_index_key = "dlq_index"
            await self.redis.zadd(
                dlq_index_key,
                {message.id: datetime.now(UTC).timestamp()}
            )
            
            await self._update_message_status(message.id, MessageStatus.DEAD_LETTER, error)
            
            logger.info(
                f"Message {message.id} moved to Dead Letter Queue",
                extra={
                    "message_id": message.id,
                    "message_type": message.type,
                    "user_id": message.user_id,
                    "total_retries": message.retry_count,
                    "dlq_key": dlq_key
                }
            )
            
        except Exception as e:
            logger.error(
                f"Failed to move message {message.id} to DLQ: {e}",
                extra={"message_id": message.id, "dlq_error": str(e)}
            )
    
    async def _background_retry_processor(self) -> None:
        """Background task to process failed messages for retry"""
        logger.info("Background retry processor started")
        
        while self._running:
            try:
                await self._process_retry_batch()
                await self._process_circuit_breaker_retries()
                
                # Sleep for 30 seconds before next cycle
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                logger.info("Background retry processor cancelled")
                break
            except Exception as e:
                logger.error(f"Background retry processor error: {e}")
                await asyncio.sleep(5)  # Short sleep on error
    
    async def _process_retry_batch(self) -> None:
        """Process a batch of messages ready for retry"""
        try:
            retry_messages = await self._get_ready_retry_messages()
            
            if not retry_messages:
                return
            
            logger.info(f"Processing {len(retry_messages)} messages ready for retry")
            
            for message in retry_messages:
                try:
                    if message.is_retry_ready():
                        await self._retry_message(message)
                    else:
                        # Put back if not ready yet
                        await self._reschedule_retry(message)
                        
                except Exception as e:
                    logger.error(
                        f"Error processing retry for message {message.id}: {e}",
                        extra={"message_id": message.id, "retry_error": str(e)}
                    )
                    
        except Exception as e:
            logger.error(f"Error in retry batch processing: {e}")
    
    async def _get_ready_retry_messages(self) -> List[QueuedMessage]:
        """Get messages that are ready for retry"""
        try:
            pattern = "retry:*"
            keys = await self.redis.keys(pattern)
            
            ready_messages = []
            for key in keys:
                try:
                    message_data = await self.redis.get(key)
                    if message_data:
                        message = QueuedMessage.from_dict(json.loads(message_data))
                        if message.is_retry_ready():
                            ready_messages.append(message)
                            # Remove from retry queue
                            await self.redis.delete(key)
                            
                except Exception as e:
                    logger.warning(f"Error processing retry key {key}: {e}")
                    
            return ready_messages
            
        except Exception as e:
            logger.error(f"Error getting ready retry messages: {e}")
            return []
    
    async def _retry_message(self, message: QueuedMessage) -> None:
        """Retry a failed message"""
        try:
            # Check if message circuit breaker allows execution
            if not self.message_circuit.can_execute():
                logger.warning(f"Message circuit breaker prevented retry for {message.id}")
                await self._reschedule_retry(message)
                return
            
            logger.info(
                f"Retrying message {message.id} (attempt {message.retry_count + 1})",
                extra={
                    "message_id": message.id,
                    "message_type": message.type,
                    "retry_attempt": message.retry_count + 1
                }
            )
            
            # Reset status to processing
            message.status = MessageStatus.PROCESSING
            message.processing_started_at = datetime.now(UTC)
            
            # Process the message
            await self._process_message(message)
            
        except Exception as e:
            logger.error(
                f"Retry failed for message {message.id}: {e}",
                extra={"message_id": message.id, "retry_error": str(e)}
            )
            await self._handle_failed_message(message, str(e))
    
    async def _reschedule_retry(self, message: QueuedMessage) -> None:
        """Reschedule message retry if not ready yet"""
        if message.next_retry_at:
            delay = (message.next_retry_at - datetime.now(UTC)).total_seconds()
            if delay > 0:
                retry_key = f"retry:{message.id}"
                await self.redis.set(
                    retry_key,
                    json.dumps(message.to_dict()),
                    ex=int(delay + 60)  # Add 1 minute buffer
                )
    
    async def _process_circuit_breaker_retries(self) -> None:
        """Process messages queued due to circuit breaker being open"""
        try:
            if not self.redis_circuit.can_execute():
                return  # Circuit still open
            
            pattern = "circuit_breaker_retry:*"
            keys = await self.redis.keys(pattern)
            
            for key in keys:
                try:
                    message_data = await self.redis.get(key)
                    if message_data:
                        message = QueuedMessage.from_dict(json.loads(message_data))
                        
                        # Try to enqueue normally now
                        if await self.enqueue(message):
                            await self.redis.delete(key)
                            logger.info(f"Circuit breaker retry successful for message {message.id}")
                            
                except Exception as e:
                    logger.warning(f"Error processing circuit breaker retry {key}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in circuit breaker retry processing: {e}")
    
    async def get_dead_letter_queue_messages(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get messages from Dead Letter Queue for investigation"""
        try:
            # Get message IDs from DLQ index (sorted by timestamp)
            dlq_index_key = "dlq_index"
            message_ids = await self.redis.zrange(dlq_index_key, 0, limit - 1, desc=True)
            
            dlq_messages = []
            for message_id in message_ids:
                dlq_key = f"dlq:{message_id.decode() if isinstance(message_id, bytes) else message_id}"
                message_data = await self.redis.get(dlq_key)
                
                if message_data:
                    dlq_messages.append(json.loads(message_data))
            
            return dlq_messages
            
        except Exception as e:
            logger.error(f"Error getting DLQ messages: {e}")
            return []
    
    async def reprocess_dead_letter_message(self, message_id: str) -> bool:
        """Reprocess a message from Dead Letter Queue"""
        try:
            dlq_key = f"dlq:{message_id}"
            message_data = await self.redis.get(dlq_key)
            
            if not message_data:
                logger.warning(f"Message {message_id} not found in DLQ")
                return False
            
            message_dict = json.loads(message_data)
            message = QueuedMessage.from_dict(message_dict)
            
            # Reset retry count and status
            message.retry_count = 0
            message.status = MessageStatus.PENDING
            message.permanent_failure = False
            message.next_retry_at = None
            
            # Remove from DLQ
            await self.redis.delete(dlq_key)
            await self.redis.zrem("dlq_index", message_id)
            
            # Re-enqueue
            success = await self.enqueue(message)
            
            if success:
                logger.info(f"Message {message_id} successfully reprocessed from DLQ")
            else:
                logger.error(f"Failed to reprocess message {message_id} from DLQ")
            
            return success
            
        except Exception as e:
            logger.error(f"Error reprocessing DLQ message {message_id}: {e}")
            return False

message_queue = MessageQueue()