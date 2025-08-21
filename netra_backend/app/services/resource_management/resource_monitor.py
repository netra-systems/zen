"""Resource Monitor for tracking and alerting on resource usage"""

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class AlertLevel(Enum):
    """Alert levels for resource monitoring"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class ResourceMetric:
    """Resource metric data point"""
    metric_name: str
    value: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class AlertRule:
    """Alert rule configuration"""
    name: str
    metric_name: str
    threshold: float
    comparison: str  # "gt", "lt", "eq", "gte", "lte"
    level: AlertLevel
    duration_seconds: int = 60  # How long threshold must be breached
    enabled: bool = True


@dataclass
class Alert:
    """Resource alert"""
    rule_name: str
    metric_name: str
    current_value: float
    threshold: float
    level: AlertLevel
    message: str
    triggered_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    resolved_at: Optional[datetime] = None
    labels: Dict[str, str] = field(default_factory=dict)


class ResourceMonitor:
    """Monitors resource usage and triggers alerts"""
    
    def __init__(self, retention_hours: int = 24):
        self.metrics: Dict[str, List[ResourceMetric]] = {}
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.alert_callbacks: List[Callable] = []
        self.retention_hours = retention_hours
        self.monitoring_active = False
        self._monitoring_task = None
    
    async def start_monitoring(self, interval_seconds: int = 30) -> None:
        """Start resource monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop(interval_seconds))
    
    async def stop_monitoring(self) -> None:
        """Stop resource monitoring"""
        self.monitoring_active = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
    
    async def record_metric(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a resource metric"""
        metric = ResourceMetric(
            metric_name=metric_name,
            value=value,
            labels=labels or {}
        )
        
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        
        self.metrics[metric_name].append(metric)
        
        # Clean up old metrics
        await self._cleanup_old_metrics(metric_name)
        
        # Check alert rules
        await self._evaluate_alert_rules(metric)
    
    async def _cleanup_old_metrics(self, metric_name: str) -> None:
        """Remove metrics older than retention period"""
        cutoff_time = datetime.now(UTC) - timedelta(hours=self.retention_hours)
        
        self.metrics[metric_name] = [
            metric for metric in self.metrics[metric_name]
            if metric.timestamp > cutoff_time
        ]
    
    async def add_alert_rule(self, rule: AlertRule) -> bool:
        """Add an alert rule"""
        if rule.name in self.alert_rules:
            return False
        
        # Validate comparison operator
        valid_comparisons = ["gt", "lt", "eq", "gte", "lte"]
        if rule.comparison not in valid_comparisons:
            return False
        
        self.alert_rules[rule.name] = rule
        return True
    
    async def remove_alert_rule(self, rule_name: str) -> bool:
        """Remove an alert rule"""
        if rule_name in self.alert_rules:
            del self.alert_rules[rule_name]
            # Resolve any active alerts for this rule
            if rule_name in self.active_alerts:
                await self._resolve_alert(rule_name)
            return True
        return False
    
    async def _evaluate_alert_rules(self, metric: ResourceMetric) -> None:
        """Evaluate all alert rules against a metric"""
        for rule_name, rule in self.alert_rules.items():
            if not rule.enabled or rule.metric_name != metric.metric_name:
                continue
            
            if self._check_threshold_breach(metric.value, rule.threshold, rule.comparison):
                await self._handle_threshold_breach(rule_name, rule, metric)
            else:
                await self._handle_threshold_recovery(rule_name, rule, metric)
    
    def _check_threshold_breach(self, value: float, threshold: float, comparison: str) -> bool:
        """Check if metric value breaches threshold"""
        if comparison == "gt":
            return value > threshold
        elif comparison == "lt":
            return value < threshold
        elif comparison == "eq":
            return value == threshold
        elif comparison == "gte":
            return value >= threshold
        elif comparison == "lte":
            return value <= threshold
        return False
    
    async def _handle_threshold_breach(self, rule_name: str, rule: AlertRule, metric: ResourceMetric) -> None:
        """Handle threshold breach"""
        if rule_name in self.active_alerts:
            # Alert already active, update current value
            self.active_alerts[rule_name].current_value = metric.value
        else:
            # Check if breach has been sustained for required duration
            if await self._check_sustained_breach(rule, metric):
                await self._trigger_alert(rule_name, rule, metric)
    
    async def _handle_threshold_recovery(self, rule_name: str, rule: AlertRule, metric: ResourceMetric) -> None:
        """Handle threshold recovery"""
        if rule_name in self.active_alerts:
            await self._resolve_alert(rule_name)
    
    async def _check_sustained_breach(self, rule: AlertRule, current_metric: ResourceMetric) -> bool:
        """Check if threshold has been breached for required duration"""
        if rule.duration_seconds <= 0:
            return True  # Immediate alerting
        
        # Look back through recent metrics
        cutoff_time = current_metric.timestamp - timedelta(seconds=rule.duration_seconds)
        recent_metrics = [
            m for m in self.metrics.get(rule.metric_name, [])
            if m.timestamp >= cutoff_time
        ]
        
        # Check if all recent metrics breach the threshold
        for metric in recent_metrics:
            if not self._check_threshold_breach(metric.value, rule.threshold, rule.comparison):
                return False
        
        return len(recent_metrics) > 0
    
    async def _trigger_alert(self, rule_name: str, rule: AlertRule, metric: ResourceMetric) -> None:
        """Trigger an alert"""
        alert = Alert(
            rule_name=rule_name,
            metric_name=rule.metric_name,
            current_value=metric.value,
            threshold=rule.threshold,
            level=rule.level,
            message=f"{rule.metric_name} is {metric.value} ({rule.comparison} {rule.threshold})",
            labels=metric.labels
        )
        
        self.active_alerts[rule_name] = alert
        
        # Notify callbacks
        for callback in self.alert_callbacks:
            try:
                await callback(alert)
            except Exception:
                # Don't let callback errors break monitoring
                pass
    
    async def _resolve_alert(self, rule_name: str) -> None:
        """Resolve an active alert"""
        if rule_name in self.active_alerts:
            alert = self.active_alerts[rule_name]
            alert.resolved_at = datetime.now(UTC)
            
            # Move to history
            self.alert_history.append(alert)
            del self.active_alerts[rule_name]
            
            # Notify callbacks about resolution
            for callback in self.alert_callbacks:
                try:
                    await callback(alert)
                except Exception:
                    pass
    
    async def _monitoring_loop(self, interval_seconds: int) -> None:
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Collect system metrics
                await self._collect_system_metrics()
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception:
                # Continue monitoring even if collection fails
                await asyncio.sleep(interval_seconds)
    
    async def _collect_system_metrics(self) -> None:
        """Collect basic system metrics"""
        # Simulate system metrics collection
        # In real implementation, this would use psutil or similar
        
        # CPU usage
        cpu_usage = 45.0  # Simulated
        await self.record_metric("cpu_usage_percent", cpu_usage)
        
        # Memory usage
        memory_usage = 1024  # MB, simulated
        await self.record_metric("memory_usage_mb", memory_usage)
        
        # Disk usage
        disk_usage = 5.5  # GB, simulated
        await self.record_metric("disk_usage_gb", disk_usage)
    
    def add_alert_callback(self, callback: Callable) -> None:
        """Add callback for alert notifications"""
        self.alert_callbacks.append(callback)
    
    def remove_alert_callback(self, callback: Callable) -> None:
        """Remove alert callback"""
        if callback in self.alert_callbacks:
            self.alert_callbacks.remove(callback)
    
    async def get_current_metrics(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get current metrics for all monitored resources"""
        current_metrics = {}
        for metric_name, metric_list in self.metrics.items():
            current_metrics[metric_name] = [
                {
                    "value": metric.value,
                    "timestamp": metric.timestamp.isoformat(),
                    "labels": metric.labels
                }
                for metric in metric_list[-10:]  # Last 10 values
            ]
        return current_metrics
    
    async def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts"""
        return [
            {
                "rule_name": alert.rule_name,
                "metric_name": alert.metric_name,
                "current_value": alert.current_value,
                "threshold": alert.threshold,
                "level": alert.level.value,
                "message": alert.message,
                "triggered_at": alert.triggered_at.isoformat(),
                "labels": alert.labels
            }
            for alert in self.active_alerts.values()
        ]
    
    async def get_alert_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get alert history for specified hours"""
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
        
        recent_alerts = [
            alert for alert in self.alert_history
            if alert.triggered_at > cutoff_time
        ]
        
        return [
            {
                "rule_name": alert.rule_name,
                "metric_name": alert.metric_name,
                "current_value": alert.current_value,
                "threshold": alert.threshold,
                "level": alert.level.value,
                "message": alert.message,
                "triggered_at": alert.triggered_at.isoformat(),
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                "labels": alert.labels
            }
            for alert in recent_alerts
        ]
    
    async def get_metric_summary(self, metric_name: str, hours: int = 1) -> Optional[Dict[str, Any]]:
        """Get summary statistics for a metric"""
        if metric_name not in self.metrics:
            return None
        
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
        recent_metrics = [
            metric for metric in self.metrics[metric_name]
            if metric.timestamp > cutoff_time
        ]
        
        if not recent_metrics:
            return None
        
        values = [metric.value for metric in recent_metrics]
        
        return {
            "metric_name": metric_name,
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "latest": values[-1],
            "time_range_hours": hours
        }
    
    def get_monitor_stats(self) -> Dict[str, Any]:
        """Get monitoring system statistics"""
        total_metrics = sum(len(metric_list) for metric_list in self.metrics.values())
        
        return {
            "monitoring_active": self.monitoring_active,
            "tracked_metrics": len(self.metrics),
            "total_metric_points": total_metrics,
            "alert_rules": len(self.alert_rules),
            "active_alerts": len(self.active_alerts),
            "alert_history_count": len(self.alert_history),
            "alert_callbacks": len(self.alert_callbacks),
            "retention_hours": self.retention_hours
        }