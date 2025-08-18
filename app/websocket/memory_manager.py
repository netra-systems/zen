"""WebSocket Memory Management and Leak Prevention.

Manages memory usage, prevents leaks, and handles resource cleanup
for WebSocket connections and associated data structures.
"""

import asyncio
import gc
import sys
import time
import weakref
from datetime import datetime, timezone, timedelta
from typing import Dict, Set, List, Optional, Any
from dataclasses import dataclass, field

from app.logging_config import central_logger
from .connection import ConnectionInfo

logger = central_logger.get_logger(__name__)


@dataclass
class MemoryMetrics:
    """Memory usage metrics."""
    total_memory_mb: float = 0.0
    connection_memory_mb: float = 0.0
    message_buffer_mb: float = 0.0
    active_connections: int = 0
    total_allocations: int = 0
    gc_collections: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ConnectionMemoryTracker:
    """Tracks memory usage per connection."""
    
    def __init__(self):
        self.connection_refs: weakref.WeakSet[ConnectionInfo] = weakref.WeakSet()
        self.message_buffers: Dict[str, List[Any]] = {}
        self.buffer_sizes: Dict[str, float] = {}  # Cache buffer sizes
        self.buffer_limits = {
            "max_messages_per_connection": 1000,
            "max_buffer_size_mb": 10.0,
            "max_connection_age_hours": 24
        }
    
    def track_connection(self, conn_info: ConnectionInfo) -> None:
        """Track connection memory usage."""
        self.connection_refs.add(conn_info)
        self.message_buffers[conn_info.connection_id] = []
        self.buffer_sizes[conn_info.connection_id] = 0.0
        logger.debug(f"Started tracking memory for connection {conn_info.connection_id}")
    
    def untrack_connection(self, connection_id: str) -> None:
        """Stop tracking connection and cleanup buffers."""
        self.message_buffers.pop(connection_id, None)
        self.buffer_sizes.pop(connection_id, None)
        logger.debug(f"Stopped tracking memory for connection {connection_id}")
    
    def add_message_to_buffer(self, connection_id: str, message: Any) -> bool:
        """Add message to connection buffer with size limits."""
        if connection_id not in self.message_buffers:
            return False
        
        buffer = self.message_buffers[connection_id]
        message_size = sys.getsizeof(message) / (1024 * 1024)  # Calculate once
        
        # Check message count limit and remove oldest if needed
        if len(buffer) >= self.buffer_limits["max_messages_per_connection"]:
            removed_msg = buffer.pop(0)
            self.buffer_sizes[connection_id] -= sys.getsizeof(removed_msg) / (1024 * 1024)
        
        buffer.append(message)
        self.buffer_sizes[connection_id] += message_size
        
        # Check buffer size limit with cached value
        if self.buffer_sizes[connection_id] > self.buffer_limits["max_buffer_size_mb"]:
            self._reduce_buffer_size(connection_id)
        
        return True
    
    def _reduce_buffer_size(self, connection_id: str) -> None:
        """Reduce buffer size efficiently when over limit."""
        buffer = self.message_buffers[connection_id]
        target_size = len(buffer) // 2
        
        # Remove first half of messages and recalculate size
        removed_messages = buffer[:target_size]
        buffer[:] = buffer[target_size:]
        
        # Recalculate cached size after bulk removal
        self.buffer_sizes[connection_id] = sum(sys.getsizeof(msg) for msg in buffer) / (1024 * 1024)
        logger.warning(f"Reduced buffer size for {connection_id} to {len(buffer)} messages")
    
    def get_connection_memory_info(self, connection_id: str) -> Dict[str, Any]:
        """Get memory information for a specific connection."""
        buffer = self.message_buffers.get(connection_id, [])
        buffer_size_mb = self.buffer_sizes.get(connection_id, 0.0)
        
        return {
            "connection_id": connection_id,
            "message_count": len(buffer),
            "buffer_size_mb": buffer_size_mb,
            "is_tracked": connection_id in self.message_buffers
        }


