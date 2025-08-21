"""WebSocket Performance Monitoring - Modular Implementation.

Backward-compatible interface using optimized micro-function modules.
"""

# Import from modular implementation for backward compatibility
from netra_backend.app.performance_monitor_collector import MetricCollector
from netra_backend.app.performance_monitor_core import PerformanceMonitor
from netra_backend.app.performance_monitor_types import (
    Alert,
    AlertSeverity,
    MetricPoint,
    MetricType,
    PerformanceThresholds,
)

# Maintain backward compatibility by exposing all classes at module level
__all__ = [
    'MetricType', 'AlertSeverity', 'MetricPoint', 'Alert', 
    'PerformanceThresholds', 'MetricCollector', 'PerformanceMonitor'
]