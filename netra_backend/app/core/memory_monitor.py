"""
Memory Monitor Module - Compatibility Layer for Integration Tests

This module provides a compatibility layer for integration tests that expect
a memory monitoring implementation. This is a minimal implementation for test compatibility.

CRITICAL ARCHITECTURAL COMPLIANCE:
- This is a COMPATIBILITY LAYER for integration tests
- Provides minimal implementation for test collection compatibility
- DO NOT use in production - this is test infrastructure only

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Test Infrastructure Stability
- Value Impact: Enables integration test collection and execution
- Strategic Impact: Maintains test coverage during system evolution
"""

from typing import Any, Dict, List, Optional, Union, Callable
import gc
import tracemalloc
import psutil
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
import os

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class MemoryMetricType(Enum):
    """Types of memory metrics."""
    RSS = "rss"  # Resident Set Size
    VMS = "vms"  # Virtual Memory Size
    HEAP = "heap"
    STACK = "stack"
    ALLOCATED = "allocated"
    FREED = "freed"
    PEAK = "peak"


@dataclass
class MemorySnapshot:
    """A memory usage snapshot."""
    timestamp: float
    rss_mb: float
    vms_mb: float
    heap_mb: float
    available_mb: float
    percent_used: float
    process_id: int
    thread_count: int = 0

    @classmethod
    def create_current(cls) -> 'MemorySnapshot':
        """Create a snapshot of current memory usage."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            system_memory = psutil.virtual_memory()

            return cls(
                timestamp=time.time(),
                rss_mb=memory_info.rss / (1024 * 1024),
                vms_mb=memory_info.vms / (1024 * 1024),
                heap_mb=0.0,  # Not easily available in Python
                available_mb=system_memory.available / (1024 * 1024),
                percent_used=system_memory.percent,
                process_id=os.getpid(),
                thread_count=process.num_threads()
            )
        except Exception as e:
            logger.error(f"Failed to create memory snapshot: {e}")
            return cls(
                timestamp=time.time(),
                rss_mb=0.0,
                vms_mb=0.0,
                heap_mb=0.0,
                available_mb=0.0,
                percent_used=0.0,
                process_id=os.getpid(),
                thread_count=0
            )


class MemoryMonitor:
    """
    Simple memory monitor for test compatibility.

    This is a minimal implementation to satisfy integration test imports.
    Not intended for production use.
    """

    def __init__(self, max_snapshots: int = 100):
        """Initialize memory monitor."""
        self.max_snapshots = max_snapshots
        self.snapshots: deque = deque(maxlen=max_snapshots)
        self.memory_allocations: Dict[str, float] = defaultdict(float)
        self.memory_peaks: Dict[str, float] = defaultdict(float)
        self._lock = threading.Lock()
        self.monitoring_active = False
        self.tracemalloc_active = False

        logger.info("Memory monitor initialized (test compatibility mode)")

    def start_monitoring(self):
        """Start memory monitoring."""
        self.monitoring_active = True

        # Try to start tracemalloc for detailed tracking
        try:
            if not tracemalloc.is_tracing():
                tracemalloc.start()
                self.tracemalloc_active = True
                logger.debug("Tracemalloc started for detailed memory tracking")
        except Exception as e:
            logger.warning(f"Could not start tracemalloc: {e}")

        # Take initial snapshot
        self.take_snapshot("start_monitoring")

        logger.info("Memory monitoring started")

    def stop_monitoring(self):
        """Stop memory monitoring."""
        self.monitoring_active = False

        # Stop tracemalloc if we started it
        if self.tracemalloc_active:
            try:
                tracemalloc.stop()
                self.tracemalloc_active = False
                logger.debug("Tracemalloc stopped")
            except Exception as e:
                logger.warning(f"Error stopping tracemalloc: {e}")

        logger.info("Memory monitoring stopped")

    def take_snapshot(self, label: str = None) -> MemorySnapshot:
        """Take a memory usage snapshot."""
        snapshot = MemorySnapshot.create_current()

        with self._lock:
            self.snapshots.append((label or "snapshot", snapshot))

            # Update peaks
            self.memory_peaks["rss_mb"] = max(self.memory_peaks["rss_mb"], snapshot.rss_mb)
            self.memory_peaks["vms_mb"] = max(self.memory_peaks["vms_mb"], snapshot.vms_mb)
            self.memory_peaks["percent_used"] = max(self.memory_peaks["percent_used"], snapshot.percent_used)

        logger.debug(f"Memory snapshot taken ({label}): RSS={snapshot.rss_mb:.1f}MB, "
                    f"VMS={snapshot.vms_mb:.1f}MB, Used={snapshot.percent_used:.1f}%")

        return snapshot

    def record_allocation(self, component: str, size_bytes: float):
        """Record a memory allocation."""
        size_mb = size_bytes / (1024 * 1024)

        with self._lock:
            self.memory_allocations[component] += size_mb
            self.memory_peaks[f"{component}_allocated"] = max(
                self.memory_peaks[f"{component}_allocated"],
                self.memory_allocations[component]
            )

    def record_deallocation(self, component: str, size_bytes: float):
        """Record a memory deallocation."""
        size_mb = size_bytes / (1024 * 1024)

        with self._lock:
            self.memory_allocations[component] = max(0, self.memory_allocations[component] - size_mb)

    def get_current_usage(self) -> Dict[str, float]:
        """Get current memory usage statistics."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            system_memory = psutil.virtual_memory()

            return {
                "process_rss_mb": memory_info.rss / (1024 * 1024),
                "process_vms_mb": memory_info.vms / (1024 * 1024),
                "system_total_mb": system_memory.total / (1024 * 1024),
                "system_available_mb": system_memory.available / (1024 * 1024),
                "system_used_percent": system_memory.percent,
                "process_memory_percent": process.memory_percent()
            }
        except Exception as e:
            logger.error(f"Failed to get memory usage: {e}")
            return {}

    def get_memory_growth(self, start_label: str = None, end_label: str = None) -> Dict[str, float]:
        """Get memory growth between two snapshots."""
        with self._lock:
            if not self.snapshots:
                return {}

            snapshots_list = list(self.snapshots)

            # Find start snapshot
            start_snapshot = None
            if start_label:
                for label, snapshot in snapshots_list:
                    if label == start_label:
                        start_snapshot = snapshot
                        break
            else:
                start_snapshot = snapshots_list[0][1]

            # Find end snapshot
            end_snapshot = None
            if end_label:
                for label, snapshot in reversed(snapshots_list):
                    if label == end_label:
                        end_snapshot = snapshot
                        break
            else:
                end_snapshot = snapshots_list[-1][1]

            if not start_snapshot or not end_snapshot:
                return {}

            return {
                "rss_growth_mb": end_snapshot.rss_mb - start_snapshot.rss_mb,
                "vms_growth_mb": end_snapshot.vms_mb - start_snapshot.vms_mb,
                "time_elapsed": end_snapshot.timestamp - start_snapshot.timestamp,
                "start_timestamp": start_snapshot.timestamp,
                "end_timestamp": end_snapshot.timestamp
            }

    def get_memory_leaks(self, threshold_mb: float = 1.0) -> List[Dict[str, Any]]:
        """Detect potential memory leaks."""
        potential_leaks = []

        with self._lock:
            if len(self.snapshots) < 3:
                return potential_leaks

            # Compare first third with last third of snapshots
            snapshots_list = list(self.snapshots)
            third = len(snapshots_list) // 3

            early_snapshots = snapshots_list[:third]
            recent_snapshots = snapshots_list[-third:]

            if not early_snapshots or not recent_snapshots:
                return potential_leaks

            early_avg_rss = sum(s[1].rss_mb for s in early_snapshots) / len(early_snapshots)
            recent_avg_rss = sum(s[1].rss_mb for s in recent_snapshots) / len(recent_snapshots)

            growth = recent_avg_rss - early_avg_rss

            if growth > threshold_mb:
                potential_leaks.append({
                    "type": "steady_growth",
                    "growth_mb": growth,
                    "early_avg_mb": early_avg_rss,
                    "recent_avg_mb": recent_avg_rss,
                    "threshold_mb": threshold_mb,
                    "severity": "high" if growth > threshold_mb * 3 else "medium"
                })

        return potential_leaks

    def force_garbage_collection(self) -> Dict[str, Any]:
        """Force garbage collection and return statistics."""
        try:
            # Take snapshot before
            before_snapshot = self.take_snapshot("before_gc")

            # Force garbage collection
            collected = gc.collect()

            # Take snapshot after
            after_snapshot = self.take_snapshot("after_gc")

            memory_freed = before_snapshot.rss_mb - after_snapshot.rss_mb

            return {
                "objects_collected": collected,
                "memory_freed_mb": memory_freed,
                "before_rss_mb": before_snapshot.rss_mb,
                "after_rss_mb": after_snapshot.rss_mb
            }
        except Exception as e:
            logger.error(f"Failed to perform garbage collection: {e}")
            return {"error": str(e)}

    def get_peak_usage(self) -> Dict[str, float]:
        """Get peak memory usage statistics."""
        with self._lock:
            return dict(self.memory_peaks)

    def get_allocation_summary(self) -> Dict[str, float]:
        """Get memory allocation summary by component."""
        with self._lock:
            return dict(self.memory_allocations)

    def clear_history(self):
        """Clear monitoring history."""
        with self._lock:
            self.snapshots.clear()
            self.memory_allocations.clear()
            self.memory_peaks.clear()
            logger.info("Memory monitoring history cleared")

    def export_snapshots(self) -> List[Dict[str, Any]]:
        """Export all snapshots as dictionaries."""
        with self._lock:
            return [
                {
                    "label": label,
                    "timestamp": snapshot.timestamp,
                    "rss_mb": snapshot.rss_mb,
                    "vms_mb": snapshot.vms_mb,
                    "heap_mb": snapshot.heap_mb,
                    "available_mb": snapshot.available_mb,
                    "percent_used": snapshot.percent_used,
                    "process_id": snapshot.process_id,
                    "thread_count": snapshot.thread_count
                }
                for label, snapshot in self.snapshots
            ]


# Global instance for compatibility
memory_monitor = MemoryMonitor()

__all__ = [
    "MemoryMonitor",
    "MemorySnapshot",
    "MemoryMetricType",
    "memory_monitor"
]