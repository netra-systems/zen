"""Connection pool reduction memory recovery strategy."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from netra_backend.app.core.memory_recovery_base import (
    MemoryPressureLevel,
    MemoryRecoveryStrategy,
    MemorySnapshot,
    RecoveryAction,
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ConnectionPoolReductionStrategy(MemoryRecoveryStrategy):
    """Strategy to reduce connection pool sizes."""
    
    def __init__(self, connection_pools: List[Any]):
        """Initialize with connection pools."""
        self.connection_pools = connection_pools
        self.original_sizes: Dict[int, int] = {}
        self.reduction_factor = 0.5  # Reduce to 50% of original
    
    async def can_apply(self, snapshot: MemorySnapshot) -> bool:
        """Check if connection pool reduction should be applied."""
        return snapshot.pressure_level in [
            MemoryPressureLevel.CRITICAL,
            MemoryPressureLevel.EMERGENCY
        ]
    
    def _get_pool_size_attr(self, pool: Any) -> Optional[str]:
        """Get the pool size attribute name."""
        if hasattr(pool, 'maxsize'):
            return 'maxsize'
        elif hasattr(pool, 'max_size'):
            return 'max_size'
        return None
    
    def _store_original_pool_size(self, pool: Any, pool_id: int) -> bool:
        """Store original pool size if not already stored."""
        if pool_id in self.original_sizes:
            return True
        return self._save_pool_size_if_available(pool, pool_id)
    
    def _save_pool_size_if_available(self, pool: Any, pool_id: int) -> bool:
        """Save pool size if size attribute is available."""
        size_attr = self._get_pool_size_attr(pool)
        if size_attr:
            self.original_sizes[pool_id] = getattr(pool, size_attr)
            return True
        return False
    
    def _calculate_reduced_size(self, original_size: int) -> int:
        """Calculate reduced pool size based on reduction factor."""
        return max(1, int(original_size * self.reduction_factor))
    
    def _apply_pool_size_reduction(self, pool: Any, new_size: int) -> bool:
        """Apply new size to connection pool."""
        size_attr = self._get_pool_size_attr(pool)
        if size_attr:
            setattr(pool, size_attr, new_size)
            return True
        return False
    
    async def _cleanup_excess_connections(self, pool: Any) -> None:
        """Close excess connections if pool supports cleanup."""
        if hasattr(pool, '_cleanup'):
            await pool._cleanup()
    
    async def _process_single_pool(self, pool: Any) -> bool:
        """Process a single connection pool for size reduction."""
        pool_id = id(pool)
        if not self._store_original_pool_size(pool, pool_id):
            return False
        original_size = self.original_sizes[pool_id]
        new_size = self._calculate_reduced_size(original_size)
        if self._apply_pool_size_reduction(pool, new_size):
            await self._cleanup_excess_connections(pool)
            return True
        return False
    
    def _build_reduction_result(self, start_time: datetime, reduced_pools: int, 
                              errors: List[str]) -> Dict[str, Any]:
        """Build the connection pool reduction result dictionary."""
        duration = (datetime.now() - start_time).total_seconds()
        base_result = self._create_base_reduction_data(reduced_pools, duration)
        base_result['errors'] = errors
        return base_result
    
    def _create_base_reduction_data(self, reduced_pools: int, duration: float) -> Dict[str, Any]:
        """Create base reduction result data."""
        return {
            'action': RecoveryAction.REDUCE_CONNECTIONS.value,
            'pools_reduced': reduced_pools,
            'reduction_factor': self.reduction_factor,
            'duration_seconds': duration
        }
    
    async def execute(self, snapshot: MemorySnapshot) -> Dict[str, Any]:
        """Execute connection pool reduction."""
        start_time = datetime.now()
        reduced_pools, errors = 0, []
        for pool in self.connection_pools:
            try:
                if await self._process_single_pool(pool):
                    reduced_pools += 1
            except Exception as e:
                errors.append(str(e))
                logger.warning(f"Failed to reduce connection pool: {e}")
        result = self._build_reduction_result(start_time, reduced_pools, errors)
        logger.info(f"Connection pool reduction completed: {result}")
        return result
    
    def get_priority(self) -> int:
        """Connection reduction has lower priority as it affects performance."""
        return 3
    
    async def restore_original_sizes(self) -> None:
        """Restore original connection pool sizes."""
        for pool in self.connection_pools:
            try:
                self._restore_single_pool_size(pool)
            except Exception as e:
                logger.warning(f"Failed to restore connection pool size: {e}")
    
    def _restore_single_pool_size(self, pool: Any) -> None:
        """Restore original size for a single pool."""
        pool_id = id(pool)
        if pool_id not in self.original_sizes:
            return
        original_size = self.original_sizes[pool_id]
        self._apply_original_size(pool, original_size)
    
    def _apply_original_size(self, pool: Any, original_size: int) -> None:
        """Apply original size to pool."""
        if hasattr(pool, 'maxsize'):
            pool.maxsize = original_size
        elif hasattr(pool, 'max_size'):
            pool.max_size = original_size