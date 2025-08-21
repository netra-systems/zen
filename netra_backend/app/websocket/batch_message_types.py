"""WebSocket Batch Message Types and Data Models.

Core data structures for message batching system.
"""

import time
import json
from dataclasses import dataclass, field
from typing import Dict, Any, Union
from enum import Enum

from netra_backend.app.schemas.websocket_message_types import ServerMessage


class BatchingStrategy(Enum):
    """Message batching strategies."""
    TIME_BASED = "time_based"      # Batch by time interval
    SIZE_BASED = "size_based"      # Batch by message count
    ADAPTIVE = "adaptive"          # Adaptive batching based on load
    PRIORITY = "priority"          # Batch by message priority


class MessageState(Enum):
    """Message processing states for transactional reliability."""
    PENDING = "pending"    # Message queued, ready to send
    SENDING = "sending"    # Message being sent, don't remove from queue
    SENT = "sent"          # Message successfully sent, can be removed
    FAILED = "failed"      # Message failed to send, available for retry


@dataclass
class BatchConfig:
    """Configuration for message batching."""
    max_batch_size: int = 10
    max_wait_time: float = 0.1  # 100ms
    strategy: BatchingStrategy = BatchingStrategy.ADAPTIVE
    priority_threshold: int = 3
    adaptive_min_batch: int = 2
    adaptive_max_batch: int = 50


@dataclass
class PendingMessage:
    """Message pending in batch queue."""
    content: Union[Dict[str, Any], ServerMessage]
    connection_id: str
    user_id: str
    priority: int = 1
    timestamp: float = field(default_factory=time.time)
    size_bytes: int = 0
    state: MessageState = MessageState.PENDING
    retry_count: int = 0
    last_retry_time: float = 0.0
    max_retries: int = 3
    
    def __post_init__(self):
        if self.size_bytes == 0:
            self.size_bytes = len(json.dumps(self.content, default=str))


@dataclass
class BatchMetrics:
    """Metrics for batch processing."""
    total_batches: int = 0
    total_messages: int = 0
    avg_batch_size: float = 0.0
    avg_wait_time: float = 0.0
    compression_ratio: float = 0.0
    throughput_per_second: float = 0.0
    last_reset: float = field(default_factory=time.time)