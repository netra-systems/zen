"""Canonical monitoring schemas for type consistency.

Provides shared interfaces and base types for monitoring across domains
without disrupting valid domain-specific implementations.

Business Value Justification (BVJ):
1. Segment: All segments (Foundation)
2. Business Goal: Ensure monitoring type consistency
3. Value Impact: Reduces integration issues, improves reliability
4. Revenue Impact: Better monitoring = Higher uptime = Better value capture
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Protocol, Union
from pydantic import BaseModel, Field

from netra_backend.app.core.resilience.monitor import AlertSeverity as CanonicalAlertSeverity, HealthStatus


# === Core Monitoring Enums ===

# Use canonical AlertSeverity from resilience monitor
AlertSeverity = CanonicalAlertSeverity


class AlertLevel(str, Enum):
    """Alert level classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CircuitState(str, Enum):
    """Circuit breaker state enumeration."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class MonitoringState(str, Enum):
    """General monitoring component state."""
    INACTIVE = "inactive"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"


# === Base Alert Types ===

class BaseAlert(BaseModel):
    """Base alert schema for all alert types."""
    alert_id: str = Field(..., description="Unique alert identifier")
    timestamp: datetime = Field(..., description="Alert creation timestamp")
    severity: AlertSeverity = Field(..., description="Alert severity level")
    message: str = Field(..., description="Human-readable alert message")
    component: str = Field(..., description="Component that triggered alert")
    resolved: bool = Field(default=False, description="Alert resolution status")
    resolved_at: Optional[datetime] = Field(None, description="Resolution timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ThresholdAlert(BaseAlert):
    """Alert for threshold violations."""
    metric_name: str = Field(..., description="Metric that violated threshold")
    current_value: float = Field(..., description="Current metric value")
    threshold_value: float = Field(..., description="Threshold that was violated")
    threshold_type: str = Field(..., description="Type of threshold (>, <, ==)")


class PerformanceAlert(BaseAlert):
    """Performance-specific alert."""
    metric_name: str = Field(..., description="Performance metric name")
    current_value: float = Field(..., description="Current performance value")
    threshold: float = Field(..., description="Performance threshold")
    duration_ms: Optional[int] = Field(None, description="Duration of condition")


# === Alert Manager Protocol ===

class AlertManagerProtocol(Protocol):
    """Protocol for alert manager implementations."""
    
    def add_alert_rule(self, rule: Any) -> None:
        """Add alert rule to manager."""
        ...
    
    def remove_alert_rule(self, rule_id: str) -> bool:
        """Remove alert rule from manager."""
        ...
    
    async def resolve_alert(self, alert_id: str, resolved_by: str = "system") -> bool:
        """Mark alert as resolved."""
        ...
    
    def get_active_alerts(self) -> List[BaseAlert]:
        """Get all active alerts."""
        ...


# === Circuit Breaker Types ===

class CircuitConfig(BaseModel):
    """Circuit breaker configuration."""
    name: str = Field(..., description="Circuit breaker name")
    failure_threshold: int = Field(default=5, description="Failures before opening")
    recovery_timeout: float = Field(default=60.0, description="Timeout before recovery attempt")
    timeout_seconds: float = Field(default=30.0, description="Call timeout in seconds")
    half_open_max_calls: int = Field(default=3, description="Max calls in half-open state")


class CircuitMetrics(BaseModel):
    """Circuit breaker metrics."""
    total_calls: int = Field(default=0, description="Total calls made")
    successful_calls: int = Field(default=0, description="Successful calls")
    failed_calls: int = Field(default=0, description="Failed calls")
    rejected_calls: int = Field(default=0, description="Rejected calls")
    timeouts: int = Field(default=0, description="Timeout occurrences")
    state_changes: int = Field(default=0, description="State transition count")
    last_failure_time: Optional[float] = Field(None, description="Last failure timestamp")
    last_success_time: Optional[float] = Field(None, description="Last success timestamp")
    failure_types: Dict[str, int] = Field(default_factory=dict, description="Failure type counts")


class CircuitStatus(BaseModel):
    """Circuit breaker status information."""
    name: str = Field(..., description="Circuit breaker name")
    state: CircuitState = Field(..., description="Current circuit state")
    failure_count: int = Field(..., description="Current failure count")
    success_rate: float = Field(..., description="Success rate (0.0-1.0)")
    config: CircuitConfig = Field(..., description="Circuit configuration")
    metrics: CircuitMetrics = Field(..., description="Circuit metrics")
    health: str = Field(..., description="Health status")


# === Circuit Breaker Protocol ===

class CircuitBreakerProtocol(Protocol):
    """Protocol for circuit breaker implementations."""
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open."""
        ...
    
    def can_execute(self) -> bool:
        """Check if execution is allowed."""
        ...
    
    def record_success(self) -> None:
        """Record successful execution."""
        ...
    
    def record_failure(self, error_type: str) -> None:
        """Record failed execution."""
        ...
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        ...


