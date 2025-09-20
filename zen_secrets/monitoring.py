"""
Secret Management Monitoring and Alerting

This module provides comprehensive monitoring and alerting for the secret management system:
- Real-time metrics collection and export
- Security event detection and alerting
- Audit logging and compliance tracking
- Performance monitoring and optimization
- Integration with external monitoring systems
"""

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from uuid import uuid4

from .core import SecretConfig
from .exceptions import SecretManagerError

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types of metrics tracked."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class Alert:
    """Represents a security or operational alert."""
    id: str
    title: str
    description: str
    severity: AlertSeverity
    timestamp: datetime
    secret_name: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "secret_name": self.secret_name,
            "user_id": self.user_id,
            "metadata": self.metadata,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None
        }


@dataclass
class Metric:
    """Represents a monitoring metric."""
    name: str
    type: MetricType
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)

    def to_prometheus_format(self) -> str:
        """Convert metric to Prometheus format."""
        labels_str = ""
        if self.labels:
            label_pairs = [f'{k}="{v}"' for k, v in self.labels.items()]
            labels_str = f"{{{','.join(label_pairs)}}}"

        return f"{self.name}{labels_str} {self.value} {int(self.timestamp.timestamp() * 1000)}"


class AnomalyDetector:
    """Detects anomalous patterns in secret access and operations."""

    def __init__(self, config: SecretConfig):
        self.config = config
        self.access_patterns: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.baseline_metrics: Dict[str, Dict[str, float]] = {}
        self._learning_period = timedelta(days=7)

    def record_access(self, secret_name: str, user_id: Optional[str],
                     operation: str, timestamp: datetime) -> Optional[Alert]:
        """Record a secret access and detect anomalies."""
        access_key = f"{secret_name}:{user_id or 'system'}"
        self.access_patterns[access_key].append({
            "operation": operation,
            "timestamp": timestamp,
            "hour": timestamp.hour,
            "day_of_week": timestamp.weekday()
        })

        # Check for anomalies
        return self._detect_access_anomaly(secret_name, user_id, operation, timestamp)

    def _detect_access_anomaly(self, secret_name: str, user_id: Optional[str],
                              operation: str, timestamp: datetime) -> Optional[Alert]:
        """Detect anomalous access patterns."""
        access_key = f"{secret_name}:{user_id or 'system'}"
        recent_accesses = list(self.access_patterns[access_key])

        if len(recent_accesses) < 10:  # Not enough data
            return None

        # Check for unusual time patterns
        current_hour = timestamp.hour
        hour_accesses = [a for a in recent_accesses[-100:] if a["hour"] == current_hour]

        if len(hour_accesses) < 3:  # Unusual time access
            if current_hour < 6 or current_hour > 22:  # Outside business hours
                return Alert(
                    id=str(uuid4()),
                    title="Unusual Time Access",
                    description=f"Secret '{secret_name}' accessed at unusual hour {current_hour}:00",
                    severity=AlertSeverity.MEDIUM,
                    timestamp=timestamp,
                    secret_name=secret_name,
                    user_id=user_id,
                    metadata={
                        "operation": operation,
                        "hour": current_hour,
                        "pattern": "unusual_time"
                    }
                )

        # Check for high frequency access
        recent_window = timestamp - timedelta(minutes=10)
        recent_count = len([a for a in recent_accesses if a["timestamp"] > recent_window])

        if recent_count > 50:  # Too many accesses in short time
            return Alert(
                id=str(uuid4()),
                title="High Frequency Access",
                description=f"Secret '{secret_name}' accessed {recent_count} times in 10 minutes",
                severity=AlertSeverity.HIGH,
                timestamp=timestamp,
                secret_name=secret_name,
                user_id=user_id,
                metadata={
                    "operation": operation,
                    "access_count": recent_count,
                    "pattern": "high_frequency"
                }
            )

        return None


