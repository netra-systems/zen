"""Memory recovery strategies and monitoring system.

Provides strategy implementations and memory monitoring functionality
for proactive memory management and recovery.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from netra_backend.app.core.memory_recovery_base import (
    MemoryPressureLevel,
    MemoryRecoveryStrategy,
    MemorySnapshot,
    MemoryThresholds,
)
from netra_backend.app.core.memory_recovery_utils import (
    calculate_pressure_level,
    collect_all_memory_metrics,
    create_memory_snapshot,
)
from netra_backend.app.core.memory_strategies import (
    CacheClearingStrategy,
    ConnectionPoolReductionStrategy,
    GarbageCollectionStrategy,
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)



class MemoryMonitor:
    """Monitor memory usage and trigger recovery actions."""
    
    def __init__(self, thresholds: Optional[MemoryThresholds] = None):
        """Initialize memory monitor."""
        self.thresholds = thresholds or MemoryThresholds()
        self.strategies: List[MemoryRecoveryStrategy] = []
        self.snapshots: List[MemorySnapshot] = []
        self.max_snapshots = 100
        self._init_recovery_tracking()
        self._init_monitoring_state()
    
    def _init_recovery_tracking(self) -> None:
        """Initialize recovery tracking attributes."""
        self.recovery_history: List[Dict[str, Any]] = []
        self.last_recovery_time: Optional[datetime] = None
        self.min_recovery_interval = timedelta(seconds=30)
    
    def _init_monitoring_state(self) -> None:
        """Initialize monitoring state attributes."""
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

    def _store_snapshot(self, snapshot: MemorySnapshot) -> None:
        """Store snapshot and manage snapshot history."""
        self.snapshots.append(snapshot)
        if len(self.snapshots) > self.max_snapshots:
            self.snapshots = self.snapshots[-self.max_snapshots//2:]
    
    async def take_snapshot(self) -> MemorySnapshot:
        """Take a memory usage snapshot."""
        metrics = collect_all_memory_metrics()
        timestamp, total_mb, available_mb, used_mb, percent_used, rss_mb, vms_mb, gc_counts, object_count = metrics
        pressure_level = calculate_pressure_level(percent_used, self.thresholds)
        snapshot = create_memory_snapshot(timestamp, total_mb, available_mb, used_mb,
                                        percent_used, pressure_level, gc_counts, 
                                        object_count, rss_mb, vms_mb)
        self._store_snapshot(snapshot)
        return snapshot
    
    async def check_and_recover(self, snapshot: MemorySnapshot) -> List[Dict[str, Any]]:
        """Check memory pressure and trigger recovery if needed."""
        if self._should_skip_recovery(snapshot):
            return []
        self._log_memory_pressure_warning(snapshot)
        recovery_results = await self._execute_recovery_strategies(snapshot)
        self._finalize_recovery_session(recovery_results)
        return recovery_results
    
    def _should_skip_recovery(self, snapshot: MemorySnapshot) -> bool:
        """Check if recovery should be skipped."""
        if snapshot.pressure_level == MemoryPressureLevel.LOW:
            return True
        return self._is_recovery_throttled()
    
    def _is_recovery_throttled(self) -> bool:
        """Check if recovery is throttled by time interval."""
        if not self.last_recovery_time:
            return False
        time_since_recovery = datetime.now() - self.last_recovery_time
        return time_since_recovery < self.min_recovery_interval
    
    def _log_memory_pressure_warning(self, snapshot: MemorySnapshot) -> None:
        """Log memory pressure warning with details."""
        logger.warning(
            f"Memory pressure detected: {snapshot.pressure_level.value} "
            f"({snapshot.percent_used:.1f}% used)"
        )
    
    async def _execute_recovery_strategies(self, snapshot: MemorySnapshot) -> List[Dict[str, Any]]:
        """Execute recovery strategies in priority order."""
        recovery_results = []
        for strategy in self.strategies:
            strategy_result = await self._try_recovery_strategy(strategy, snapshot)
            if strategy_result:
                recovery_results.append(strategy_result)
                if await self._check_pressure_improvement(snapshot):
                    break
        return recovery_results
    
    async def _try_recovery_strategy(self, strategy: MemoryRecoveryStrategy, 
                                   snapshot: MemorySnapshot) -> Optional[Dict[str, Any]]:
        """Try executing a single recovery strategy."""
        try:
            if await strategy.can_apply(snapshot):
                return await strategy.execute(snapshot)
        except Exception as e:
            logger.error(f"Recovery strategy failed {type(strategy).__name__}: {e}")
        return None
    
    async def _check_pressure_improvement(self, original_snapshot: MemorySnapshot) -> bool:
        """Check if memory pressure has improved after recovery."""
        new_snapshot = await self.take_snapshot()
        if new_snapshot.pressure_level < original_snapshot.pressure_level:
            logger.info(f"Memory pressure reduced: {new_snapshot.pressure_level.value}")
            return True
        return False
    
    def _finalize_recovery_session(self, recovery_results: List[Dict[str, Any]]) -> None:
        """Finalize recovery session tracking."""
        self.last_recovery_time = datetime.now()
        self.recovery_history.extend(recovery_results)
    
    def get_memory_status(self) -> Dict[str, Any]:
        """Get current memory status."""
        if not self.snapshots:
            return {'status': 'no_data'}
        latest = self.snapshots[-1]
        basic_status = self._get_basic_memory_status(latest)
        recovery_status = self._get_recovery_status()
        return {**basic_status, **recovery_status}
    
    def _get_basic_memory_status(self, latest: MemorySnapshot) -> Dict[str, Any]:
        """Get basic memory status information."""
        basic_metrics = self._create_basic_metrics(latest)
        additional_metrics = self._create_additional_metrics(latest)
        return {**basic_metrics, **additional_metrics}
    
    def _create_basic_metrics(self, latest: MemorySnapshot) -> Dict[str, Any]:
        """Create basic memory metrics."""
        return {
            'current_usage_percent': latest.percent_used,
            'pressure_level': latest.pressure_level.value,
            'available_mb': latest.available_mb
        }
    
    def _create_additional_metrics(self, latest: MemorySnapshot) -> Dict[str, Any]:
        """Create additional memory metrics."""
        return {
            'process_rss_mb': latest.rss_mb,
            'gc_objects': latest.object_count
        }
    
    def _get_recovery_status(self) -> Dict[str, Any]:
        """Get recovery status information."""
        last_recovery_iso = self.last_recovery_time.isoformat() if self.last_recovery_time else None
        return {
            'recovery_count': len(self.recovery_history),
            'last_recovery': last_recovery_iso
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
    _configure_memory_monitor(thresholds)
    _add_recovery_strategies(cache_managers, connection_pools)
    await memory_monitor.start_monitoring()

def _configure_memory_monitor(thresholds: Optional[MemoryThresholds]) -> None:
    """Configure global memory monitor with thresholds."""
    if thresholds:
        global memory_monitor
        memory_monitor = MemoryMonitor(thresholds)

def _add_recovery_strategies(cache_managers: List[Any], connection_pools: List[Any]) -> None:
    """Add standard recovery strategies to memory monitor."""
    memory_monitor.add_recovery_strategy(GarbageCollectionStrategy())
    memory_monitor.add_recovery_strategy(GarbageCollectionStrategy(aggressive=True))
    memory_monitor.add_recovery_strategy(CacheClearingStrategy(cache_managers))
    memory_monitor.add_recovery_strategy(ConnectionPoolReductionStrategy(connection_pools))


async def emergency_memory_recovery() -> List[Dict[str, Any]]:
    """Trigger emergency memory recovery."""
    logger.critical("Triggering emergency memory recovery")
    snapshot = await memory_monitor.take_snapshot()
    # Force emergency-level snapshot
    snapshot.pressure_level = MemoryPressureLevel.EMERGENCY
    return await memory_monitor.check_and_recover(snapshot)