# === Performance Monitor Types ===

class PerformanceThresholds(BaseModel):
    """Performance monitoring thresholds."""
    response_time_ms: float = Field(default=1000.0, description="Max response time")
    throughput_requests_per_sec: float = Field(default=100.0, description="Min throughput")
    error_rate_percent: float = Field(default=5.0, description="Max error rate")
    cpu_percent: float = Field(default=80.0, description="Max CPU usage")
    memory_percent: float = Field(default=85.0, description="Max memory usage")


class PerformanceMetric(BaseModel):
    """Performance metric data point."""
    metric_name: str = Field(..., description="Metric identifier")
    value: float = Field(..., description="Metric value")
    timestamp: datetime = Field(..., description="Measurement timestamp")
    tags: Dict[str, str] = Field(default_factory=dict, description="Metric tags")
    unit: str = Field(default="", description="Measurement unit")


class PerformanceSummary(BaseModel):
    """Performance monitoring summary."""
    timestamp: datetime = Field(..., description="Summary timestamp")
    total_requests: int = Field(default=0, description="Total requests processed")
    successful_requests: int = Field(default=0, description="Successful requests")
    failed_requests: int = Field(default=0, description="Failed requests")
    avg_response_time_ms: float = Field(default=0.0, description="Average response time")
    throughput_per_second: float = Field(default=0.0, description="Requests per second")
    error_rate_percent: float = Field(default=0.0, description="Error rate percentage")
    active_connections: int = Field(default=0, description="Active connections")


# === Performance Monitor Protocol ===

class PerformanceMonitorProtocol(Protocol):
    """Protocol for performance monitor implementations."""
    
    async def start_monitoring(self) -> None:
        """Start performance monitoring."""
        ...
    
    async def stop_monitoring(self) -> None:
        """Stop performance monitoring."""
        ...
    
    def record_request(self, duration_ms: float, success: bool) -> None:
        """Record request performance."""
        ...
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        ...


# === Database Metrics ===

class DatabaseConnectionMetrics(BaseModel):
    """Database connection metrics."""
    active_connections: int = Field(default=0, description="Active connections")
    idle_connections: int = Field(default=0, description="Idle connections")
    total_connections: int = Field(default=0, description="Total connections")
    connection_errors: int = Field(default=0, description="Connection errors")
    connection_timeouts: int = Field(default=0, description="Connection timeouts")
    pool_utilization: float = Field(default=0.0, description="Pool utilization ratio")


class DatabaseQueryMetrics(BaseModel):
    """Database query performance metrics."""
    total_queries: int = Field(default=0, description="Total queries executed")
    slow_queries: int = Field(default=0, description="Slow queries")
    failed_queries: int = Field(default=0, description="Failed queries")
    avg_query_time_ms: float = Field(default=0.0, description="Average query time")
    max_query_time_ms: float = Field(default=0.0, description="Maximum query time")
    queries_per_second: float = Field(default=0.0, description="Query throughput")


class DatabaseCacheMetrics(BaseModel):
    """Database cache metrics."""
    cache_hits: int = Field(default=0, description="Cache hits")
    cache_misses: int = Field(default=0, description="Cache misses")
    cache_size_bytes: int = Field(default=0, description="Cache size in bytes")
    cache_hit_ratio: float = Field(default=0.0, description="Cache hit ratio")
    evictions: int = Field(default=0, description="Cache evictions")


class ComprehensiveDatabaseMetrics(BaseModel):
    """Comprehensive database metrics."""
    timestamp: datetime = Field(..., description="Metrics timestamp")
    connection_metrics: DatabaseConnectionMetrics = Field(default_factory=DatabaseConnectionMetrics)
    query_metrics: DatabaseQueryMetrics = Field(default_factory=DatabaseQueryMetrics)
    cache_metrics: DatabaseCacheMetrics = Field(default_factory=DatabaseCacheMetrics)
    transaction_metrics: Dict[str, int] = Field(default_factory=dict, description="Transaction stats")
    health_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Overall health score")


# === Notification Types ===

class NotificationChannel(str, Enum):
    """Notification delivery channels."""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    LOG = "log"
    SMS = "sms"


class NotificationConfig(BaseModel):
    """Notification channel configuration."""
    channel: NotificationChannel = Field(..., description="Notification channel")
    enabled: bool = Field(default=True, description="Channel enabled status")
    endpoint: Optional[str] = Field(None, description="Channel endpoint/URL")
    credentials: Dict[str, str] = Field(default_factory=dict, description="Channel credentials")
    retry_count: int = Field(default=3, description="Retry attempts")
    timeout_seconds: int = Field(default=30, description="Request timeout")


