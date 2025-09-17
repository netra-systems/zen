"""
Monitoring models and data structures.

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: System observability and monitoring
- Value Impact: Provides structured data models for metrics and monitoring
- Revenue Impact: Critical for Enterprise monitoring and alerting
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class MetricType(str, Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class MetricUnit(str, Enum):
    """Common metric units."""
    COUNT = "count"
    BYTES = "bytes"
    SECONDS = "seconds"
    MILLISECONDS = "milliseconds"
    PERCENTAGE = "percentage"
    REQUESTS = "requests"
    ERRORS = "errors"


@dataclass
class Metric:
    """Base metric data structure."""
    name: str
    value: Union[int, float]
    metric_type: MetricType = MetricType.GAUGE
    unit: MetricUnit = MetricUnit.COUNT
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    labels: Dict[str, str] = field(default_factory=dict)
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary."""
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "unit": self.unit.value,
            "timestamp": self.timestamp.isoformat(),
            "labels": self.labels,
            "description": self.description
        }


class MetricDataPoint(BaseModel):
    """Single metric data point."""
    timestamp: datetime
    value: float
    labels: Dict[str, str] = Field(default_factory=dict)


class MetricSeries(BaseModel):
    """Time series of metric data."""
    name: str
    metric_type: MetricType
    unit: MetricUnit
    data_points: List[MetricDataPoint]
    labels: Dict[str, str] = Field(default_factory=dict)
    
    def latest_value(self) -> Optional[float]:
        """Get the latest value in the series."""
        if self.data_points:
            return max(self.data_points, key=lambda p: p.timestamp).value
        return None
    
    def average_value(self) -> Optional[float]:
        """Calculate average value."""
        if self.data_points:
            return sum(p.value for p in self.data_points) / len(self.data_points)
        return None


class AlertLevel(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Alert(BaseModel):
    """Alert model."""
    id: str
    name: str
    level: AlertLevel
    message: str
    metric_name: Optional[str] = None
    threshold_value: Optional[float] = None
    actual_value: Optional[float] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    labels: Dict[str, str] = Field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class MonitoringDashboard(BaseModel):
    """Dashboard configuration."""
    id: str
    name: str
    description: str
    panels: List[Dict[str, Any]]
    refresh_interval: int = 30  # seconds
    time_range: str = "1h"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HealthCheck(BaseModel):
    """Health check result."""
    service: str
    status: str  # healthy, degraded, unhealthy
    latency_ms: float
    checks: Dict[str, bool]
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MetricsCollector:
    """Collector for system metrics"""
    def __init__(self):
        self.metrics = []
    
    def collect(self, metric: Metric):
        """Collect a metric"""
        self.metrics.append(metric)
    
    def get_metrics(self) -> List[Metric]:
        """Get collected metrics"""
        return self.metrics
    
    def clear(self):
        """Clear collected metrics"""
        self.metrics = []


@dataclass
class ResourcePrediction:
    """Resource usage prediction data."""
    resource_type: str
    current_usage: float
    predicted_usage: float
    prediction_time: datetime
    confidence_score: float
    time_to_exhaustion_seconds: Optional[float] = None


@dataclass
class TrendAnalysis:
    """Trend analysis for resource usage."""
    trend_direction: str  # "increasing", "decreasing", "stable"
    growth_rate: float
    variance: float
    correlation_coefficient: float
    prediction_accuracy: float


__all__ = [
    'Metric',
    'MetricType',
    'MetricUnit',
    'MetricDataPoint',
    'MetricSeries',
    'AlertLevel',
    'Alert',
    'MonitoringDashboard',
    'HealthCheck',
    'MetricsCollector',
    'ResourcePrediction',
    'TrendAnalysis'
]