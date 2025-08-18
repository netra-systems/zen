"""WebSocket Memory Cleanup Operations and Management.

Handles memory cleanup, garbage collection, and resource management
for WebSocket connections and memory buffers.
"""

import gc
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class MemoryCleanupManager:
    """Manages cleanup operations for WebSocket memory management."""
    
    def __init__(self, memory_tracker, metrics_collector):
        self.memory_tracker = memory_tracker
        self.metrics_collector = metrics_collector
        self.metrics_retention_hours = 24
        self._last_gc_count = gc.get_count()
    
    async def perform_cleanup(self) -> Dict[str, Any]:
        """Perform memory cleanup operations."""
        start_time = time.time()
        cleaned_metrics = self._cleanup_old_metrics()
        cleaned_connections, freed_memory_mb = self._cleanup_stale_connections()
        return self._build_cleanup_stats(start_time, cleaned_connections, cleaned_metrics, freed_memory_mb)
    
    def _cleanup_old_metrics(self) -> int:
        """Clean up old metrics and return count cleaned."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.metrics_retention_hours)
        initial_count = len(self.metrics_collector.metrics_history)
        self.metrics_collector.metrics_history = [
            m for m in self.metrics_collector.metrics_history if m.timestamp > cutoff_time
        ]
        return initial_count - len(self.metrics_collector.metrics_history)
    
    def _cleanup_stale_connections(self) -> Tuple[int, float]:
        """Clean up stale connection buffers and return counts."""
        stale_connections = self._identify_stale_connections()
        return self._remove_stale_connections(stale_connections)
    
    def _identify_stale_connections(self) -> List[str]:
        """Identify connections with oversized buffers."""
        active_connection_ids = set(self.memory_tracker.message_buffers.keys())
        stale_connections = []
        for connection_id in active_connection_ids:
            if self._is_connection_stale(connection_id):
                stale_connections.append(connection_id)
        return stale_connections
    
    def _is_connection_stale(self, connection_id: str) -> bool:
        """Check if connection buffer exceeds size limit."""
        buffer_size_mb = self.memory_tracker.buffer_sizes.get(connection_id, 0.0)
        return buffer_size_mb > self.memory_tracker.buffer_limits["max_buffer_size_mb"]
    
    def _remove_stale_connections(self, stale_connections: List[str]) -> Tuple[int, float]:
        """Remove stale connections and return cleanup metrics."""
        freed_memory_mb = 0.0
        for connection_id in stale_connections:
            buffer_size = self.memory_tracker.buffer_sizes.get(connection_id, 0.0)
            self.memory_tracker.untrack_connection(connection_id)
            freed_memory_mb += buffer_size
        return len(stale_connections), freed_memory_mb
    
    def _build_cleanup_stats(self, start_time: float, cleaned_connections: int, 
                           cleaned_metrics: int, freed_memory_mb: float) -> Dict[str, Any]:
        """Build cleanup statistics report."""
        cleanup_time = time.time() - start_time
        cleanup_stats = self._create_cleanup_stats_dict(
            cleaned_connections, cleaned_metrics, freed_memory_mb, cleanup_time
        )
        self._log_cleanup_results(cleanup_stats, cleaned_connections, cleaned_metrics)
        return cleanup_stats
    
    def _create_cleanup_stats_dict(self, cleaned_connections: int, cleaned_metrics: int, 
                                  freed_memory_mb: float, cleanup_time: float) -> Dict[str, Any]:
        """Create cleanup statistics dictionary."""
        return {
            "cleaned_connections": cleaned_connections, "cleaned_metrics": cleaned_metrics,
            "freed_memory_mb": freed_memory_mb, "cleanup_time_seconds": cleanup_time
        }
    
    def _log_cleanup_results(self, cleanup_stats: Dict[str, Any], 
                           cleaned_connections: int, cleaned_metrics: int) -> None:
        """Log cleanup results if any cleanup occurred."""
        if cleaned_connections > 0 or cleaned_metrics > 0:
            logger.info(f"Memory cleanup completed: {cleanup_stats}")


class GarbageCollectionManager:
    """Manages garbage collection operations."""
    
    def __init__(self):
        self._last_gc_count = gc.get_count()
    
    async def collect_garbage(self) -> None:
        """Force garbage collection."""
        gc.collect()
        collections = self._calculate_gc_collections()
        self._log_gc_stats(collections)
    
    def _calculate_gc_collections(self) -> Tuple:
        """Calculate garbage collection counts since last check."""
        current_gc_count = gc.get_count()
        collections = tuple(a - b for a, b in zip(current_gc_count, self._last_gc_count))
        self._last_gc_count = current_gc_count
        return collections
    
    def _log_gc_stats(self, collections: Tuple) -> None:
        """Log garbage collection statistics if any occurred."""
        if any(collections):
            logger.debug(f"Garbage collection stats: {collections}")