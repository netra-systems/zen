"""WebSocket Message Batching Configuration.

Configuration classes and enums for message batching system.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional

from netra_backend.app.schemas.registry import WebSocketMessage


class BatchStrategy(str, Enum):
    """Batching strategy options."""
    TIME_BASED = "time_based"
    SIZE_BASED = "size_based"
    HYBRID = "hybrid"
    PRIORITY_BASED = "priority_based"


@dataclass
class BatchConfig:
    """Batching configuration."""
    strategy: BatchStrategy = BatchStrategy.HYBRID
    max_batch_size: int = 50
    max_wait_time_ms: int = 100
    max_batch_memory_kb: int = 500
    priority_threshold: int = 5
    flush_on_high_priority: bool = True


@dataclass
class BatchedMessage:
    """Container for batched message."""
    message: WebSocketMessage
    priority: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    size_bytes: int = 0
    _cached_data: Optional[Dict] = field(default=None, init=False)
    
    def __post_init__(self):
        """Calculate message size efficiently."""
        if self.size_bytes == 0:
            self.size_bytes = len(str(self.message)) * 2


@dataclass
class BatchMetrics:
    """Batch processing metrics."""
    total_batches_sent: int = 0
    total_messages_batched: int = 0
    average_batch_size: float = 0.0
    average_wait_time_ms: float = 0.0
    total_bytes_sent: int = 0
    forced_flushes: int = 0
    time_based_flushes: int = 0
    size_based_flushes: int = 0