class WebSocketMemoryManager:
    """Manages WebSocket memory usage and prevents leaks."""
    
    def __init__(self):
        self.memory_tracker = ConnectionMemoryTracker()
        self.metrics_history: List[MemoryMetrics] = []
        self.cleanup_interval_seconds = 300  # 5 minutes
        self.metrics_retention_hours = 24
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        self._last_gc_count = gc.get_count()
    
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
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("WebSocket memory manager stopped")
    
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
        cleanup_stats = await self._perform_cleanup()
        await self._collect_garbage()
        return cleanup_stats
    
    async def _cleanup_loop(self) -> None:
        """Main cleanup monitoring loop."""
        while self._running:
            try:
                await self._perform_cleanup()
                await self._collect_metrics()
                await asyncio.sleep(self.cleanup_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Memory cleanup loop error: {e}")
                await asyncio.sleep(30)
    
    async def _perform_cleanup(self) -> Dict[str, Any]:
        """Perform memory cleanup operations."""
        start_time = time.time()
        cleaned_metrics = self._cleanup_old_metrics()
        cleaned_connections, freed_memory_mb = self._cleanup_stale_connections()
        return self._build_cleanup_stats(start_time, cleaned_connections, cleaned_metrics, freed_memory_mb)
    
    def _cleanup_old_metrics(self) -> int:
        """Clean up old metrics and return count cleaned."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.metrics_retention_hours)
        initial_count = len(self.metrics_history)
        self.metrics_history = [m for m in self.metrics_history if m.timestamp > cutoff_time]
        return initial_count - len(self.metrics_history)
    
    def _cleanup_stale_connections(self) -> tuple[int, float]:
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
    
    def _remove_stale_connections(self, stale_connections: List[str]) -> tuple[int, float]:
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
        cleanup_stats = {
            "cleaned_connections": cleaned_connections,
            "cleaned_metrics": cleaned_metrics,
            "freed_memory_mb": freed_memory_mb,
            "cleanup_time_seconds": cleanup_time
        }
        if cleaned_connections > 0 or cleaned_metrics > 0:
            logger.info(f"Memory cleanup completed: {cleanup_stats}")
        return cleanup_stats
    
    async def _collect_garbage(self) -> None:
        """Force garbage collection."""
        gc.collect()
        current_gc_count = gc.get_count()
        collections = tuple(a - b for a, b in zip(current_gc_count, self._last_gc_count))
        self._last_gc_count = current_gc_count
        
        if any(collections):
            logger.debug(f"Garbage collection stats: {collections}")
    
    async def _collect_metrics(self) -> None:
        """Collect current memory metrics efficiently."""
        # Use cached buffer sizes for efficiency
        connection_memory_mb = sum(self.memory_tracker.buffer_sizes.values())
        total_memory_mb = connection_memory_mb + (len(self.memory_tracker.message_buffers) * 0.1)  # Estimate
        
        metrics = MemoryMetrics(
            total_memory_mb=total_memory_mb,
            connection_memory_mb=connection_memory_mb,
            active_connections=len(self.memory_tracker.message_buffers),
            total_allocations=len(self.memory_tracker.connection_refs),
            gc_collections=sum(gc.get_count())
        )
        
        self.metrics_history.append(metrics)
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics."""
        current_metrics = self.metrics_history[-1] if self.metrics_history else MemoryMetrics()
        
        connection_stats = {}
        for connection_id in self.memory_tracker.message_buffers.keys():
            connection_stats[connection_id] = self.memory_tracker.get_connection_memory_info(connection_id)
        
        return {
            "current_metrics": {
                "total_memory_mb": current_metrics.total_memory_mb,
                "connection_memory_mb": current_metrics.connection_memory_mb,
                "active_connections": current_metrics.active_connections,
                "total_allocations": current_metrics.total_allocations,
                "gc_collections": current_metrics.gc_collections
            },
            "connection_details": connection_stats,
            "buffer_limits": self.memory_tracker.buffer_limits,
            "metrics_history_count": len(self.metrics_history),
            "monitoring_active": self._running
        }
    
    def check_memory_health(self) -> Dict[str, Any]:
        """Check memory health and identify issues."""
        if not self.metrics_history:
            return {"status": "no_data", "issues": []}
        current = self.metrics_history[-1]
        issues = self._collect_memory_health_issues(current)
        return self._build_health_report(current, issues)
    
    def _collect_memory_health_issues(self, current) -> List[Dict[str, Any]]:
        """Collect all memory health issues."""
        issues = []
        self._check_high_memory_usage(current, issues)
        self._check_high_connection_count(current, issues)
        self._check_memory_growth_trend(issues)
        return issues
    
    def _check_high_memory_usage(self, current, issues: List[Dict[str, Any]]) -> None:
        """Check for high memory usage issues."""
        if current.connection_memory_mb > 100:
            issues.append({
                "type": "high_memory_usage",
                "severity": "high",
                "message": f"Connection memory usage: {current.connection_memory_mb:.1f}MB"
            })
    
    def _check_high_connection_count(self, current, issues: List[Dict[str, Any]]) -> None:
        """Check for high connection count issues."""
        if current.active_connections > 1000:
            issues.append({
                "type": "high_connection_count",
                "severity": "medium",
                "message": f"Active connections: {current.active_connections}"
            })
    
    def _check_memory_growth_trend(self, issues: List[Dict[str, Any]]) -> None:
        """Check for memory growth trend issues."""
        if len(self.metrics_history) >= 2:
            growth_rate = self._calculate_memory_growth_rate()
            if growth_rate > 0.1:
                issues.append({
                    "type": "memory_growth",
                    "severity": "medium",
                    "message": f"Memory growth rate: {growth_rate:.1%}"
                })
    
    def _calculate_memory_growth_rate(self) -> float:
        """Calculate memory growth rate between last two metrics."""
        current = self.metrics_history[-1]
        prev = self.metrics_history[-2]
        return (current.total_memory_mb - prev.total_memory_mb) / prev.total_memory_mb
    
    def _build_health_report(self, current, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build final health report."""
        status = "healthy" if not issues else "issues_detected"
        return {
            "status": status,
            "issues": issues,
            "total_issues": len(issues),
            "current_memory_mb": current.total_memory_mb
        }