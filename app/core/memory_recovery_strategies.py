"""Memory exhaustion detection and recovery strategies.

Provides proactive memory monitoring, leak detection, and recovery mechanisms
to prevent system crashes due to memory exhaustion.
"""

import asyncio
import gc
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class MemoryPressureLevel(Enum):
    """Levels of memory pressure."""
    LOW = "low"          # < 70% usage
    MODERATE = "moderate"  # 70-80% usage
    HIGH = "high"        # 80-90% usage
    CRITICAL = "critical"  # 90-95% usage
    EMERGENCY = "emergency"  # > 95% usage


class RecoveryAction(Enum):
    """Types of memory recovery actions."""
    GARBAGE_COLLECT = "garbage_collect"
    CLEAR_CACHES = "clear_caches"
    REDUCE_CONNECTIONS = "reduce_connections"
    PAUSE_NON_CRITICAL = "pause_non_critical"
    EMERGENCY_SHUTDOWN = "emergency_shutdown"


@dataclass
class MemoryThresholds:
    """Memory usage thresholds."""
    moderate_percent: float = 70.0
    high_percent: float = 80.0
    critical_percent: float = 90.0
    emergency_percent: float = 95.0
    gc_threshold_mb: int = 100  # MB increase to trigger GC


@dataclass
class MemorySnapshot:
    """Snapshot of memory usage at a point in time."""
    timestamp: datetime
    total_mb: float
    available_mb: float
    used_mb: float
    percent_used: float
    pressure_level: MemoryPressureLevel
    
    # Python-specific metrics
    gc_counts: Tuple[int, int, int]
    object_count: int
    
    # Process-specific metrics
    rss_mb: float  # Resident Set Size
    vms_mb: float  # Virtual Memory Size


class MemoryRecoveryStrategy(ABC):
    """Abstract base for memory recovery strategies."""
    
    @abstractmethod
    async def can_apply(self, snapshot: MemorySnapshot) -> bool:
        """Check if this strategy can be applied."""
        pass
    
    @abstractmethod
    async def execute(self, snapshot: MemorySnapshot) -> Dict[str, Any]:
        """Execute the recovery strategy."""
        pass
    
    @abstractmethod
    def get_priority(self) -> int:
        """Get strategy priority (lower = higher priority)."""
        pass