# === System Health Types ===

# ComponentHealthStatus moved to canonical source: app.core.shared_health_types.HealthStatus


class ComponentHealth(BaseModel):
    """Individual component health status."""
    name: str = Field(..., description="Component name")
    status: HealthStatus = Field(..., description="Health status")
    health_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Health score")
    last_check: datetime = Field(..., description="Last health check time")
    error_count: int = Field(default=0, description="Recent error count")
    response_time_ms: Optional[float] = Field(None, description="Component response time")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional health details")


class SystemHealth(BaseModel):
    """Overall system health status."""
    timestamp: datetime = Field(..., description="Health check timestamp")
    overall_status: HealthStatus = Field(..., description="Overall system status")
    overall_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Overall health score")
    components: List[ComponentHealth] = Field(default_factory=list, description="Component statuses")
    active_alerts: int = Field(default=0, description="Number of active alerts")
    critical_issues: List[str] = Field(default_factory=list, description="Critical issues")


# === Export Models ===

class MonitoringExport(BaseModel):
    """Monitoring data export format."""
    export_timestamp: datetime = Field(..., description="Export timestamp")
    time_range_start: datetime = Field(..., description="Data range start")
    time_range_end: datetime = Field(..., description="Data range end")
    alerts: List[BaseAlert] = Field(default_factory=list, description="Alert data")
    performance_metrics: List[PerformanceMetric] = Field(default_factory=list, description="Performance data")
    system_health: Optional[SystemHealth] = Field(None, description="System health snapshot")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Export metadata")


# === Factory Functions ===

def create_threshold_alert(
    component: str,
    metric_name: str,
    current_value: float,
    threshold_value: float,
    severity: AlertSeverity = AlertSeverity.MEDIUM,
    alert_id: Optional[str] = None
) -> ThresholdAlert:
    """Factory function for threshold alerts."""
    alert_params = _build_threshold_alert_params(
        component, metric_name, current_value, threshold_value, severity, alert_id
    )
    return ThresholdAlert(**alert_params)

def _build_threshold_alert_params(
    component: str, metric_name: str, current_value: float, 
    threshold_value: float, severity: AlertSeverity, alert_id: Optional[str]
) -> Dict[str, Any]:
    """Build threshold alert parameters."""
    base_params = _get_base_alert_params(component, metric_name, alert_id)
    threshold_params = _get_threshold_params(current_value, threshold_value)
    return {**base_params, "severity": severity, **threshold_params}

def _get_base_alert_params(component: str, metric_name: str, alert_id: Optional[str]) -> Dict[str, Any]:
    """Get base alert parameters."""
    alert_id = alert_id or f"threshold_{component}_{metric_name}_{int(datetime.now().timestamp())}"
    return {
        "alert_id": alert_id, "timestamp": datetime.now(),
        "message": f"{component} {metric_name} threshold violation",
        "component": component, "metric_name": metric_name
    }

def _get_threshold_params(current_value: float, threshold_value: float) -> Dict[str, Any]:
    """Get threshold-specific parameters."""
    return {
        "current_value": current_value, "threshold_value": threshold_value,
        "threshold_type": ">" if current_value > threshold_value else "<"
    }


def create_performance_alert(
    component: str,
    metric_name: str,
    current_value: float,
    threshold: float,
    severity: AlertSeverity = AlertSeverity.MEDIUM,
    alert_id: Optional[str] = None
) -> PerformanceAlert:
    """Factory function for performance alerts."""
    alert_params = _build_performance_alert_params(
        component, metric_name, current_value, threshold, severity, alert_id
    )
    return PerformanceAlert(**alert_params)

def _build_performance_alert_params(
    component: str, metric_name: str, current_value: float, 
    threshold: float, severity: AlertSeverity, alert_id: Optional[str]
) -> Dict[str, Any]:
    """Build performance alert parameters."""
    base_params = _get_performance_base_params(component, metric_name, alert_id)
    performance_params = _get_performance_metrics(current_value, threshold)
    return {**base_params, "severity": severity, **performance_params}

def _get_performance_base_params(component: str, metric_name: str, alert_id: Optional[str]) -> Dict[str, Any]:
    """Get performance alert base parameters."""
    alert_id = alert_id or f"perf_{component}_{metric_name}_{int(datetime.now().timestamp())}"
    return {"alert_id": alert_id, "timestamp": datetime.now(), "component": component}

def _get_performance_metrics(current_value: float, threshold: float) -> Dict[str, Any]:
    """Get performance metrics parameters."""
    return {
        "current_value": current_value, "threshold": threshold,
        "message": f"performance issue: current = {current_value} (threshold: {threshold})"
    }