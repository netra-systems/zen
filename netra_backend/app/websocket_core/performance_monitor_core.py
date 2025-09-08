# Shim module for backward compatibility
from netra_backend.app.monitoring.performance_metrics import PerformanceMonitor
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

# Legacy alias for backward compatibility
WebSocketPerformanceMonitor = PerformanceMonitor

# Additional classes needed by unit tests
@dataclass
class PerformanceMetrics:
    """Performance metrics for WebSocket operations."""
    latency_ms: float = 0.0
    throughput_msgs_per_sec: float = 0.0
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    active_connections: int = 0
    error_rate_percent: float = 0.0
    timestamp: Optional[datetime] = None

@dataclass
class LatencyMeasurement:
    """Latency measurement data."""
    min_ms: float = 0.0
    max_ms: float = 0.0
    avg_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0

@dataclass 
class ThroughputMetrics:
    """Throughput metrics data."""
    messages_per_second: float = 0.0
    bytes_per_second: float = 0.0
    peak_messages_per_second: float = 0.0
    total_messages: int = 0

class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class PerformanceAlert:
    """Performance alert data."""
    severity: AlertSeverity
    message: str
    metric_name: str
    current_value: float
    threshold_value: float
    timestamp: Optional[datetime] = None

@dataclass
class PerformanceThresholds:
    """Performance thresholds configuration."""
    max_latency_ms: float = 1000.0
    min_throughput_msgs_per_sec: float = 10.0
    max_cpu_usage_percent: float = 80.0
    max_memory_usage_mb: float = 512.0
    max_error_rate_percent: float = 5.0
