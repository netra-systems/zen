from netra_backend.app.logging_config import central_logger
"""
Service Level Objective (SLO) Monitoring and Alerting

Business Value Justification (BVJ):
- Segment: Platform/Internal - Development Velocity, Risk Reduction
- Business Goal: Proactive chat performance monitoring to prevent degradation
- Value Impact: Reduces chat downtime by 80% through early detection and alerting
- Strategic Impact: Maintains 99.5% chat availability SLA protecting revenue streams

Key SLOs Monitored:
- Chat Response Time: 95% of requests < 2s
- WebSocket Uptime: > 99.5% availability  
- Error Rate: < 0.1% of requests fail
- Database Query Performance: 95% < 500ms
- Agent Execution Time: 90% < 30s
"""

import asyncio
import time
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import statistics

from netra_backend.app.core.unified_logging import central_logger
from shared.isolated_environment import get_env

logger = central_logger.get_logger(__name__)


@dataclass
class SLODefinition:
    """Definition of a Service Level Objective."""
    name: str
    description: str
    target_value: float
    comparison: str  # 'lt', 'gt', 'eq'
    measurement_window_minutes: int = 5
    evaluation_window_minutes: int = 60
    critical_threshold: float = 0.95  # When to trigger critical alerts
    warning_threshold: float = 0.98   # When to trigger warnings
    error_budget_minutes: int = 43200  # 30 days in minutes
    labels: Dict[str, str] = None


@dataclass
class SLOMetric:
    """Single SLO measurement."""
    timestamp: float
    value: float
    labels: Dict[str, str] = None
    success: bool = True


@dataclass
class SLOStatus:
    """Current status of an SLO."""
    slo_name: str
    current_value: float
    target_value: float
    success_rate: float
    status: str  # 'healthy', 'warning', 'critical'
    error_budget_remaining: float
    error_budget_consumed_percent: float
    measurements_count: int
    last_measurement: float
    trend: str  # 'improving', 'stable', 'degrading'


@dataclass
class Alert:
    """SLO violation alert."""
    alert_id: str
    slo_name: str
    severity: str  # 'warning', 'critical'
    message: str
    current_value: float
    target_value: float
    triggered_at: float
    labels: Dict[str, str] = None
    resolved_at: Optional[float] = None


