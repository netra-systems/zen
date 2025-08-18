"""WebSocket Message Batch Container.

Single message batch container with flush logic.
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple

from app.schemas.registry import WebSocketMessage
from app.websocket.batch_message_config import BatchConfig, BatchedMessage


class MessageBatch:
    """Single message batch container."""
    
    def __init__(self, config: BatchConfig):
        self.config = config
        self.messages: List[BatchedMessage] = []
        self.created_at = datetime.now(timezone.utc)
        self.total_size_bytes = 0
        self.highest_priority = 0
    
    def add_message(self, message: WebSocketMessage, priority: int = 0) -> bool:
        """Add message to batch if it fits."""
        batched_msg = BatchedMessage(message=message, priority=priority)
        if not self._can_add_message(batched_msg):
            return False
        self._add_batched_message(batched_msg, priority)
        return True

    def _add_batched_message(self, batched_msg: BatchedMessage, priority: int) -> None:
        """Add batched message and update batch stats."""
        self.messages.append(batched_msg)
        self.total_size_bytes += batched_msg.size_bytes
        self.highest_priority = max(self.highest_priority, priority)
    
    def _can_add_message(self, message: BatchedMessage) -> bool:
        """Check if message can be added to batch."""
        if self._exceeds_size_limit():
            return False
        if self._exceeds_memory_limit(message):
            return False
        return True

    def _exceeds_size_limit(self) -> bool:
        """Check if batch size limit is exceeded."""
        return len(self.messages) >= self.config.max_batch_size

    def _exceeds_memory_limit(self, message: BatchedMessage) -> bool:
        """Check if memory limit would be exceeded."""
        new_total_size = self.total_size_bytes + message.size_bytes
        return new_total_size > self.config.max_batch_memory_kb * 1024
    
    def should_flush(self) -> tuple[bool, str]:
        """Check if batch should be flushed."""
        age_ms = self._calculate_batch_age_ms()
        flush_checks = self._get_flush_checks(age_ms)
        return next(((True, reason) for should_flush, reason in flush_checks if should_flush), (False, ""))

    def _get_flush_checks(self, age_ms: float) -> List[Tuple[bool, str]]:
        """Get list of flush condition checks."""
        return [
            (self._should_flush_by_time(age_ms), "time_limit"),
            (self._should_flush_by_size(), "size_limit"),
            (self._should_flush_by_memory(), "memory_limit"),
            (self._should_flush_by_priority(), "high_priority")
        ]

    def _calculate_batch_age_ms(self) -> float:
        """Calculate batch age in milliseconds."""
        now = datetime.now(timezone.utc)
        return (now - self.created_at).total_seconds() * 1000

    def _should_flush_by_time(self, age_ms: float) -> bool:
        """Check if batch should flush based on time."""
        return age_ms >= self.config.max_wait_time_ms

    def _should_flush_by_size(self) -> bool:
        """Check if batch should flush based on size."""
        return len(self.messages) >= self.config.max_batch_size

    def _should_flush_by_memory(self) -> bool:
        """Check if batch should flush based on memory usage."""
        return self.total_size_bytes >= self.config.max_batch_memory_kb * 1024

    def _should_flush_by_priority(self) -> bool:
        """Check if batch should flush based on priority."""
        return (self.config.flush_on_high_priority and 
               self.highest_priority >= self.config.priority_threshold)
    
    def is_empty(self) -> bool:
        """Check if batch is empty."""
        return len(self.messages) == 0
    
    def get_batch_data(self) -> Dict[str, Any]:
        """Get batch data for sending efficiently."""
        messages_data = self._prepare_messages_data()
        return self._create_batch_metadata(messages_data)

    def _prepare_messages_data(self) -> List[Dict[str, Any]]:
        """Prepare message data with caching."""
        messages_data = []
        for msg in self.messages:
            if msg._cached_data is None:
                msg._cached_data = msg.message.model_dump()
            messages_data.append(msg._cached_data)
        return messages_data

    def _create_batch_metadata(self, messages_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create batch metadata dictionary."""
        base_data = {"type": "batch", "count": len(self.messages), "messages": messages_data}
        additional_data = {"total_size_bytes": self.total_size_bytes, 
                          "highest_priority": self.highest_priority,
                          "created_at": self.created_at.isoformat()}
        return {**base_data, **additional_data}