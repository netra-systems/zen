"""WebSocket Memory Management and Leak Prevention.

Manages memory usage, prevents leaks, and handles resource cleanup
for WebSocket connections and associated data structures.
"""

import asyncio
from typing import Dict, Any, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.connection import ConnectionInfo
from netra_backend.app.memory_tracker import ConnectionMemoryTracker
from netra_backend.app.memory_metrics import MemoryMetricsCollector, MemoryHealthChecker, MemoryStatsCollector
from netra_backend.app.memory_cleanup import MemoryCleanupManager, GarbageCollectionManager

logger = central_logger.get_logger(__name__)


class WebSocketMemoryManager:
    """Manages WebSocket memory usage and prevents leaks."""
    
    def __init__(self):
        self._init_memory_trackers()
        self._init_state_variables()
    
    def _init_memory_trackers(self):
        """Initialize memory tracking components."""
        self.memory_tracker = ConnectionMemoryTracker()
        self.metrics_collector = MemoryMetricsCollector(self.memory_tracker)
        self.health_checker = MemoryHealthChecker(self.metrics_collector)
        self.stats_collector = MemoryStatsCollector(self.memory_tracker, self.metrics_collector)
        self.cleanup_manager = MemoryCleanupManager(self.memory_tracker, self.metrics_collector)
        self.gc_manager = GarbageCollectionManager()
    
    def _init_state_variables(self):
        """Initialize state and configuration variables."""
        self.cleanup_interval_seconds = 300  # 5 minutes
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start_monitoring(self) -> None:
        """Start memory monitoring and cleanup."""
        if self._running:
            return
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("WebSocket memory manager started")
    
    async def stop_monitoring(self) -> None:
        """Stop memory monitoring."""
        self._running = False
        await self._cancel_cleanup_task()
        logger.info("WebSocket memory manager stopped")
    
    async def _cancel_cleanup_task(self) -> None:
        """Cancel cleanup task safely."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
    
    def register_connection(self, conn_info: ConnectionInfo) -> None:
        """Register connection for memory tracking."""
        self.memory_tracker.track_connection(conn_info)
    
    def unregister_connection(self, connection_id: str) -> None:
        """Unregister connection from memory tracking."""
        self.memory_tracker.untrack_connection(connection_id)
    
    def track_message(self, connection_id: str, message: Any) -> None:
        """Track message for memory management."""
        self.memory_tracker.add_message_to_buffer(connection_id, message)
    
    async def force_cleanup(self) -> Dict[str, Any]:
        """Force immediate memory cleanup."""
        cleanup_stats = await self.cleanup_manager.perform_cleanup()
        await self.gc_manager.collect_garbage()
        return cleanup_stats
    
    async def _cleanup_loop(self) -> None:
        """Main cleanup monitoring loop."""
        while self._running:
            try:
                await self._execute_cleanup_cycle()
                await asyncio.sleep(self.cleanup_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                await self._handle_cleanup_error(e)
    
    async def _execute_cleanup_cycle(self) -> None:
        """Execute one cleanup cycle."""
        await self.cleanup_manager.perform_cleanup()
        await self._collect_metrics()
    
    async def _handle_cleanup_error(self, error: Exception) -> None:
        """Handle error in cleanup loop."""
        logger.error(f"Memory cleanup loop error: {error}")
        await asyncio.sleep(30)
    
    async def _collect_metrics(self) -> None:
        """Collect current memory metrics efficiently."""
        metrics = self.metrics_collector.collect_current_metrics()
        self.metrics_collector.add_metrics(metrics)
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics."""
        return self.stats_collector.get_memory_stats()
    
    def check_memory_health(self) -> Dict[str, Any]:
        """Check memory health and identify issues."""
        return self.health_checker.check_memory_health()


# Re-export classes for backward compatibility
from netra_backend.app.memory_tracker import ConnectionMemoryTracker
from netra_backend.app.memory_metrics import MemoryMetrics, MemoryMetricsCollector, MemoryHealthChecker, MemoryStatsCollector
from netra_backend.app.memory_cleanup import MemoryCleanupManager, GarbageCollectionManager

__all__ = [
    "WebSocketMemoryManager", "ConnectionMemoryTracker", "MemoryMetrics", 
    "MemoryMetricsCollector", "MemoryHealthChecker", "MemoryStatsCollector",
    "MemoryCleanupManager", "GarbageCollectionManager"
]