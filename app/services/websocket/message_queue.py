"""WebSocket Message Queue System

Implements a robust message queue with retry logic and error handling.
"""

from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
import asyncio
import json
import uuid
from enum import Enum
from app.logging_config import central_logger
from app.redis_manager import redis_manager

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
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type,
            "payload": self.payload,
            "priority": self.priority.value,
            "status": self.status.value,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "created_at": self.created_at.isoformat(),
            "processing_started_at": self.processing_started_at.isoformat() if self.processing_started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueuedMessage':
        """Create from dictionary"""
        msg = cls()
        msg.id = data.get("id", str(uuid.uuid4()))
        msg.user_id = data.get("user_id", "")
        msg.type = data.get("type", "")
        msg.payload = data.get("payload", {})
        msg.priority = MessagePriority(data.get("priority", 1))
        msg.status = MessageStatus(data.get("status", "pending"))
        msg.retry_count = data.get("retry_count", 0)
        msg.max_retries = data.get("max_retries", 3)
        msg.created_at = datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(UTC)
        msg.processing_started_at = datetime.fromisoformat(data["processing_started_at"]) if data.get("processing_started_at") else None
        msg.completed_at = datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
        msg.error = data.get("error")
        return msg

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
            queue_key = self._get_queue_key(message.priority)
            message_data = json.dumps(message.to_dict())
            
            await self.redis.lpush(queue_key, message_data)
            
            await self._update_message_status(message.id, MessageStatus.PENDING)
            
            logger.info(f"Enqueued message {message.id} of type {message.type} with priority {message.priority.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enqueue message: {e}")
            return False
    
    async def process_queue(self, worker_count: int = 3) -> None:
        """Start processing messages from the queue"""
        if self._running:
            logger.warning("Queue processing already running")
            return
        
        self._running = True
        logger.info(f"Starting message queue processing with {worker_count} workers")
        
        for i in range(worker_count):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)
        
        try:
            await asyncio.gather(*self._workers)
        except asyncio.CancelledError:
            logger.info("Queue processing cancelled")
        finally:
            self._running = False
    
    async def stop_processing(self) -> None:
        """Stop processing messages"""
        self._running = False
        
        for worker in self._workers:
            worker.cancel()
        
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        
        logger.info("Message queue processing stopped")
    
    async def _worker(self, worker_id: int) -> None:
        """Worker coroutine to process messages"""
        logger.info(f"Worker {worker_id} started")
        
        while self._running:
            try:
                message = await self._get_next_message()
                
                if message:
                    await self._process_message(message)
                else:
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(1)
        
        logger.info(f"Worker {worker_id} stopped")
    
    async def _get_next_message(self) -> Optional[QueuedMessage]:
        """Get the next message from the queue"""
        try:
            for priority in [MessagePriority.CRITICAL, MessagePriority.HIGH, 
                           MessagePriority.NORMAL, MessagePriority.LOW]:
                queue_key = self._get_queue_key(priority)
                
                message_data = await self.redis.rpop(queue_key)
                if message_data:
                    return QueuedMessage.from_dict(json.loads(message_data))
            
            retry_messages = await self._get_retry_messages()
            return retry_messages[0] if retry_messages else None
            
        except Exception as e:
            logger.error(f"Error getting next message: {e}")
            return None
    
    async def _process_message(self, message: QueuedMessage) -> None:
        """Process a single message"""
        try:
            message.status = MessageStatus.PROCESSING
            message.processing_started_at = datetime.now(UTC)
            await self._update_message_status(message.id, MessageStatus.PROCESSING)
            
            handler = self.handlers.get(message.type)
            if not handler:
                raise ValueError(f"No handler registered for message type: {message.type}")
            
            await asyncio.wait_for(
                handler(message.user_id, message.payload),
                timeout=self.processing_timeout
            )
            
            message.status = MessageStatus.COMPLETED
            message.completed_at = datetime.now(UTC)
            await self._update_message_status(message.id, MessageStatus.COMPLETED)
            
            logger.info(f"Successfully processed message {message.id}")
            
        except asyncio.TimeoutError:
            await self._handle_failed_message(message, "Processing timeout")
        except Exception as e:
            await self._handle_failed_message(message, str(e))
    
    async def _handle_failed_message(self, message: QueuedMessage, error: str) -> None:
        """Handle a failed message"""
        message.error = error
        message.retry_count += 1
        
        if message.retry_count < message.max_retries:
            message.status = MessageStatus.RETRYING
            await self._schedule_retry(message)
            logger.warning(f"Message {message.id} failed, scheduling retry {message.retry_count}/{message.max_retries}: {error}")
        else:
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
        retry_messages = []
        
        try:
            pattern = "retry:*"
            keys = await self.redis.keys(pattern)
            
            for key in keys:
                message_data = await self.redis.get(key)
                if message_data:
                    message = QueuedMessage.from_dict(json.loads(message_data))
                    retry_messages.append(message)
                    await self.redis.delete(key)
            
        except Exception as e:
            logger.error(f"Error getting retry messages: {e}")
        
        return retry_messages
    
    async def _update_message_status(self, message_id: str, status: MessageStatus, error: Optional[str] = None) -> None:
        """Update message status in Redis"""
        status_key = f"message_status:{message_id}"
        status_data = {
            "status": status.value,
            "updated_at": datetime.now(UTC).isoformat(),
            "error": error
        }
        
        await self.redis.set(status_key, json.dumps(status_data), ex=3600)
    
    async def _send_failure_notification(self, message: QueuedMessage) -> None:
        """Send notification for permanently failed message"""
        from app.ws_manager import manager
        
        try:
            await manager.send_error(
                message.user_id,
                f"Message processing failed: {message.error}"
            )
        except Exception as e:
            logger.error(f"Failed to send failure notification: {e}")
    
    def _get_queue_key(self, priority: MessagePriority) -> str:
        """Get Redis key for a priority queue"""
        return f"message_queue:{priority.name.lower()}"
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        stats = {
            "queues": {},
            "total_pending": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0
        }
        
        try:
            for priority in MessagePriority:
                queue_key = self._get_queue_key(priority)
                queue_length = await self.redis.llen(queue_key)
                stats["queues"][priority.name] = queue_length
                stats["total_pending"] += queue_length
            
            pattern = "message_status:*"
            keys = await self.redis.keys(pattern)
            
            for key in keys:
                status_data = await self.redis.get(key)
                if status_data:
                    status = json.loads(status_data)["status"]
                    if status == "processing":
                        stats["processing"] += 1
                    elif status == "completed":
                        stats["completed"] += 1
                    elif status == "failed":
                        stats["failed"] += 1
            
        except Exception as e:
            logger.error(f"Error getting queue stats: {e}")
        
        return stats

message_queue = MessageQueue()