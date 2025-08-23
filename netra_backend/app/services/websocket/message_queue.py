"""WebSocket Message Queue System

Implements a robust message queue with retry logic and error handling.
"""

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import redis_manager

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
    max_retries: int = 3
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    processing_started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    
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
    
    def register_handler(self, message_type: str, handler: Callable) -> None:
        """Register a handler for a specific message type"""
        self.handlers[message_type] = handler
        logger.info(f"Registered handler for message type: {message_type}")
    
    async def enqueue(self, message: QueuedMessage) -> bool:
        """Add message to the queue"""
        try:
            await self._add_message_to_redis_queue(message)
            await self._update_message_status(message.id, MessageStatus.PENDING)
            self._log_enqueue_success(message)
            return True
        except Exception as e:
            logger.error(f"Failed to enqueue message: {e}")
            return False

    async def _add_message_to_redis_queue(self, message: QueuedMessage) -> None:
        """Add message to Redis queue."""
        queue_key = self._get_queue_key(message.priority)
        message_data = json.dumps(message.to_dict())
        await self.redis.lpush(queue_key, message_data)

    def _log_enqueue_success(self, message: QueuedMessage) -> None:
        """Log successful message enqueue."""
        logger.info(f"Enqueued message {message.id} of type {message.type} with priority {message.priority.name}")
    
    async def process_queue(self, worker_count: int = 3) -> None:
        """Start processing messages from the queue"""
        if self._running:
            logger.warning("Queue processing already running")
            return
        await self._start_queue_processing(worker_count)

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
        """Stop processing messages"""
        self._running = False
        await self._cancel_all_workers()
        await self._wait_for_workers_completion()
        self._workers.clear()
        logger.info("Message queue processing stopped")
    
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
        """Handle a failed message"""
        message.error = error
        message.retry_count += 1
        if message.retry_count < message.max_retries:
            await self._handle_retry_message(message, error)
        else:
            await self._handle_permanent_failure(message, error)

    async def _handle_retry_message(self, message: QueuedMessage, error: str) -> None:
        """Handle message that can be retried."""
        message.status = MessageStatus.RETRYING
        await self._schedule_retry(message)
        logger.warning(f"Message {message.id} failed, scheduling retry {message.retry_count}/{message.max_retries}: {error}")

    async def _handle_permanent_failure(self, message: QueuedMessage, error: str) -> None:
        """Handle permanently failed message."""
        message.status = MessageStatus.FAILED
        await self._update_message_status(message.id, MessageStatus.FAILED, error)
        await self._send_failure_notification(message)
        logger.error(f"Message {message.id} permanently failed after {message.max_retries} retries: {error}")
    
    async def _schedule_retry(self, message: QueuedMessage) -> None:
        """Schedule a message for retry"""
        retry_at = datetime.now(UTC) + timedelta(seconds=self.retry_delay * message.retry_count)
        retry_key = f"retry:{message.id}"
        
        await self.redis.set(
            retry_key,
            json.dumps(message.to_dict()),
            ex=self.retry_delay * message.retry_count
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
        from netra_backend.app.websocket.unified import get_unified_manager
        manager = get_unified_manager()
        await manager.send_error(
            message.user_id,
            f"Message processing failed: {message.error}"
        )
    
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

message_queue = MessageQueue()