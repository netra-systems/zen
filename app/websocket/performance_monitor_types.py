"""WebSocket Performance Monitor Types and Data Models.

Core data structures and enums for performance monitoring system.
"""

from datetime import datetime
from typing import Dict
from dataclasses import dataclass, field
from enum import Enum

from app.core.resilience.monitor import AlertSeverity


class MetricType(str, Enum):
    """Types of metrics collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"




@dataclass
class MetricPoint:
    """Single metric data point."""
    timestamp: datetime
    value: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class Alert:
    """Performance alert."""
    metric_name: str
    severity: AlertSeverity
    message: str
    threshold: float
    current_value: float
    timestamp: datetime
    resolved: bool = False
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class PerformanceThresholds:
    """Performance monitoring thresholds."""
    max_response_time_ms: float = 1000.0
    max_memory_usage_mb: float = 500.0
    max_connection_errors_per_minute: int = 10
    max_message_queue_size: int = 1000
    min_throughput_messages_per_second: float = 10.0
    max_cpu_usage_percent: float = 80.0
    max_heartbeat_failures_per_minute: int = 5