"""WebSocket Batch Message Strategies.

Batching strategy implementations with micro-functions.
"""

import time
from typing import List

from netra_backend.app.batch_message_types import (
    BatchConfig,
    BatchingStrategy,
    PendingMessage,
)


class BatchingStrategyManager:
    """Manages batching strategies with micro-functions."""
    
    def __init__(self, config: BatchConfig, load_monitor):
        self.config = config
        self.load_monitor = load_monitor
    
    def should_flush_batch(self, pending: List[PendingMessage]) -> bool:
        """Determine if batch should be flushed based on strategy."""
        if not pending:
            return False
        return self._evaluate_strategy_condition(pending)


    def _evaluate_strategy_condition(self, pending: List[PendingMessage]) -> bool:
        """Evaluate flush condition based on current strategy."""
        strategy_checks = self._get_strategy_checks()
        check_function = strategy_checks.get(self.config.strategy)
        return check_function(pending) if check_function else False
    
    def _get_strategy_checks(self) -> dict:
        """Get mapping of strategy types to check functions."""
        return {
            BatchingStrategy.SIZE_BASED: self._check_size_based_flush,
            BatchingStrategy.TIME_BASED: self._check_time_based_flush,
            BatchingStrategy.PRIORITY: self._check_priority_based_flush,
            BatchingStrategy.ADAPTIVE: self._check_adaptive_flush
        }
    
    def _check_size_based_flush(self, pending: List[PendingMessage]) -> bool:
        """Check size-based flush condition."""
        return len(pending) >= self.config.max_batch_size
    
    def _check_time_based_flush(self, pending: List[PendingMessage]) -> bool:
        """Check time-based flush condition."""
        oldest_msg = min(pending, key=lambda m: m.timestamp)
        age = time.time() - oldest_msg.timestamp
        return age >= self.config.max_wait_time
    
    def _check_priority_based_flush(self, pending: List[PendingMessage]) -> bool:
        """Check priority-based flush condition."""
        high_priority_count = self._count_high_priority_messages(pending)
        priority_ready = self._has_priority_batch_ready(high_priority_count, pending)
        size_exceeded = self._exceeds_max_batch_size(pending)
        return priority_ready or size_exceeded
    
    def _count_high_priority_messages(self, pending: List[PendingMessage]) -> int:
        """Count high priority messages in batch."""
        return sum(1 for msg in pending if msg.priority >= self.config.priority_threshold)
    
    def _has_priority_batch_ready(self, high_priority_count: int, pending: List[PendingMessage]) -> bool:
        """Check if priority batch is ready for flush."""
        return high_priority_count > 0 and len(pending) >= self.config.adaptive_min_batch
    
    def _exceeds_max_batch_size(self, pending: List[PendingMessage]) -> bool:
        """Check if batch exceeds maximum size."""
        return len(pending) >= self.config.max_batch_size
    
    def _check_adaptive_flush(self, pending: List[PendingMessage]) -> bool:
        """Check adaptive flush condition."""
        size_ready = self._check_adaptive_size_condition(pending)
        time_ready = self._check_time_based_flush(pending)
        return size_ready or time_ready
    
    def _check_adaptive_size_condition(self, pending: List[PendingMessage]) -> bool:
        """Check adaptive size condition for flush."""
        current_load = self.load_monitor.get_current_load()
        dynamic_size = self._calculate_adaptive_batch_size(current_load)
        return len(pending) >= dynamic_size
    
    def _calculate_adaptive_batch_size(self, load: float) -> int:
        """Calculate adaptive batch size based on current load."""
        if load > 0.8:
            return self.config.adaptive_max_batch
        elif load > 0.5:
            return self._calculate_medium_load_batch_size()
        return self.config.adaptive_min_batch
    
    def _calculate_medium_load_batch_size(self) -> int:
        """Calculate batch size for medium load conditions."""
        return (self.config.adaptive_max_batch + self.config.adaptive_min_batch) // 2