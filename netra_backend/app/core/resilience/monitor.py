"""Real-time monitoring and alerting for unified resilience framework.

This module provides enterprise-grade monitoring with:
- Real-time health monitoring and metrics collection
- Configurable alerting thresholds and notifications
- Performance tracking and trend analysis
- Integration with external monitoring systems

All functions are  <= 8 lines per MANDATORY requirements.
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class HealthStatus(Enum):
    """Health status for monitoring - local definition to avoid circular imports."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    CRITICAL = "critical"


class AlertSeverity(Enum):
    """Alert severity levels for enterprise monitoring."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AlertThreshold:
    """Configuration for alert thresholds."""
    metric_name: str
    threshold_value: float
    comparison_operator: str  # "gt", "lt", "eq", "gte", "lte"
    severity: AlertSeverity
    window_minutes: int = 5
    min_samples: int = 3
    
    def __post_init__(self) -> None:
        """Validate threshold configuration."""
        self._validate_operator()
        self._validate_window()
    
    def _validate_operator(self) -> None:
        """Validate comparison operator."""
        valid_ops = {"gt", "lt", "eq", "gte", "lte"}
        if self.comparison_operator not in valid_ops:
            raise ValueError(f"Invalid operator: {self.comparison_operator}")
    
    def _validate_window(self) -> None:
        """Validate window parameters."""
        if self.window_minutes <= 0:
            raise ValueError("window_minutes must be positive")
        if self.min_samples <= 0:
            raise ValueError("min_samples must be positive")


@dataclass
class Alert:
    """Alert information for monitoring events."""
    id: str
    service_name: str
    metric_name: str
    severity: AlertSeverity
    message: str
    timestamp: datetime
    threshold: AlertThreshold
    current_value: float
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class HealthMetric:
    """Health metric data point."""
    name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    
    def age_minutes(self) -> float:
        """Get metric age in minutes."""
        return (datetime.now(UTC) - self.timestamp).total_seconds() / 60.0


@dataclass
class ServiceHealth:
    """Health status for a service."""
    service_name: str
    status: HealthStatus
    last_updated: datetime
    metrics: Dict[str, HealthMetric] = field(default_factory=dict)
    alerts: List[Alert] = field(default_factory=list)
    
    def add_metric(self, metric: HealthMetric) -> None:
        """Add or update metric."""
        self.metrics[metric.name] = metric
        self.last_updated = datetime.now(UTC)
    
    def get_active_alerts(self) -> List[Alert]:
        """Get unresolved alerts."""
        return [alert for alert in self.alerts if not alert.resolved]


class UnifiedResilienceMonitor:
    """Enterprise resilience monitoring system."""
    
    def __init__(self) -> None:
        self.services: Dict[str, ServiceHealth] = {}
        self.alert_handlers: List[Callable[[Alert], None]] = []
        self.thresholds: Dict[str, List[AlertThreshold]] = {}
        self.monitoring_active = False
        self.monitor_task: Optional[asyncio.Task] = None
    
    def register_service(self, service_name: str) -> None:
        """Register service for monitoring."""
        self.services[service_name] = ServiceHealth(
            service_name=service_name,
            status=HealthStatus.HEALTHY,
            last_updated=datetime.now(UTC)
        )
        logger.info(f"Registered service for monitoring: {service_name}")
    
    def add_alert_threshold(
        self, 
        service_name: str, 
        threshold: AlertThreshold
    ) -> None:
        """Add alert threshold for service."""
        self._ensure_threshold_list_exists(service_name)
        self.thresholds[service_name].append(threshold)
    
    def _ensure_threshold_list_exists(self, service_name: str) -> None:
        """Ensure threshold list exists for service."""
        if service_name not in self.thresholds:
            self.thresholds[service_name] = []
    
    def add_alert_handler(self, handler: Callable[[Alert], None]) -> None:
        """Add alert handler for notifications."""
        self.alert_handlers.append(handler)
    
    async def start_monitoring(self, interval_seconds: float = 30.0) -> None:
        """Start continuous monitoring."""
        if self._is_monitoring_already_active():
            return
        
        self._activate_monitoring(interval_seconds)
        logger.info(f"Started resilience monitoring (interval: {interval_seconds}s)")
    
    def _is_monitoring_already_active(self) -> bool:
        """Check if monitoring is already active."""
        if self.monitoring_active:
            logger.warning("Monitoring already active")
            return True
        return False
    
    def _activate_monitoring(self, interval_seconds: float) -> None:
        """Activate monitoring with given interval."""
        self.monitoring_active = True
        self.monitor_task = asyncio.create_task(
            self._monitoring_loop(interval_seconds)
        )
    
    async def stop_monitoring(self) -> None:
        """Stop monitoring."""
        self.monitoring_active = False
        await self._cancel_monitor_task()
        logger.info("Stopped resilience monitoring")
    
    async def _cancel_monitor_task(self) -> None:
        """Cancel active monitoring task."""
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
    
    async def _monitoring_loop(self, interval_seconds: float) -> None:
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                await self._execute_monitoring_cycle(interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                await self._handle_monitoring_error(e, interval_seconds)
    
    async def _execute_monitoring_cycle(self, interval_seconds: float) -> None:
        """Execute one monitoring cycle."""
        await self._collect_and_evaluate_metrics()
        await asyncio.sleep(interval_seconds)
    
    async def _handle_monitoring_error(self, error: Exception, interval_seconds: float) -> None:
        """Handle monitoring loop error."""
        logger.error(f"Monitoring loop error: {error}")
        await asyncio.sleep(interval_seconds)
    
    async def _collect_and_evaluate_metrics(self) -> None:
        """Collect metrics and evaluate alert conditions."""
        for service_name in self.services.keys():
            try:
                await self._evaluate_service_alerts(service_name)
                self._update_service_health(service_name)
            except Exception as e:
                logger.error(f"Error evaluating service {service_name}: {e}")
    
    async def _evaluate_service_alerts(self, service_name: str) -> None:
        """Evaluate alert conditions for service."""
        thresholds = self.thresholds.get(service_name, [])
        for threshold in thresholds:
            await self._check_threshold_condition(service_name, threshold)
    
    async def _check_threshold_condition(
        self, 
        service_name: str, 
        threshold: AlertThreshold
    ) -> None:
        """Check if threshold condition is met."""
        metric = self._get_service_metric(service_name, threshold.metric_name)
        if self._should_create_alert(metric, threshold):
            await self._create_alert(service_name, threshold, metric.value)
    
    def _get_service_metric(self, service_name: str, metric_name: str) -> Optional[HealthMetric]:
        """Get metric from service."""
        service = self.services[service_name]
        return service.metrics.get(metric_name)
    
    def _should_create_alert(self, metric: Optional[HealthMetric], threshold: AlertThreshold) -> bool:
        """Check if alert should be created."""
        return metric is not None and self._threshold_breached(metric.value, threshold)
    
    def _threshold_breached(self, value: float, threshold: AlertThreshold) -> bool:
        """Check if threshold is breached."""
        op = threshold.comparison_operator
        target = threshold.threshold_value
        return self._evaluate_threshold_condition(value, op, target)
    
    def _evaluate_threshold_condition(self, value: float, op: str, target: float) -> bool:
        """Evaluate specific threshold condition."""
        basic_result = self._evaluate_basic_conditions(value, op, target)
        if basic_result is not None:
            return basic_result
        return self._evaluate_gte_lte_condition(value, op, target)
    
    def _evaluate_basic_conditions(self, value: float, op: str, target: float) -> Optional[bool]:
        """Evaluate basic threshold conditions."""
        if op == "gt":
            return value > target
        elif op == "lt":
            return value < target
        elif op == "eq":
            return value == target
        return None
    
    def _evaluate_gte_lte_condition(self, value: float, op: str, target: float) -> bool:
        """Evaluate gte/lte threshold conditions."""
        if op == "gte":
            return value >= target
        elif op == "lte":
            return value <= target
        return False
    
    async def _create_alert(
        self, 
        service_name: str, 
        threshold: AlertThreshold, 
        current_value: float
    ) -> None:
        """Create and dispatch alert."""
        alert = self._build_alert_object(service_name, threshold, current_value)
        self._add_alert_to_service(service_name, alert)
        await self._dispatch_alert(alert)
    
    def _add_alert_to_service(self, service_name: str, alert: Alert) -> None:
        """Add alert to service."""
        self.services[service_name].alerts.append(alert)
    
    def _build_alert_object(
        self, 
        service_name: str, 
        threshold: AlertThreshold, 
        current_value: float
    ) -> Alert:
        """Build alert object."""
        alert_id = self._generate_alert_id(service_name, threshold.metric_name)
        return self._create_alert_instance(
            alert_id, service_name, threshold, current_value
        )
    
    def _generate_alert_id(self, service_name: str, metric_name: str) -> str:
        """Generate unique alert ID."""
        return f"{service_name}_{metric_name}_{int(time.time())}"
    
    def _create_alert_instance(
        self, 
        alert_id: str, 
        service_name: str, 
        threshold: AlertThreshold, 
        current_value: float
    ) -> Alert:
        """Create Alert instance."""
        return Alert(
            id=alert_id,
            service_name=service_name,
            metric_name=threshold.metric_name,
            severity=threshold.severity,
            message=self._build_alert_message(threshold, current_value),
            timestamp=datetime.now(UTC),
            threshold=threshold,
            current_value=current_value
        )
    
    def _build_alert_message(
        self, 
        threshold: AlertThreshold, 
        current_value: float
    ) -> str:
        """Build alert message."""
        return (f"{threshold.metric_name} is {current_value:.2f}, "
                f"threshold: {threshold.comparison_operator} {threshold.threshold_value}")
    
    async def _dispatch_alert(self, alert: Alert) -> None:
        """Dispatch alert to all handlers."""
        for handler in self.alert_handlers:
            await self._execute_alert_handler(handler, alert)
    
    async def _execute_alert_handler(self, handler: Callable[[Alert], None], alert: Alert) -> None:
        """Execute single alert handler."""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(alert)
            else:
                handler(alert)
        except Exception as e:
            logger.error(f"Alert handler error: {e}")
    
    def _update_service_health(self, service_name: str) -> None:
        """Update overall service health status."""
        service = self.services[service_name]
        active_alerts = service.get_active_alerts()
        service.status = self._determine_health_status(active_alerts)
    
    def _determine_health_status(self, active_alerts: List[Alert]) -> HealthStatus:
        """Determine health status from active alerts."""
        if not active_alerts:
            return HealthStatus.HEALTHY
        elif any(a.severity == AlertSeverity.CRITICAL for a in active_alerts):
            return HealthStatus.CRITICAL
        elif any(a.severity == AlertSeverity.HIGH for a in active_alerts):
            return HealthStatus.UNHEALTHY
        return HealthStatus.DEGRADED
    
    def report_metric(
        self, 
        service_name: str, 
        metric_name: str, 
        value: float, 
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Report metric for service."""
        self._ensure_service_registered(service_name)
        metric = self._create_health_metric(metric_name, value, labels)
        self._add_metric_to_service(service_name, metric)
    
    def _add_metric_to_service(self, service_name: str, metric: HealthMetric) -> None:
        """Add metric to service."""
        self.services[service_name].add_metric(metric)
    
    def _ensure_service_registered(self, service_name: str) -> None:
        """Ensure service is registered."""
        if service_name not in self.services:
            self.register_service(service_name)
    
    def _create_health_metric(
        self, 
        metric_name: str, 
        value: float, 
        labels: Optional[Dict[str, str]]
    ) -> HealthMetric:
        """Create health metric object."""
        return HealthMetric(
            name=metric_name,
            value=value,
            timestamp=datetime.now(UTC),
            labels=self._get_safe_labels(labels)
        )
    
    def _get_safe_labels(self, labels: Optional[Dict[str, str]]) -> Dict[str, str]:
        """Get safe labels dict."""
        return labels or {}
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve alert by ID."""
        for service in self.services.values():
            if self._try_resolve_alert_in_service(service, alert_id):
                return True
        return False
    
    def _try_resolve_alert_in_service(self, service: ServiceHealth, alert_id: str) -> bool:
        """Try to resolve alert in service."""
        for alert in service.alerts:
            if alert.id == alert_id and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = datetime.now(UTC)
                logger.info(f"Resolved alert: {alert_id}")
                return True
        return False
    
    def get_service_health(self, service_name: str) -> Optional[ServiceHealth]:
        """Get health status for service."""
        return self.services.get(service_name)
    
    def get_all_services_health(self) -> Dict[str, ServiceHealth]:
        """Get health status for all services."""
        return self.services.copy()
    
    def get_system_health_summary(self) -> Dict[str, Any]:
        """Get system-wide health summary."""
        service_counts = self._calculate_service_counts()
        return {
            **service_counts,
            "overall_health": self._calculate_overall_health(),
            "active_alerts": self._count_active_alerts(),
            "monitoring_active": self.monitoring_active
        }
    
    def _calculate_service_counts(self) -> Dict[str, int]:
        """Calculate service count statistics."""
        total_services = len(self.services)
        healthy_count = self._count_healthy_services()
        critical_count = self._count_critical_services()
        return {
            "total_services": total_services,
            "healthy_services": healthy_count,
            "critical_services": critical_count
        }
    
    def _count_healthy_services(self) -> int:
        """Count healthy services."""
        return sum(1 for s in self.services.values() 
                  if s.status == HealthStatus.HEALTHY)
    
    def _count_critical_services(self) -> int:
        """Count critical services."""
        return sum(1 for s in self.services.values() 
                  if s.status == HealthStatus.CRITICAL)
    
    def _calculate_overall_health(self) -> str:
        """Calculate overall system health."""
        if not self.services:
            return "unknown"
        
        statuses = [s.status for s in self.services.values()]
        return self._determine_overall_health_from_statuses(statuses)
    
    def _determine_overall_health_from_statuses(self, statuses: List[HealthStatus]) -> str:
        """Determine overall health from status list."""
        if all(s == HealthStatus.HEALTHY for s in statuses):
            return "healthy"
        elif any(s == HealthStatus.CRITICAL for s in statuses):
            return "critical"
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            return "unhealthy"
        return "degraded"
    
    def _count_active_alerts(self) -> int:
        """Count total active alerts."""
        return sum(len(service.get_active_alerts()) for service in self.services.values())


# Global monitoring instance
resilience_monitor = UnifiedResilienceMonitor()


async def default_alert_handler(alert: Alert) -> None:
    """Default alert handler that logs alerts."""
    logger.warning(
        f"Resilience Alert [{alert.severity.value.upper()}] "
        f"{alert.service_name}.{alert.metric_name}: {alert.message}"
    )


# Set up default alert handler
resilience_monitor.add_alert_handler(default_alert_handler)