"""
Monitoring Types: Single Source of Truth for Metrics Collection and Monitoring Models

This module contains all monitoring and metrics-related models used across 
the Netra platform, ensuring consistency and preventing duplication.

CRITICAL ARCHITECTURAL COMPLIANCE:
- All monitoring model definitions MUST be imported from this module
- NO duplicate monitoring model definitions allowed anywhere else in codebase
- This file maintains strong typing and single sources of truth
- Maximum file size: 300 lines (currently under limit)

Usage:
    from netra_backend.app.schemas.monitoring_types import MetricsCollector, MetricData, AlertConfig

Business Value Justification (BVJ):
- Segment: Enterprise & Growth
- Business Goal: Ensure 99.9% uptime for customer retention
- Value Impact: Prevents $50K MRR loss from monitoring blind spots
- Revenue Impact: +$50K MRR retained through reliability
"""

import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol, Union

from pydantic import BaseModel, Field


class MetricType(str, Enum):
    """Types of metrics that can be collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"
    SUMMARY = "summary"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MonitoringStatus(str, Enum):
    """Status of monitoring systems."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    RECOVERING = "recovering"


class MetricData(BaseModel):
    """Standard metric data structure."""
    name: str = Field(..., description="Metric name")
    value: Union[int, float] = Field(..., description="Metric value")
    metric_type: MetricType = Field(..., description="Type of metric")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tags: Dict[str, str] = Field(default_factory=dict, description="Metric tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class AlertRule(BaseModel):
    """Alert rule configuration."""
    name: str = Field(..., description="Rule name")
    metric_name: str = Field(..., description="Metric to monitor")
    threshold: Union[int, float] = Field(..., description="Alert threshold")
    operator: str = Field(..., description="Comparison operator (>, <, ==, etc.)")
    severity: AlertSeverity = Field(..., description="Alert severity")
    enabled: bool = Field(default=True, description="Whether rule is enabled")
    cooldown_seconds: int = Field(default=300, description="Cooldown period")


class AlertEvent(BaseModel):
    """Alert event data."""
    rule_name: str = Field(..., description="Alert rule that triggered")
    metric_name: str = Field(..., description="Metric that triggered alert")
    current_value: Union[int, float] = Field(..., description="Current metric value")
    threshold: Union[int, float] = Field(..., description="Alert threshold")
    severity: AlertSeverity = Field(..., description="Alert severity")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = Field(default=False, description="Whether alert is resolved")
    message: Optional[str] = Field(None, description="Alert message")


@dataclass
class SystemStats:
    """System performance statistics."""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_percent: float = 0.0
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0
    process_count: int = 0
    load_average: List[float] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# PerformanceMetrics moved to shared.types.performance_metrics for SSOT compliance
from shared.types.performance_metrics import PerformanceMetrics


class MonitoringConfig(BaseModel):
    """Configuration for monitoring systems."""
    retention_period: int = Field(default=3600, description="Data retention in seconds")
    collection_interval: float = Field(default=5.0, description="Collection interval in seconds")
    buffer_size: int = Field(default=1000, description="Buffer size for metrics")
    enable_alerts: bool = Field(default=True, description="Enable alerting")
    enable_system_monitoring: bool = Field(default=True, description="Enable system monitoring")
    alert_rules: List[AlertRule] = Field(default_factory=list, description="Alert rules")


class MetricsCollectorProtocol(Protocol):
    """Protocol for metrics collection implementations."""
    
    def record_metric(self, name: str, value: Union[int, float], tags: Optional[Dict[str, str]] = None) -> None:
        """Record a metric value."""
        ...
    
    def increment_counter(self, name: str, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        ...
    
    def record_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a histogram value."""
        ...
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        ...


class MonitoringInterface(Protocol):
    """Interface for monitoring implementations."""
    
    async def start_monitoring(self) -> None:
        """Start monitoring process."""
        ...
    
    async def stop_monitoring(self) -> None:
        """Stop monitoring process."""
        ...
    
    def get_status(self) -> MonitoringStatus:
        """Get current monitoring status."""
        ...


class HealthCheckResult(BaseModel):
    """Result of a health check."""
    service_name: str = Field(..., description="Name of the service")
    status: str = Field(..., description="Health status")
    response_time_ms: float = Field(..., description="Response time in milliseconds")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")


class ExecutionMetrics(BaseModel):
    """Metrics for operation execution."""
    operation_name: str = Field(..., description="Name of the operation")
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")
    success: bool = Field(..., description="Whether operation was successful")
    memory_usage_mb: Optional[float] = Field(None, description="Memory usage in MB")
    cpu_usage_percent: Optional[float] = Field(None, description="CPU usage percentage")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class QualityMetrics(BaseModel):
    """Quality metrics for services and operations."""
    availability_percent: float = Field(default=100.0, ge=0.0, le=100.0)
    reliability_percent: float = Field(default=100.0, ge=0.0, le=100.0)
    performance_score: float = Field(default=100.0, ge=0.0, le=100.0)
    error_rate_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    customer_satisfaction: Optional[float] = Field(None, ge=0.0, le=10.0)
    sla_compliance_percent: float = Field(default=100.0, ge=0.0, le=100.0)


class DashboardConfig(BaseModel):
    """Configuration for monitoring dashboards."""
    name: str = Field(..., description="Dashboard name")
    metrics: List[str] = Field(..., description="Metrics to display")
    refresh_interval: int = Field(default=30, description="Refresh interval in seconds")
    time_range: str = Field(default="1h", description="Time range for data display")
    charts: List[Dict[str, Any]] = Field(default_factory=list, description="Chart configurations")
    alerts_enabled: bool = Field(default=True, description="Enable alerts on dashboard")


# Export all monitoring types
__all__ = [
    "MetricType",
    "AlertSeverity",
    "MonitoringStatus",
    "MetricData",
    "AlertRule",
    "AlertEvent",
    "SystemStats",
    "PerformanceMetrics",
    "MonitoringConfig",
    "MetricsCollectorProtocol",
    "MonitoringInterface",
    "HealthCheckResult",
    "ExecutionMetrics",
    "QualityMetrics",
    "DashboardConfig"
]