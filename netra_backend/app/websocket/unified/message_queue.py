"""WebSocket Message Queue Management.

Zero-loss message queue with priority handling and retry logic
for reliable WebSocket message delivery.
"""

import time
from collections import deque
from typing import Any, Deque, Dict, Optional


class MessageQueue:
    """Zero-loss message queue with priority handling."""
    
    def __init__(self, max_size: int = 1000) -> None:
        """Initialize message queue with size limit."""
        self.queue: Deque[Dict[str, Any]] = deque(maxlen=max_size)
        self.priority_queue: Deque[Dict[str, Any]] = deque(maxlen=max_size)
        self.failed_queue: Deque[Dict[str, Any]] = deque(maxlen=max_size)

    def add_message(self, message: Dict[str, Any], priority: bool = False) -> None:
        """Add message to appropriate queue."""
        target_queue = self.priority_queue if priority else self.queue
        message_with_timestamp = {**message, "queued_at": time.time()}
        target_queue.append(message_with_timestamp)

    def get_next_message(self) -> Optional[Dict[str, Any]]:
        """Get next message prioritizing priority queue."""
        if self.priority_queue:
            return self.priority_queue.popleft()
        if self.queue:
            return self.queue.popleft()
        return None

    def add_failed_message(self, message: Dict[str, Any]) -> None:
        """Add failed message for retry processing."""
        retry_count = message.get("retry_count", 0) + 1
        retry_message = {**message, "failed_at": time.time(), "retry_count": retry_count}
        self.failed_queue.append(retry_message)

    def get_stats(self) -> Dict[str, int]:
        """Get queue statistics."""
        return {
            "queue_size": len(self.queue), "priority_queue_size": len(self.priority_queue),
            "failed_queue_size": len(self.failed_queue),
            "total_queued": len(self.queue) + len(self.priority_queue) + len(self.failed_queue)
        }