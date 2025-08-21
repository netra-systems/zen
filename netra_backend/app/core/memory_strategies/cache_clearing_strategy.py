"""Cache clearing memory recovery strategy."""

import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.core.memory_recovery_base import (
    MemoryPressureLevel,
    MemoryRecoveryStrategy,
    MemorySnapshot,
    RecoveryAction
)
from app.core.memory_recovery_utils import get_current_process_memory_mb
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class CacheClearingStrategy(MemoryRecoveryStrategy):
    """Strategy to clear various caches."""
    
    def __init__(self, cache_managers: List[Any]):
        """Initialize with cache managers."""
        self.cache_managers = cache_managers
        self.last_clear_time: Optional[datetime] = None
        self.min_clear_interval = timedelta(minutes=5)
    
    async def can_apply(self, snapshot: MemorySnapshot) -> bool:
        """Check if cache clearing should be applied."""
        if self._is_clear_too_frequent():
            return False
        return self._should_clear_for_pressure(snapshot)
    
    def _is_clear_too_frequent(self) -> bool:
        """Check if cache was cleared too recently."""
        if not self.last_clear_time:
            return False
        time_since_clear = datetime.now() - self.last_clear_time
        return time_since_clear < self.min_clear_interval
    
    def _should_clear_for_pressure(self, snapshot: MemorySnapshot) -> bool:
        """Check if memory pressure justifies cache clearing."""
        return snapshot.pressure_level in [
            MemoryPressureLevel.HIGH,
            MemoryPressureLevel.CRITICAL,
            MemoryPressureLevel.EMERGENCY
        ]
    
    async def execute(self, snapshot: MemorySnapshot) -> Dict[str, Any]:
        """Execute cache clearing."""
        start_time = datetime.now()
        initial_memory = get_current_process_memory_mb()
        cleared_count, errors = await self._clear_all_caches()
        self._clear_python_internal_caches()
        return self._build_cache_clear_result(start_time, initial_memory, cleared_count, errors)
    
    async def _clear_all_caches(self) -> Tuple[int, List[str]]:
        """Clear all managed caches."""
        cleared_count = 0
        errors = []
        for cache_manager in self.cache_managers:
            cache_result = await self._clear_single_cache(cache_manager)
            if cache_result['success']:
                cleared_count += 1
            else:
                errors.append(cache_result['error'])
        return cleared_count, errors
    
    async def _clear_single_cache(self, cache_manager: Any) -> Dict[str, Any]:
        """Clear a single cache manager."""
        try:
            if hasattr(cache_manager, 'clear_all'):
                await cache_manager.clear_all()
                return {'success': True}
            elif hasattr(cache_manager, 'clear'):
                cache_manager.clear()
                return {'success': True}
            return {'success': False, 'error': 'No clear method found'}
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Failed to clear cache {type(cache_manager).__name__}: {e}")
            return {'success': False, 'error': error_msg}
    
    def _clear_python_internal_caches(self) -> None:
        """Clear Python's internal caches."""
        if hasattr(sys, '_clear_type_cache'):
            sys._clear_type_cache()
    
    def _build_cache_clear_result(self, start_time: datetime, initial_memory: float, 
                                 cleared_count: int, errors: List[str]) -> Dict[str, Any]:
        """Build cache clearing result dictionary."""
        final_memory = get_current_process_memory_mb()
        memory_freed = initial_memory - final_memory
        duration = (datetime.now() - start_time).total_seconds()
        self.last_clear_time = datetime.now()
        result = self._create_cache_result_dict(cleared_count, memory_freed, duration, errors)
        logger.info(f"Cache clearing completed: {result}")
        return result
    
    def _create_cache_result_dict(self, cleared_count: int, memory_freed: float, 
                                 duration: float, errors: List[str]) -> Dict[str, Any]:
        """Create cache clearing result dictionary."""
        base_data = self._create_base_cache_data(cleared_count, memory_freed, duration)
        base_data['errors'] = errors
        return base_data
    
    def _create_base_cache_data(self, cleared_count: int, memory_freed: float, duration: float) -> Dict[str, Any]:
        """Create base cache clearing data."""
        return {
            'action': RecoveryAction.CLEAR_CACHES.value,
            'caches_cleared': cleared_count,
            'memory_freed_mb': memory_freed,
            'duration_seconds': duration
        }
    
    def get_priority(self) -> int:
        """Cache clearing has medium priority."""
        return 2