class GarbageCollectionStrategy(MemoryRecoveryStrategy):
    """Strategy to trigger garbage collection."""
    
    def __init__(self, aggressive: bool = False):
        """Initialize GC strategy."""
        self.aggressive = aggressive
        self.last_gc_time: Optional[datetime] = None
        self.min_gc_interval = timedelta(seconds=30)
    
    async def can_apply(self, snapshot: MemorySnapshot) -> bool:
        """Check if GC should be triggered."""
        # Don't run GC too frequently
        if self.last_gc_time:
            time_since_gc = datetime.now() - self.last_gc_time
            if time_since_gc < self.min_gc_interval:
                return False
        
        # Apply when memory pressure is moderate or higher
        return snapshot.pressure_level != MemoryPressureLevel.LOW
    
    def _prepare_gc_execution(self):
        """Prepare for garbage collection execution."""
        start_time = datetime.now()
        initial_memory = self._get_current_memory()
        before_counts = gc.get_count()
        return start_time, initial_memory, before_counts

    def _perform_garbage_collection(self) -> int:
        """Perform garbage collection based on strategy mode."""
        if self.aggressive:
            collected = sum(gc.collect(generation) for generation in range(3))
        else:
            collected = gc.collect()
        return collected

    def _calculate_gc_results(self, start_time, initial_memory, before_counts, collected):
        """Calculate garbage collection results and metrics."""
        after_counts = gc.get_count()
        final_memory = self._get_current_memory()
        memory_freed = initial_memory - final_memory
        duration = (datetime.now() - start_time).total_seconds()
        self.last_gc_time = datetime.now()
        return after_counts, memory_freed, duration

    def _build_gc_result_dict(self, collected, memory_freed, duration, before_counts, after_counts):
        """Build the garbage collection result dictionary."""
        return {
            'action': RecoveryAction.GARBAGE_COLLECT.value,
            'objects_collected': collected, 'memory_freed_mb': memory_freed,
            'duration_seconds': duration, 'gc_counts_before': before_counts,
            'gc_counts_after': after_counts, 'aggressive': self.aggressive
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
    
    def _get_current_memory(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0


class CacheClearingStrategy(MemoryRecoveryStrategy):
    """Strategy to clear various caches."""
    
    def __init__(self, cache_managers: List[Any]):
        """Initialize with cache managers."""
        self.cache_managers = cache_managers
        self.last_clear_time: Optional[datetime] = None
        self.min_clear_interval = timedelta(minutes=5)
    
    async def can_apply(self, snapshot: MemorySnapshot) -> bool:
        """Check if cache clearing should be applied."""
        # Don't clear caches too frequently
        if self.last_clear_time:
            time_since_clear = datetime.now() - self.last_clear_time
            if time_since_clear < self.min_clear_interval:
                return False
        
        # Apply when memory pressure is high
        return snapshot.pressure_level in [
            MemoryPressureLevel.HIGH,
            MemoryPressureLevel.CRITICAL,
            MemoryPressureLevel.EMERGENCY
        ]
    
    async def execute(self, snapshot: MemorySnapshot) -> Dict[str, Any]:
        """Execute cache clearing."""
        start_time = datetime.now()
        initial_memory = self._get_current_memory()
        
        cleared_count = 0
        errors = []
        
        for cache_manager in self.cache_managers:
            try:
                if hasattr(cache_manager, 'clear_all'):
                    await cache_manager.clear_all()
                    cleared_count += 1
                elif hasattr(cache_manager, 'clear'):
                    cache_manager.clear()
                    cleared_count += 1
            except Exception as e:
                errors.append(str(e))
                logger.warning(f"Failed to clear cache {type(cache_manager).__name__}: {e}")
        
        # Clear Python's internal caches
        if hasattr(sys, '_clear_type_cache'):
            sys._clear_type_cache()
        
        final_memory = self._get_current_memory()
        memory_freed = initial_memory - final_memory
        duration = (datetime.now() - start_time).total_seconds()
        self.last_clear_time = datetime.now()
        
        result = {
            'action': RecoveryAction.CLEAR_CACHES.value,
            'caches_cleared': cleared_count,
            'memory_freed_mb': memory_freed,
            'duration_seconds': duration,
            'errors': errors
        }
        
        logger.info(f"Cache clearing completed: {result}")
        return result
    
    def get_priority(self) -> int:
        """Cache clearing has medium priority."""
        return 2
    
    def _get_current_memory(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0


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
    
    def _build_reduction_result(self, start_time: datetime, reduced_pools: int, errors: List[str]) -> Dict[str, Any]:
        """Build the connection pool reduction result dictionary."""
        duration = (datetime.now() - start_time).total_seconds()
        return {
            'action': RecoveryAction.REDUCE_CONNECTIONS.value,
            'pools_reduced': reduced_pools, 'reduction_factor': self.reduction_factor,
            'duration_seconds': duration, 'errors': errors
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
                pool_id = id(pool)
                if pool_id in self.original_sizes:
                    original_size = self.original_sizes[pool_id]
                    
                    if hasattr(pool, 'maxsize'):
                        pool.maxsize = original_size
                    elif hasattr(pool, 'max_size'):
                        pool.max_size = original_size
                        
            except Exception as e:
                logger.warning(f"Failed to restore connection pool size: {e}")


class MemoryMonitor:
    """Monitor memory usage and trigger recovery actions."""
    
    def __init__(self, thresholds: Optional[MemoryThresholds] = None):
        """Initialize memory monitor."""
        self.thresholds = thresholds or MemoryThresholds()
        self.strategies: List[MemoryRecoveryStrategy] = []
        self.snapshots: List[MemorySnapshot] = []
        self.max_snapshots = 100
        
        # Recovery tracking
        self.recovery_history: List[Dict[str, Any]] = []
        self.last_recovery_time: Optional[datetime] = None
        self.min_recovery_interval = timedelta(seconds=30)
        
        # Monitoring state
        self.monitoring_active = False
        self.monitor_task: Optional[asyncio.Task] = None
    
    def add_recovery_strategy(self, strategy: MemoryRecoveryStrategy) -> None:
        """Add a memory recovery strategy."""
        self.strategies.append(strategy)
        # Sort by priority
        self.strategies.sort(key=lambda s: s.get_priority())
    
    async def start_monitoring(self, interval_seconds: int = 30) -> None:
        """Start continuous memory monitoring."""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_task = asyncio.create_task(
            self._monitoring_loop(interval_seconds)
        )
        logger.info("Memory monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop memory monitoring."""
        self.monitoring_active = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Memory monitoring stopped")
    
    async def _monitoring_loop(self, interval_seconds: int) -> None:
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                snapshot = await self.take_snapshot()
                await self.check_and_recover(snapshot)
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Memory monitoring error: {e}")
                await asyncio.sleep(interval_seconds)
    
    def _get_system_memory_metrics(self):
        """Get system memory metrics from psutil or fallback values."""
        try:
            import psutil
            memory = psutil.virtual_memory()
            total_mb = memory.total / 1024 / 1024
            available_mb = memory.available / 1024 / 1024
            used_mb = memory.used / 1024 / 1024
            percent_used = memory.percent
            return total_mb, available_mb, used_mb, percent_used
        except ImportError:
            total_mb = 8192.0  # Assume 8GB
            percent_used = 50.0
            available_mb = total_mb * (100 - percent_used) / 100
            used_mb = total_mb - available_mb
            return total_mb, available_mb, used_mb, percent_used

    def _get_process_memory_metrics(self):
        """Get process memory metrics from psutil or fallback values."""
        try:
            import psutil
            process = psutil.Process()
            process_memory = process.memory_info()
            rss_mb = process_memory.rss / 1024 / 1024
            vms_mb = process_memory.vms / 1024 / 1024
            return rss_mb, vms_mb
        except ImportError:
            return 512.0, 1024.0

    def _get_python_memory_metrics(self):
        """Get Python-specific memory metrics."""
        gc_counts = gc.get_count()
        object_count = len(gc.get_objects())
        return gc_counts, object_count

    def _create_memory_snapshot(self, timestamp, total_mb, available_mb, used_mb, 
                               percent_used, pressure_level, gc_counts, object_count, 
                               rss_mb, vms_mb) -> MemorySnapshot:
        """Create memory snapshot object."""
        return MemorySnapshot(
            timestamp=timestamp, total_mb=total_mb, available_mb=available_mb,
            used_mb=used_mb, percent_used=percent_used, pressure_level=pressure_level,
            gc_counts=gc_counts, object_count=object_count, rss_mb=rss_mb, vms_mb=vms_mb
        )

    def _store_snapshot(self, snapshot: MemorySnapshot) -> None:
        """Store snapshot and manage snapshot history."""
        self.snapshots.append(snapshot)
        if len(self.snapshots) > self.max_snapshots:
            self.snapshots = self.snapshots[-self.max_snapshots//2:]

    def _collect_all_memory_metrics(self) -> Tuple[datetime, float, float, float, float, float, float, Tuple[int, int, int], int]:
        """Collect all memory metrics for snapshot creation."""
        timestamp = datetime.now()
        total_mb, available_mb, used_mb, percent_used = self._get_system_memory_metrics()
        rss_mb, vms_mb = self._get_process_memory_metrics()
        gc_counts, object_count = self._get_python_memory_metrics()
        return timestamp, total_mb, available_mb, used_mb, percent_used, rss_mb, vms_mb, gc_counts, object_count
    
    async def take_snapshot(self) -> MemorySnapshot:
        """Take a memory usage snapshot."""
        timestamp, total_mb, available_mb, used_mb, percent_used, rss_mb, vms_mb, gc_counts, object_count = self._collect_all_memory_metrics()
        pressure_level = self._calculate_pressure_level(percent_used)
        snapshot = self._create_memory_snapshot(timestamp, total_mb, available_mb, used_mb,
                                              percent_used, pressure_level, gc_counts, 
                                              object_count, rss_mb, vms_mb)
        self._store_snapshot(snapshot)
        return snapshot
    
    async def check_and_recover(self, snapshot: MemorySnapshot) -> List[Dict[str, Any]]:
        """Check memory pressure and trigger recovery if needed."""
        if snapshot.pressure_level == MemoryPressureLevel.LOW:
            return []
        
        # Check if we should throttle recovery attempts
        if self.last_recovery_time:
            time_since_recovery = datetime.now() - self.last_recovery_time
            if time_since_recovery < self.min_recovery_interval:
                return []
        
        logger.warning(
            f"Memory pressure detected: {snapshot.pressure_level.value} "
            f"({snapshot.percent_used:.1f}% used)"
        )
        
        recovery_results = []
        
        # Try recovery strategies in priority order
        for strategy in self.strategies:
            try:
                if await strategy.can_apply(snapshot):
                    result = await strategy.execute(snapshot)
                    recovery_results.append(result)
                    
                    # Take new snapshot to check improvement
                    new_snapshot = await self.take_snapshot()
                    if new_snapshot.pressure_level < snapshot.pressure_level:
                        logger.info(f"Memory pressure reduced: {new_snapshot.pressure_level.value}")
                        break
                        
            except Exception as e:
                logger.error(f"Recovery strategy failed {type(strategy).__name__}: {e}")
        
        self.last_recovery_time = datetime.now()
        self.recovery_history.extend(recovery_results)
        
        return recovery_results
    
    def _calculate_pressure_level(self, percent_used: float) -> MemoryPressureLevel:
        """Calculate memory pressure level."""
        if percent_used >= self.thresholds.emergency_percent:
            return MemoryPressureLevel.EMERGENCY
        elif percent_used >= self.thresholds.critical_percent:
            return MemoryPressureLevel.CRITICAL
        elif percent_used >= self.thresholds.high_percent:
            return MemoryPressureLevel.HIGH
        elif percent_used >= self.thresholds.moderate_percent:
            return MemoryPressureLevel.MODERATE
        else:
            return MemoryPressureLevel.LOW
    
    def get_memory_status(self) -> Dict[str, Any]:
        """Get current memory status."""
        if not self.snapshots:
            return {'status': 'no_data'}
        
        latest = self.snapshots[-1]
        
        return {
            'current_usage_percent': latest.percent_used,
            'pressure_level': latest.pressure_level.value,
            'available_mb': latest.available_mb,
            'process_rss_mb': latest.rss_mb,
            'gc_objects': latest.object_count,
            'recovery_count': len(self.recovery_history),
            'last_recovery': self.last_recovery_time.isoformat() if self.last_recovery_time else None
        }


# Global memory monitor instance
memory_monitor = MemoryMonitor()


# Convenience functions
async def setup_memory_recovery(
    cache_managers: List[Any],
    connection_pools: List[Any],
    thresholds: Optional[MemoryThresholds] = None
) -> None:
    """Set up memory recovery with common strategies."""
    if thresholds:
        global memory_monitor
        memory_monitor = MemoryMonitor(thresholds)
    
    # Add standard recovery strategies
    memory_monitor.add_recovery_strategy(GarbageCollectionStrategy())
    memory_monitor.add_recovery_strategy(GarbageCollectionStrategy(aggressive=True))
    memory_monitor.add_recovery_strategy(CacheClearingStrategy(cache_managers))
    memory_monitor.add_recovery_strategy(ConnectionPoolReductionStrategy(connection_pools))
    
    await memory_monitor.start_monitoring()


async def emergency_memory_recovery() -> List[Dict[str, Any]]:
    """Trigger emergency memory recovery."""
    logger.critical("Triggering emergency memory recovery")
    
    snapshot = await memory_monitor.take_snapshot()
    
    # Force emergency-level snapshot
    snapshot.pressure_level = MemoryPressureLevel.EMERGENCY
    
    return await memory_monitor.check_and_recover(snapshot)