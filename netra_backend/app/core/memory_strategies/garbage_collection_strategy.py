"""Garbage collection memory recovery strategy."""

import gc
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from app.core.memory_recovery_base import (
    MemoryPressureLevel,
    MemoryRecoveryStrategy,
    MemorySnapshot,
    RecoveryAction
)
from app.core.memory_recovery_utils import get_current_process_memory_mb
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class GarbageCollectionStrategy(MemoryRecoveryStrategy):
    """Strategy to trigger garbage collection."""
    
    def __init__(self, aggressive: bool = False):
        """Initialize GC strategy."""
        self.aggressive = aggressive
        self.last_gc_time: Optional[datetime] = None
        self.min_gc_interval = timedelta(seconds=30)
    
    async def can_apply(self, snapshot: MemorySnapshot) -> bool:
        """Check if GC should be triggered."""
        if self._is_gc_too_frequent():
            return False
        return self._should_gc_for_pressure_level(snapshot)
    
    def _is_gc_too_frequent(self) -> bool:
        """Check if GC was run too recently."""
        if not self.last_gc_time:
            return False
        time_since_gc = datetime.now() - self.last_gc_time
        return time_since_gc < self.min_gc_interval
    
    def _should_gc_for_pressure_level(self, snapshot: MemorySnapshot) -> bool:
        """Check if memory pressure justifies GC."""
        return snapshot.pressure_level != MemoryPressureLevel.LOW
    
    def _prepare_gc_execution(self) -> Tuple[datetime, float, Tuple[int, int, int]]:
        """Prepare for garbage collection execution."""
        start_time = datetime.now()
        initial_memory = get_current_process_memory_mb()
        before_counts = gc.get_count()
        return start_time, initial_memory, before_counts

    def _perform_garbage_collection(self) -> int:
        """Perform garbage collection based on strategy mode."""
        if self.aggressive:
            return sum(gc.collect(generation) for generation in range(3))
        return gc.collect()

    def _calculate_gc_results(self, start_time: datetime, initial_memory: float, 
                            before_counts: Tuple[int, int, int], collected: int) -> Tuple[Tuple[int, int, int], float, float]:
        """Calculate garbage collection results and metrics."""
        after_counts = gc.get_count()
        final_memory = get_current_process_memory_mb()
        memory_freed = initial_memory - final_memory
        duration = (datetime.now() - start_time).total_seconds()
        self.last_gc_time = datetime.now()
        return after_counts, memory_freed, duration

    def _build_gc_result_dict(self, collected: int, memory_freed: float, duration: float, 
                            before_counts: Tuple[int, int, int], after_counts: Tuple[int, int, int]) -> Dict[str, Any]:
        """Build the garbage collection result dictionary."""
        base_result = self._create_base_gc_result(collected, memory_freed, duration)
        gc_specific = self._create_gc_specific_data(before_counts, after_counts)
        return {**base_result, **gc_specific}
    
    def _create_base_gc_result(self, collected: int, memory_freed: float, duration: float) -> Dict[str, Any]:
        """Create base garbage collection result data."""
        return {
            'action': RecoveryAction.GARBAGE_COLLECT.value,
            'objects_collected': collected,
            'memory_freed_mb': memory_freed,
            'duration_seconds': duration,
            'aggressive': self.aggressive
        }
    
    def _create_gc_specific_data(self, before_counts: Tuple[int, int, int], after_counts: Tuple[int, int, int]) -> Dict[str, Any]:
        """Create GC-specific data for result."""
        return {
            'gc_counts_before': before_counts,
            'gc_counts_after': after_counts
        }

    async def execute(self, snapshot: MemorySnapshot) -> Dict[str, Any]:
        """Execute garbage collection."""
        start_time, initial_memory, before_counts = self._prepare_gc_execution()
        collected = self._perform_garbage_collection()
        after_counts, memory_freed, duration = self._calculate_gc_results(
            start_time, initial_memory, before_counts, collected)
        result = self._build_gc_result_dict(collected, memory_freed, duration, 
                                          before_counts, after_counts)
        logger.info(f"Garbage collection completed: {result}")
        return result
    
    def get_priority(self) -> int:
        """GC has high priority as it's safe and effective."""
        return 1