"""WebSocket Performance Monitor Alert Management.

Alert creation, management, and notification with micro-functions.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Callable, Set, Any, Dict

from app.logging_config import central_logger
from netra_backend.app.performance_monitor_types import Alert, AlertSeverity

logger = central_logger.get_logger(__name__)


class PerformanceAlertManager:
    """Manages performance alerts with micro-functions."""
    
    def __init__(self):
        self.alerts: List[Alert] = []
        self.alert_callbacks: Set[Callable] = set()
    
    def register_alert_callback(self, callback: Callable[[Alert], None]) -> None:
        """Register callback for alert notifications."""
        self.alert_callbacks.add(callback)
    
    async def trigger_alert(self, metric_name: str, severity: AlertSeverity, 
                          message: str, threshold: float, current_value: float) -> None:
        """Trigger a performance alert."""
        if self._has_active_alert(metric_name):
            return
        alert = self._create_alert(metric_name, severity, message, threshold, current_value)
        await self._process_alert(alert)
    
    def _has_active_alert(self, metric_name: str) -> bool:
        """Check if active alert exists for metric."""
        active_alerts = [a for a in self.alerts if a.metric_name == metric_name and not a.resolved]
        return len(active_alerts) > 0
    
    def _create_alert(self, metric_name: str, severity: AlertSeverity, 
                     message: str, threshold: float, current_value: float) -> Alert:
        """Create new alert instance."""
        return Alert(
            metric_name=metric_name,
            severity=severity,
            message=message,
            threshold=threshold,
            current_value=current_value,
            timestamp=datetime.now(timezone.utc)
        )
    
    async def _process_alert(self, alert: Alert) -> None:
        """Process and notify alert."""
        self.alerts.append(alert)
        logger.warning(f"Performance alert: {alert.message}")
        await self._notify_callbacks(alert)
    
    async def _notify_callbacks(self, alert: Alert) -> None:
        """Notify all registered callbacks."""
        for callback in self.alert_callbacks:
            await self._execute_callback(callback, alert)
    
    async def _execute_callback(self, callback: Callable, alert: Alert) -> None:
        """Execute single callback safely."""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(alert)
            else:
                callback(alert)
        except Exception as e:
            logger.error(f"Alert callback error: {e}")
    
    async def cleanup_old_alerts(self) -> None:
        """Clean up old resolved alerts."""
        cutoff_time = self._get_cleanup_cutoff_time()
        self.alerts = self._filter_recent_alerts(cutoff_time)
    
    def _get_cleanup_cutoff_time(self) -> datetime:
        """Get cutoff time for alert cleanup."""
        return datetime.now(timezone.utc) - timedelta(hours=24)
    
    def _filter_recent_alerts(self, cutoff_time: datetime) -> List[Alert]:
        """Filter alerts to keep only recent or unresolved ones."""
        return [a for a in self.alerts if a.timestamp >= cutoff_time or not a.resolved]
    
    def resolve_alert(self, metric_name: str) -> bool:
        """Resolve alerts for a specific metric."""
        resolved_count = self._resolve_metric_alerts(metric_name)
        self._log_resolution(metric_name, resolved_count)
        return resolved_count > 0
    
    def _resolve_metric_alerts(self, metric_name: str) -> int:
        """Resolve all alerts for a metric."""
        resolved_count = 0
        for alert in self.alerts:
            if self._should_resolve_alert(alert, metric_name):
                alert.resolved = True
                resolved_count += 1
        return resolved_count
    
    def _should_resolve_alert(self, alert: Alert, metric_name: str) -> bool:
        """Check if alert should be resolved."""
        return alert.metric_name == metric_name and not alert.resolved
    
    def _log_resolution(self, metric_name: str, resolved_count: int) -> None:
        """Log alert resolution."""
        if resolved_count > 0:
            logger.info(f"Resolved {resolved_count} alerts for metric {metric_name}")
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active (unresolved) alerts."""
        return [a for a in self.alerts if not a.resolved]
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of active alerts."""
        active_alerts = self.get_active_alerts()
        return self._create_alert_summary(active_alerts)
    
    def _create_alert_summary(self, active_alerts: List[Alert]) -> Dict[str, Any]:
        """Create alert summary dictionary."""
        return {
            "total": len(active_alerts),
            "by_severity": self._count_by_severity(active_alerts)
        }
    
    def _count_by_severity(self, alerts: List[Alert]) -> Dict[str, int]:
        """Count alerts by severity level."""
        return {
            severity.value: len([a for a in alerts if a.severity == severity])
            for severity in AlertSeverity
        }
    
    def get_recent_alerts(self, duration_minutes: int) -> List[Dict[str, Any]]:
        """Get alerts from specified time period."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=duration_minutes)
        recent_alerts = [a for a in self.alerts if a.timestamp >= cutoff_time]
        return self._format_alerts_for_export(recent_alerts)
    
    def _format_alerts_for_export(self, alerts: List[Alert]) -> List[Dict[str, Any]]:
        """Format alerts for export."""
        return [self._format_single_alert(alert) for alert in alerts]
    
    def _format_single_alert(self, alert: Alert) -> Dict[str, Any]:
        """Format single alert for export."""
        return {
            "metric_name": alert.metric_name,
            "severity": alert.severity.value,
            "message": alert.message,
            "timestamp": alert.timestamp.isoformat(),
            "resolved": alert.resolved
        }