class MetricsCollector:
    """Collects and manages metrics for the secret management system."""

    def __init__(self, config: SecretConfig):
        self.config = config
        self.metrics: List[Metric] = []
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.timers: Dict[str, List[float]] = defaultdict(list)

        # Cleanup old metrics periodically
        self._cleanup_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """Initialize the metrics collector."""
        self._cleanup_task = asyncio.create_task(self._cleanup_old_metrics())

    def increment_counter(self, name: str, value: float = 1.0,
                         labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        key = self._make_metric_key(name, labels)
        self.counters[key] += value
        self._add_metric(name, MetricType.COUNTER, self.counters[key], labels)

    def set_gauge(self, name: str, value: float,
                  labels: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric."""
        key = self._make_metric_key(name, labels)
        self.gauges[key] = value
        self._add_metric(name, MetricType.GAUGE, value, labels)

    def record_histogram(self, name: str, value: float,
                        labels: Optional[Dict[str, str]] = None) -> None:
        """Record a histogram value."""
        key = self._make_metric_key(name, labels)
        self.histograms[key].append(value)
        # Keep only recent values
        if len(self.histograms[key]) > 1000:
            self.histograms[key] = self.histograms[key][-1000:]
        self._add_metric(name, MetricType.HISTOGRAM, value, labels)

    def record_timer(self, name: str, duration: float,
                    labels: Optional[Dict[str, str]] = None) -> None:
        """Record a timer duration in seconds."""
        self.record_histogram(f"{name}_duration_seconds", duration, labels)

    def timer(self, name: str, labels: Optional[Dict[str, str]] = None):
        """Context manager for timing operations."""
        return TimerContext(self, name, labels)

    def _add_metric(self, name: str, metric_type: MetricType, value: float,
                   labels: Optional[Dict[str, str]] = None) -> None:
        """Add a metric to the collection."""
        metric = Metric(
            name=name,
            type=metric_type,
            value=value,
            timestamp=datetime.utcnow(),
            labels=labels or {}
        )
        self.metrics.append(metric)

    def _make_metric_key(self, name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """Create a unique key for a metric with labels."""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}[{label_str}]"

    async def _cleanup_old_metrics(self) -> None:
        """Periodically clean up old metrics."""
        while True:
            try:
                cutoff_time = datetime.utcnow() - timedelta(hours=1)
                self.metrics = [m for m in self.metrics if m.timestamp > cutoff_time]
                await asyncio.sleep(300)  # Clean up every 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics cleanup: {str(e)}")
                await asyncio.sleep(60)

    def get_metrics_snapshot(self) -> List[Dict[str, Any]]:
        """Get a snapshot of current metrics."""
        return [
            {
                "name": m.name,
                "type": m.type.value,
                "value": m.value,
                "timestamp": m.timestamp.isoformat(),
                "labels": m.labels
            }
            for m in self.metrics[-1000:]  # Return recent metrics
        ]

    def get_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        for metric in self.metrics[-1000:]:  # Recent metrics only
            lines.append(metric.to_prometheus_format())
        return "\n".join(lines)

    async def close(self) -> None:
        """Clean up resources."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass


class TimerContext:
    """Context manager for timing operations."""

    def __init__(self, collector: MetricsCollector, name: str,
                 labels: Optional[Dict[str, str]] = None):
        self.collector = collector
        self.name = name
        self.labels = labels
        self.start_time: Optional[float] = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.collector.record_timer(self.name, duration, self.labels)


class SecretMonitor:
    """
    Comprehensive monitoring system for secret management.

    Provides:
    - Real-time metrics collection
    - Anomaly detection and alerting
    - Audit logging
    - Performance monitoring
    - Security event tracking
    """

    def __init__(self, config: SecretConfig):
        self.config = config
        self.metrics_collector = MetricsCollector(config)
        self.anomaly_detector = AnomalyDetector(config)
        self.alerts: List[Alert] = []
        self.alert_handlers: List[Callable[[Alert], None]] = []

        # Audit log
        self.audit_log: List[Dict[str, Any]] = []

        logger.info("Secret Monitor initialized")

    async def initialize(self) -> None:
        """Initialize the monitoring system."""
        await self.metrics_collector.initialize()

        # Initialize core metrics
        self.metrics_collector.set_gauge("zen_secrets_healthy", 1.0)
        self.metrics_collector.increment_counter("zen_secrets_started_total")

        logger.info("Secret Monitor started")

    async def log_access(self, access_data: Dict[str, Any]) -> None:
        """Log a secret access event."""
        try:
            # Add to audit log
            self.audit_log.append(access_data)

            # Keep audit log size manageable
            if len(self.audit_log) > 10000:
                self.audit_log = self.audit_log[-5000:]

            # Update metrics
            self.metrics_collector.increment_counter(
                "zen_secrets_access_total",
                labels={
                    "operation": access_data.get("operation", "unknown"),
                    "secret_name": access_data.get("secret_name", "unknown")
                }
            )

            # Check for anomalies
            timestamp = datetime.fromisoformat(access_data["timestamp"])
            alert = self.anomaly_detector.record_access(
                access_data.get("secret_name", "unknown"),
                access_data.get("user_id"),
                access_data.get("operation", "unknown"),
                timestamp
            )

            if alert:
                await self.raise_alert(alert)

        except Exception as e:
            logger.error(f"Error logging access: {str(e)}")

    async def log_rotation(self, secret_name: str, old_version: str,
                          new_version: str, success: bool) -> None:
        """Log a secret rotation event."""
        try:
            rotation_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": "rotation",
                "secret_name": secret_name,
                "old_version": old_version,
                "new_version": new_version,
                "success": success
            }

            self.audit_log.append(rotation_data)

            # Update metrics
            status = "success" if success else "failure"
            self.metrics_collector.increment_counter(
                "zen_secrets_rotation_total",
                labels={"status": status, "secret_name": secret_name}
            )

            # Alert on rotation failure
            if not success:
                alert = Alert(
                    id=str(uuid4()),
                    title="Secret Rotation Failed",
                    description=f"Rotation failed for secret '{secret_name}'",
                    severity=AlertSeverity.HIGH,
                    timestamp=datetime.utcnow(),
                    secret_name=secret_name,
                    metadata={"old_version": old_version}
                )
                await self.raise_alert(alert)

        except Exception as e:
            logger.error(f"Error logging rotation: {str(e)}")

    async def log_error(self, error_type: str, message: str,
                       secret_name: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log an error event."""
        try:
            error_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": "error",
                "error_type": error_type,
                "message": message,
                "secret_name": secret_name,
                "metadata": metadata or {}
            }

            self.audit_log.append(error_data)

            # Update metrics
            self.metrics_collector.increment_counter(
                "zen_secrets_errors_total",
                labels={"error_type": error_type}
            )

            # Create alert for critical errors
            if error_type in ["access_denied", "rotation_failure", "corruption"]:
                severity = AlertSeverity.HIGH if error_type == "access_denied" else AlertSeverity.CRITICAL

                alert = Alert(
                    id=str(uuid4()),
                    title=f"Secret Management Error: {error_type}",
                    description=message,
                    severity=severity,
                    timestamp=datetime.utcnow(),
                    secret_name=secret_name,
                    metadata=metadata or {}
                )
                await self.raise_alert(alert)

        except Exception as e:
            logger.error(f"Error logging error: {str(e)}")

    async def record_performance_metric(self, operation: str, duration: float,
                                       secret_name: Optional[str] = None) -> None:
        """Record a performance metric."""
        try:
            labels = {"operation": operation}
            if secret_name:
                labels["secret_name"] = secret_name

            self.metrics_collector.record_timer(
                "zen_secrets_operation_duration_seconds",
                duration,
                labels
            )

            # Alert on slow operations
            if duration > 5.0:  # More than 5 seconds
                alert = Alert(
                    id=str(uuid4()),
                    title="Slow Secret Operation",
                    description=f"Operation '{operation}' took {duration:.2f} seconds",
                    severity=AlertSeverity.MEDIUM,
                    timestamp=datetime.utcnow(),
                    secret_name=secret_name,
                    metadata={"operation": operation, "duration": duration}
                )
                await self.raise_alert(alert)

        except Exception as e:
            logger.error(f"Error recording performance metric: {str(e)}")

    async def raise_alert(self, alert: Alert) -> None:
        """Raise an alert and notify handlers."""
        try:
            self.alerts.append(alert)

            # Keep alerts list manageable
            if len(self.alerts) > 1000:
                self.alerts = self.alerts[-500:]

            # Update metrics
            self.metrics_collector.increment_counter(
                "zen_secrets_alerts_total",
                labels={"severity": alert.severity.value}
            )

            # Notify alert handlers
            for handler in self.alert_handlers:
                try:
                    handler(alert)
                except Exception as e:
                    logger.error(f"Error in alert handler: {str(e)}")

            logger.warning(f"Alert raised: {alert.title} ({alert.severity.value})")

        except Exception as e:
            logger.error(f"Error raising alert: {str(e)}")

    def add_alert_handler(self, handler: Callable[[Alert], None]) -> None:
        """Add an alert handler function."""
        self.alert_handlers.append(handler)

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all unresolved alerts."""
        return [alert.to_dict() for alert in self.alerts if not alert.resolved]

    def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved."""
        for alert in self.alerts:
            if alert.id == alert_id and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = datetime.utcnow()
                logger.info(f"Alert {alert_id} resolved")
                return True
        return False

    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit log entries."""
        return self.audit_log[-limit:]

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of current metrics."""
        return {
            "total_metrics": len(self.metrics_collector.metrics),
            "counters": dict(self.metrics_collector.counters),
            "gauges": dict(self.metrics_collector.gauges),
            "active_alerts": len([a for a in self.alerts if not a.resolved]),
            "audit_entries": len(self.audit_log)
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check of the monitoring system."""
        try:
            current_time = datetime.utcnow()

            # Check if we're receiving metrics
            recent_metrics = [
                m for m in self.metrics_collector.metrics
                if (current_time - m.timestamp).total_seconds() < 300
            ]

            # Check alert levels
            critical_alerts = [a for a in self.alerts
                             if not a.resolved and a.severity == AlertSeverity.CRITICAL]

            health_status = "healthy"
            if critical_alerts:
                health_status = "critical"
            elif len(recent_metrics) == 0:
                health_status = "degraded"

            return {
                "status": health_status,
                "recent_metrics_count": len(recent_metrics),
                "active_alerts": len([a for a in self.alerts if not a.resolved]),
                "critical_alerts": len(critical_alerts),
                "audit_entries": len(self.audit_log),
                "timestamp": current_time.isoformat()
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    async def close(self) -> None:
        """Clean up monitoring resources."""
        await self.metrics_collector.close()
        logger.info("Secret Monitor closed")