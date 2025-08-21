"""Memory recovery utility functions and helpers.

Provides memory metric collection, system monitoring utilities,
and result building helpers for memory recovery operations.
"""

import gc
from datetime import datetime
from typing import Tuple

from netra_backend.app.core.memory_recovery_base import MemoryPressureLevel, MemorySnapshot, MemoryThresholds


def get_system_memory_metrics() -> Tuple[float, float, float, float]:
    """Get system memory metrics from psutil or fallback values."""
    try:
        return _get_psutil_memory_metrics()
    except ImportError:
        return _get_fallback_memory_metrics()


def _get_psutil_memory_metrics() -> Tuple[float, float, float, float]:
    """Get memory metrics using psutil."""
    import psutil
    memory = psutil.virtual_memory()
    total_mb = memory.total / 1024 / 1024
    available_mb = memory.available / 1024 / 1024
    used_mb = memory.used / 1024 / 1024
    return total_mb, available_mb, used_mb, memory.percent


def _get_fallback_memory_metrics() -> Tuple[float, float, float, float]:
    """Get fallback memory metrics when psutil unavailable."""
    total_mb = 8192.0  # Assume 8GB
    percent_used = 50.0
    available_mb = total_mb * (100 - percent_used) / 100
    used_mb = total_mb - available_mb
    return total_mb, available_mb, used_mb, percent_used


def get_process_memory_metrics() -> Tuple[float, float]:
    """Get process memory metrics from psutil or fallback values."""
    try:
        import psutil
        process = psutil.Process()
        process_memory = process.memory_info()
        return _convert_process_memory_to_mb(process_memory)
    except ImportError:
        return 512.0, 1024.0

def _convert_process_memory_to_mb(process_memory) -> Tuple[float, float]:
    """Convert process memory info to MB."""
    rss_mb = process_memory.rss / 1024 / 1024
    vms_mb = process_memory.vms / 1024 / 1024
    return rss_mb, vms_mb


def get_python_memory_metrics() -> Tuple[Tuple[int, int, int], int]:
    """Get Python-specific memory metrics."""
    gc_counts = gc.get_count()
    object_count = len(gc.get_objects())
    return gc_counts, object_count


def get_current_process_memory_mb() -> float:
    """Get current process memory usage in MB."""
    try:
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    except ImportError:
        return 0.0


def calculate_pressure_level(percent_used: float, thresholds: MemoryThresholds) -> MemoryPressureLevel:
    """Calculate memory pressure level based on usage percentage."""
    if percent_used >= thresholds.emergency_percent:
        return MemoryPressureLevel.EMERGENCY
    elif percent_used >= thresholds.critical_percent:
        return MemoryPressureLevel.CRITICAL
    elif percent_used >= thresholds.high_percent:
        return MemoryPressureLevel.HIGH
    return _calculate_lower_pressure_levels(percent_used, thresholds)

def _calculate_lower_pressure_levels(percent_used: float, thresholds: MemoryThresholds) -> MemoryPressureLevel:
    """Calculate moderate or low pressure levels."""
    if percent_used >= thresholds.moderate_percent:
        return MemoryPressureLevel.MODERATE
    return MemoryPressureLevel.LOW


def create_memory_snapshot(
    timestamp: datetime, total_mb: float, available_mb: float, used_mb: float,
    percent_used: float, pressure_level: MemoryPressureLevel, gc_counts: Tuple[int, int, int],
    object_count: int, rss_mb: float, vms_mb: float
) -> MemorySnapshot:
    """Create memory snapshot object with all metrics."""
    return _build_memory_snapshot(
        timestamp, total_mb, available_mb, used_mb, percent_used,
        pressure_level, gc_counts, object_count, rss_mb, vms_mb
    )

def _build_memory_snapshot(
    timestamp: datetime, total_mb: float, available_mb: float, used_mb: float,
    percent_used: float, pressure_level: MemoryPressureLevel, gc_counts: Tuple[int, int, int],
    object_count: int, rss_mb: float, vms_mb: float
) -> MemorySnapshot:
    """Build MemorySnapshot object."""
    return MemorySnapshot(
        timestamp=timestamp, total_mb=total_mb, available_mb=available_mb,
        used_mb=used_mb, percent_used=percent_used, pressure_level=pressure_level,
        gc_counts=gc_counts, object_count=object_count, rss_mb=rss_mb, vms_mb=vms_mb
    )


def collect_all_memory_metrics() -> Tuple[datetime, float, float, float, float, float, float, Tuple[int, int, int], int]:
    """Collect comprehensive memory metrics for snapshot creation."""
    timestamp = datetime.now()
    total_mb, available_mb, used_mb, percent_used = get_system_memory_metrics()
    rss_mb, vms_mb = get_process_memory_metrics()
    gc_counts, object_count = get_python_memory_metrics()
    return timestamp, total_mb, available_mb, used_mb, percent_used, rss_mb, vms_mb, gc_counts, object_count