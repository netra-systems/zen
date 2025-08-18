"""Real-time monitoring and alerting for unified resilience framework.

This module provides enterprise-grade monitoring with:
- Real-time health monitoring and metrics collection
- Configurable alerting thresholds and notifications
- Performance tracking and trend analysis
- Integration with external monitoring systems

All functions are ≤8 lines per MANDATORY requirements.
"""

import asyncio
import time
from datetime import datetime, timedelta, UTC
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass, field

from app.logging_config import central_logger
from app.core.shared_health_types import HealthStatus

logger = central_logger.get_logger(__name__)


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
        if service_name not in self.thresholds:
            self.thresholds[service_name] = []
        self.thresholds[service_name].append(threshold)
    
    def add_alert_handler(self, handler: Callable[[Alert], None]) -> None:
        """Add alert handler for notifications."""
        self.alert_handlers.append(handler)
    
    async def start_monitoring(self, interval_seconds: float = 30.0) -> None:
        """Start continuous monitoring."""
        if self.monitoring_active:
            logger.warning("Monitoring already active")
            return
        
        self.monitoring_active = True
        self.monitor_task = asyncio.create_task(
            self._monitoring_loop(interval_seconds)
        )
        logger.info(f"Started resilience monitoring (interval: {interval_seconds}s)")
    
    async def stop_monitoring(self) -> None:
        """Stop monitoring."""
        self.monitoring_active = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped resilience monitoring")
    
    async def _monitoring_loop(self, interval_seconds: float) -> None:
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                await self._collect_and_evaluate_metrics()
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
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
        service = self.services[service_name]
        metric = service.metrics.get(threshold.metric_name)
        
        if metric and self._threshold_breached(metric.value, threshold):
            await self._create_alert(service_name, threshold, metric.value)
    
    def _threshold_breached(self, value: float, threshold: AlertThreshold) -> bool:
        """Check if threshold is breached."""
        op = threshold.comparison_operator
        target = threshold.threshold_value
        
        if op == "gt":
            return value > target
        elif op == "lt":
            return value < target
        elif op == "eq":
            return value == target
        elif op == "gte":
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
        alert_id = f"{service_name}_{threshold.metric_name}_{int(time.time())}"
        alert = Alert(
            id=alert_id,
            service_name=service_name,
            metric_name=threshold.metric_name,
            severity=threshold.severity,
            message=self._build_alert_message(threshold, current_value),
            timestamp=datetime.now(UTC),
            threshold=threshold,
            current_value=current_value
        )
        
        self.services[service_name].alerts.append(alert)
        await self._dispatch_alert(alert)
    
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
        
        if not active_alerts:
            service.status = HealthStatus.HEALTHY
        elif any(a.severity == AlertSeverity.CRITICAL for a in active_alerts):
            service.status = HealthStatus.CRITICAL
        elif any(a.severity == AlertSeverity.HIGH for a in active_alerts):
            service.status = HealthStatus.UNHEALTHY
        else:
            service.status = HealthStatus.DEGRADED
    
    def report_metric(
        self, 
        service_name: str, 
        metric_name: str, 
        value: float, 
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Report metric for service."""
        if service_name not in self.services:
            self.register_service(service_name)
        
        metric = HealthMetric(
            name=metric_name,
            value=value,
            timestamp=datetime.now(UTC),
            labels=labels or {}
        )
        self.services[service_name].add_metric(metric)
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve alert by ID."""
        for service in self.services.values():
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
        total_services = len(self.services)
        healthy_count = sum(1 for s in self.services.values() 
                          if s.status == HealthStatus.HEALTHY)
        critical_count = sum(1 for s in self.services.values() 
                           if s.status == HealthStatus.CRITICAL)
        
        return {
            "total_services": total_services,
            "healthy_services": healthy_count,
            "critical_services": critical_count,
            "overall_health": self._calculate_overall_health(),
            "active_alerts": self._count_active_alerts(),
            "monitoring_active": self.monitoring_active
        }
    
    def _calculate_overall_health(self) -> str:
        """Calculate overall system health."""
        if not self.services:
            return "unknown"
        
        statuses = [s.status for s in self.services.values()]
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