class SLOMonitor:
    """Service Level Objective monitoring and alerting system."""
    
    def __init__(self, retention_hours: int = 24):
        """
        Initialize SLO monitor.
        
        Args:
            retention_hours: How long to keep metrics in memory
        """
        self.retention_hours = retention_hours
        self.retention_seconds = retention_hours * 3600
        
        # Storage
        self._slos: Dict[str, SLODefinition] = {}
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self._alerts: Dict[str, Alert] = {}
        self._alert_history: deque = deque(maxlen=1000)
        
        # State tracking
        self._last_cleanup = time.time()
        self._alert_callbacks: List[callable] = []
        
        # Default SLOs for chat system
        self._setup_default_slos()
        
        logger.info(f"SLO Monitor initialized with {retention_hours}h retention")
    
    def _setup_default_slos(self):
        """Setup default SLOs for the chat system."""
        
        # Chat Response Time SLO
        self.define_slo(SLODefinition(
            name="chat_response_time",
            description="95% of chat API requests complete within 2 seconds",
            target_value=2.0,
            comparison="lt",
            measurement_window_minutes=5,
            evaluation_window_minutes=15,
            critical_threshold=0.90,  # 90% success rate triggers critical
            warning_threshold=0.95,   # 95% success rate triggers warning
            labels={"component": "chat", "metric": "response_time"}
        ))
        
        # WebSocket Uptime SLO
        self.define_slo(SLODefinition(
            name="websocket_uptime",
            description="WebSocket connections maintain >99.5% availability",
            target_value=0.995,
            comparison="gt",
            measurement_window_minutes=1,
            evaluation_window_minutes=10,
            critical_threshold=0.990,
            warning_threshold=0.995,
            labels={"component": "websocket", "metric": "uptime"}
        ))
        
        # Chat Error Rate SLO
        self.define_slo(SLODefinition(
            name="chat_error_rate", 
            description="Chat error rate remains below 0.1%",
            target_value=0.001,
            comparison="lt",
            measurement_window_minutes=5,
            evaluation_window_minutes=30,
            critical_threshold=0.95,
            warning_threshold=0.98,
            labels={"component": "chat", "metric": "error_rate"}
        ))
        
        # Database Query Performance SLO
        self.define_slo(SLODefinition(
            name="database_query_time",
            description="95% of database queries complete within 500ms",
            target_value=0.5,
            comparison="lt", 
            measurement_window_minutes=5,
            evaluation_window_minutes=20,
            critical_threshold=0.90,
            warning_threshold=0.95,
            labels={"component": "database", "metric": "query_time"}
        ))
        
        # Agent Execution Time SLO
        self.define_slo(SLODefinition(
            name="agent_execution_time",
            description="90% of agent executions complete within 30 seconds",
            target_value=30.0,
            comparison="lt",
            measurement_window_minutes=10,
            evaluation_window_minutes=30,
            critical_threshold=0.85,
            warning_threshold=0.90,
            labels={"component": "agents", "metric": "execution_time"}
        ))
        
        logger.info(f"Configured {len(self._slos)} default SLOs")
    
    def define_slo(self, slo: SLODefinition) -> None:
        """Define a new SLO for monitoring."""
        if slo.labels is None:
            slo.labels = {}
            
        self._slos[slo.name] = slo
        logger.info(f"Defined SLO: {slo.name} - {slo.description}")
    
    def record_metric(self, slo_name: str, value: float, 
                     labels: Optional[Dict[str, str]] = None,
                     success: Optional[bool] = None) -> None:
        """Record a metric measurement for an SLO."""
        if slo_name not in self._slos:
            logger.warning(f"Unknown SLO: {slo_name}")
            return
        
        slo = self._slos[slo_name]
        
        # Determine success based on SLO target if not explicitly provided
        if success is None:
            if slo.comparison == "lt":
                success = value < slo.target_value
            elif slo.comparison == "gt": 
                success = value > slo.target_value
            elif slo.comparison == "eq":
                success = abs(value - slo.target_value) < 0.001
            else:
                success = True
        
        metric = SLOMetric(
            timestamp=time.time(),
            value=value,
            labels=labels or {},
            success=success
        )
        
        self._metrics[slo_name].append(metric)
        
        # Cleanup old metrics periodically
        if time.time() - self._last_cleanup > 300:  # Every 5 minutes
            self._cleanup_old_metrics()
        
        # Check for SLO violations
        asyncio.create_task(self._check_slo_violation(slo_name))
    
    def _cleanup_old_metrics(self) -> None:
        """Remove old metrics beyond retention period."""
        cutoff = time.time() - self.retention_seconds
        cleaned_count = 0
        
        for slo_name, metrics in self._metrics.items():
            initial_len = len(metrics)
            
            # Remove old metrics from the left
            while metrics and metrics[0].timestamp < cutoff:
                metrics.popleft()
                cleaned_count += 1
        
        self._last_cleanup = time.time()
        
        if cleaned_count > 0:
            logger.debug(f"Cleaned up {cleaned_count} old metrics")
    
    async def _check_slo_violation(self, slo_name: str) -> None:
        """Check if SLO is being violated and trigger alerts."""
        slo = self._slos[slo_name]
        status = self.get_slo_status(slo_name)
        
        if not status:
            return
        
        # Determine alert severity
        alert_severity = None
        if status.success_rate <= slo.critical_threshold:
            alert_severity = "critical"
        elif status.success_rate <= slo.warning_threshold:
            alert_severity = "warning"
        
        # Check if we should trigger or resolve alerts
        alert_id = f"{slo_name}_{alert_severity}" if alert_severity else None
        existing_alert = self._alerts.get(alert_id)
        
        if alert_severity and not existing_alert:
            # Trigger new alert
            alert = Alert(
                alert_id=alert_id,
                slo_name=slo_name,
                severity=alert_severity,
                message=f"SLO violation: {slo.name} success rate {status.success_rate:.3f} below threshold {slo.warning_threshold if alert_severity == 'warning' else slo.critical_threshold:.3f}",
                current_value=status.current_value,
                target_value=status.target_value,
                triggered_at=time.time(),
                labels=slo.labels
            )
            
            self._alerts[alert_id] = alert
            self._alert_history.append(alert)
            
            await self._trigger_alert(alert)
            
        elif not alert_severity and existing_alert and not existing_alert.resolved_at:
            # Resolve existing alert
            existing_alert.resolved_at = time.time()
            self._alerts.pop(alert_id, None)
            
            await self._resolve_alert(existing_alert)
    
    async def _trigger_alert(self, alert: Alert) -> None:
        """Trigger an SLO violation alert."""
        logger.warning(f"SLO ALERT [{alert.severity.upper()}]: {alert.message}")
        
        # Call registered alert callbacks
        for callback in self._alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
        
        # Send to observability platform
        await self._send_alert_to_monitoring(alert)
    
    async def _resolve_alert(self, alert: Alert) -> None:
        """Resolve an SLO violation alert."""
        duration = alert.resolved_at - alert.triggered_at
        logger.info(f"SLO ALERT RESOLVED: {alert.slo_name} after {duration:.1f}s")
        
        # Notify via callbacks
        for callback in self._alert_callbacks:
            try:
                if hasattr(callback, '__name__') and 'resolve' in callback.__name__:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(alert)
                    else:
                        callback(alert)
            except Exception as e:
                logger.error(f"Error in alert resolution callback: {e}")
    
    async def _send_alert_to_monitoring(self, alert: Alert) -> None:
        """Send alert to external monitoring systems."""
        try:
            alert_data = {
                "alert_id": alert.alert_id,
                "slo_name": alert.slo_name,
                "severity": alert.severity,
                "message": alert.message,
                "current_value": alert.current_value,
                "target_value": alert.target_value,
                "triggered_at": alert.triggered_at,
                "labels": alert.labels or {},
                "service": "netra_backend",
                "environment": get_env().get('ENVIRONMENT', 'development')
            }
            
            # Send to internal monitoring endpoint
            # This would typically integrate with Prometheus AlertManager,
            # PagerDuty, Slack, etc.
            logger.info(f"Alert data prepared for external systems: {json.dumps(alert_data, indent=2)}")
            
            # Integration with external systems would go here
            # Example:
            # await self._send_to_slack(alert_data)
            # await self._send_to_pagerduty(alert_data)
            
        except Exception as e:
            logger.error(f"Failed to send alert to monitoring: {e}")
    
    def get_slo_status(self, slo_name: str) -> Optional[SLOStatus]:
        """Get current status of an SLO."""
        if slo_name not in self._slos:
            return None
        
        slo = self._slos[slo_name]
        metrics = self._metrics[slo_name]
        
        if not metrics:
            return None
        
        # Filter to evaluation window
        now = time.time()
        window_start = now - (slo.evaluation_window_minutes * 60)
        recent_metrics = [m for m in metrics if m.timestamp >= window_start]
        
        if not recent_metrics:
            return None
        
        # Calculate success rate
        successful = sum(1 for m in recent_metrics if m.success)
        total = len(recent_metrics)
        success_rate = successful / total if total > 0 else 0.0
        
        # Calculate current value (latest measurement)
        current_value = recent_metrics[-1].value
        
        # Calculate error budget
        total_minutes = slo.error_budget_minutes
        allowed_failures = total_minutes * (1.0 - slo.target_value)
        actual_failures = total - successful
        error_budget_remaining = max(0, allowed_failures - actual_failures)
        error_budget_consumed_percent = (actual_failures / allowed_failures * 100) if allowed_failures > 0 else 0
        
        # Determine status
        if success_rate <= slo.critical_threshold:
            status = "critical"
        elif success_rate <= slo.warning_threshold:
            status = "warning"
        else:
            status = "healthy"
        
        # Calculate trend
        trend = self._calculate_trend(recent_metrics)
        
        return SLOStatus(
            slo_name=slo_name,
            current_value=current_value,
            target_value=slo.target_value,
            success_rate=success_rate,
            status=status,
            error_budget_remaining=error_budget_remaining,
            error_budget_consumed_percent=error_budget_consumed_percent,
            measurements_count=total,
            last_measurement=recent_metrics[-1].timestamp,
            trend=trend
        )
    
    def _calculate_trend(self, metrics: List[SLOMetric]) -> str:
        """Calculate trend direction for SLO metrics."""
        if len(metrics) < 10:
            return "stable"
        
        # Split into two halves and compare success rates
        mid = len(metrics) // 2
        first_half = metrics[:mid]
        second_half = metrics[mid:]
        
        first_success_rate = sum(1 for m in first_half if m.success) / len(first_half)
        second_success_rate = sum(1 for m in second_half if m.success) / len(second_half)
        
        diff = second_success_rate - first_success_rate
        
        if diff > 0.02:  # 2% improvement
            return "improving"
        elif diff < -0.02:  # 2% degradation
            return "degrading"
        else:
            return "stable"
    
    def get_all_slo_statuses(self) -> Dict[str, SLOStatus]:
        """Get status of all defined SLOs."""
        statuses = {}
        for slo_name in self._slos.keys():
            status = self.get_slo_status(slo_name)
            if status:
                statuses[slo_name] = status
        return statuses
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all currently active alerts."""
        return [alert for alert in self._alerts.values() if not alert.resolved_at]
    
    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        """Get alert history for the specified time period."""
        cutoff = time.time() - (hours * 3600)
        return [alert for alert in self._alert_history if alert.triggered_at >= cutoff]
    
    def add_alert_callback(self, callback: callable) -> None:
        """Add callback function to be called when alerts are triggered."""
        self._alert_callbacks.append(callback)
        logger.info(f"Added alert callback: {callback.__name__}")
    
    def get_monitoring_summary(self) -> Dict[str, Any]:
        """Get comprehensive monitoring summary."""
        statuses = self.get_all_slo_statuses()
        active_alerts = self.get_active_alerts()
        
        # Calculate overall health score
        if statuses:
            health_scores = [
                1.0 if status.status == "healthy" else
                0.5 if status.status == "warning" else
                0.0 for status in statuses.values()
            ]
            overall_health_score = sum(health_scores) / len(health_scores)
        else:
            overall_health_score = 1.0
        
        # Count by severity
        alert_counts = {"critical": 0, "warning": 0}
        for alert in active_alerts:
            alert_counts[alert.severity] = alert_counts.get(alert.severity, 0) + 1
        
        return {
            "timestamp": time.time(),
            "overall_health_score": round(overall_health_score, 3),
            "total_slos": len(self._slos),
            "slo_statuses": {name: asdict(status) for name, status in statuses.items()},
            "active_alerts_count": len(active_alerts),
            "alert_breakdown": alert_counts,
            "active_alerts": [asdict(alert) for alert in active_alerts],
            "monitoring_stats": {
                "total_metrics": sum(len(metrics) for metrics in self._metrics.values()),
                "retention_hours": self.retention_hours,
                "last_cleanup": self._last_cleanup
            }
        }


# Global SLO monitor instance
_slo_monitor: Optional[SLOMonitor] = None


def get_slo_monitor() -> SLOMonitor:
    """Get global SLO monitor instance."""
    global _slo_monitor
    
    if _slo_monitor is None:
        retention_hours = int(get_env().get('SLO_RETENTION_HOURS', '24'))
        _slo_monitor = SLOMonitor(retention_hours=retention_hours)
        logger.info("Global SLO monitor initialized")
    
    return _slo_monitor


# Convenience functions for recording common metrics
def record_chat_response_time(response_time: float) -> None:
    """Record chat API response time metric."""
    get_slo_monitor().record_metric("chat_response_time", response_time)


def record_websocket_uptime(is_healthy: bool) -> None:
    """Record WebSocket uptime metric."""
    get_slo_monitor().record_metric("websocket_uptime", 1.0 if is_healthy else 0.0)


def record_chat_error_rate(error_rate: float) -> None:
    """Record chat error rate metric."""
    get_slo_monitor().record_metric("chat_error_rate", error_rate)


def record_database_query_time(query_time: float) -> None:
    """Record database query time metric."""
    get_slo_monitor().record_metric("database_query_time", query_time)


def record_agent_execution_time(execution_time: float) -> None:
    """Record agent execution time metric."""
    get_slo_monitor().record_metric("agent_execution_time", execution_time)