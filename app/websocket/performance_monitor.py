"""WebSocket Performance Monitoring - Modular Implementation.

Backward-compatible interface using optimized micro-function modules.
"""

# Import from modular implementation for backward compatibility
from .performance_monitor_types import (
    MetricType, AlertSeverity, MetricPoint, Alert, PerformanceThresholds
)
from .performance_monitor_collector import MetricCollector
from .performance_monitor_core import PerformanceMonitor

# Maintain backward compatibility by exposing all classes at module level
__all__ = [
    'MetricType', 'AlertSeverity', 'MetricPoint', 'Alert', 
    'PerformanceThresholds', 'MetricCollector', 'PerformanceMonitor'
]