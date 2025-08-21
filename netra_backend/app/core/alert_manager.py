"""Alert management and notification system.

Handles alert generation, thresholds, and recovery actions.
"""

import asyncio
import time
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime, UTC

from netra_backend.app.logging_config import central_logger
from netra_backend.app.shared_health_types import HealthStatus, ComponentHealth, SystemAlert
from netra_backend.app.health_types import AlertSeverity, RecoveryAction

logger = central_logger.get_logger(__name__)


class HealthAlertManager:
    """Manages system alerts and recovery actions."""
    
    def __init__(self, max_alert_history: int = 1000):
        self.alerts: List[SystemAlert] = []
        self.max_alert_history = max_alert_history
        self.alert_callbacks: List[Callable] = []
        self.recovery_actions: Dict[str, Callable] = {}
        self._setup_default_recovery_actions()
    
    def register_alert_callback(self, callback: Callable) -> None:
        """Register a callback function for alerts."""
        self.alert_callbacks.append(callback)
        logger.debug("Registered alert callback")
    
    def register_recovery_action(self, action: RecoveryAction, handler: Callable) -> None:
        """Register a recovery action handler."""
        self.recovery_actions[action.value] = handler
        logger.debug(f"Registered recovery action: {action.value}")
    
    async def emit_alert(self, alert: SystemAlert) -> None:
        """Emit alert to all registered callbacks."""
        self._store_alert(alert)
        self._log_alert(alert)
        await self._notify_callbacks(alert)
        await self._attempt_recovery(alert)
    
    async def create_status_change_alert(self, previous: ComponentHealth, current: ComponentHealth) -> SystemAlert:
        """Generate alert for component status change."""
        severity = self._get_alert_severity(current.status)
        message = self._create_status_change_message(previous, current)
        alert_id = self._generate_status_change_alert_id(current.name)
        metadata = self._create_status_metadata(previous, current)
        
        return self._build_status_change_alert(alert_id, current.name, severity, message, metadata)
    
    def _generate_status_change_alert_id(self, component_name: str) -> str:
        """Generate unique alert ID for status change."""
        return f"status_change_{component_name}_{int(time.time())}"
    
    def _build_status_change_alert(self, alert_id: str, component: str, severity: str, message: str, metadata: Dict[str, Any]) -> SystemAlert:
        """Build SystemAlert object for status change."""
        return SystemAlert(
            alert_id=alert_id,
            component=component,
            severity=severity,
            message=message,
            timestamp=datetime.now(UTC),
            metadata=metadata
        )
    
    async def create_threshold_alert(self, component: str, metric: str, value: float, threshold: float) -> SystemAlert:
        """Generate alert for threshold violation."""
        severity = self._determine_threshold_severity(value, threshold)
        message = self._create_threshold_message(component, metric, value, threshold)
        alert_id = self._generate_threshold_alert_id(component, metric)
        metadata = self._create_threshold_metadata(metric, value, threshold)
        
        return self._build_threshold_alert(alert_id, component, severity, message, metadata)
    
    def _create_threshold_message(self, component: str, metric: str, value: float, threshold: float) -> str:
        """Create message for threshold violation alert."""
        return f"{component} {metric} exceeded threshold: {value:.2f} > {threshold:.2f}"
    
    def _generate_threshold_alert_id(self, component: str, metric: str) -> str:
        """Generate unique alert ID for threshold violation."""
        return f"threshold_{component}_{metric}_{int(time.time())}"
    
    def _create_threshold_metadata(self, metric: str, value: float, threshold: float) -> Dict[str, Any]:
        """Create metadata for threshold alert."""
        return {"metric": metric, "value": value, "threshold": threshold}
    
    def _build_threshold_alert(self, alert_id: str, component: str, severity: str, message: str, metadata: Dict[str, Any]) -> SystemAlert:
        """Build SystemAlert object for threshold violation."""
        return SystemAlert(
            alert_id=alert_id,
            component=component,
            severity=severity,
            message=message,
            timestamp=datetime.now(UTC),
            metadata=metadata
        )
    
    def get_recent_alerts(self, hours: int = 24) -> List[SystemAlert]:
        """Get alerts from the last N hours."""
        cutoff = datetime.now(UTC).timestamp() - (hours * 3600)
        return [alert for alert in self.alerts if alert.timestamp.timestamp() > cutoff]
    
    def get_active_alerts(self) -> List[SystemAlert]:
        """Get all unresolved alerts."""
        return [alert for alert in self.alerts if not alert.resolved]
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved."""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                logger.info(f"Alert resolved: {alert_id}")
                return True
        return False
    
    def _store_alert(self, alert: SystemAlert) -> None:
        """Store alert in history with size management."""
        self.alerts.append(alert)
        if len(self.alerts) > self.max_alert_history:
            self.alerts = self.alerts[-self.max_alert_history:]
    
    def _log_alert(self, alert: SystemAlert) -> None:
        """Log alert with appropriate level."""
        log_methods = {
            "info": logger.info,
            "warning": logger.warning,
            "error": logger.error,
            "critical": logger.critical
        }
        log_method = log_methods.get(alert.severity, logger.info)
        log_method(f"HEALTH ALERT [{alert.severity.upper()}] {alert.component}: {alert.message}")
    
    async def _notify_callbacks(self, alert: SystemAlert) -> None:
        """Notify all registered callbacks."""
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
    
    async def _attempt_recovery(self, alert: SystemAlert) -> None:
        """Attempt automatic recovery based on alert."""
        if not self._should_attempt_recovery_for_alert(alert):
            return
        
        recovery_action = self._determine_recovery_action(alert)
        if self._is_recovery_action_available(recovery_action):
            await self._execute_recovery_action(recovery_action, alert)
    
    def _should_attempt_recovery_for_alert(self, alert: SystemAlert) -> bool:
        """Check if recovery should be attempted for alert severity."""
        return alert.severity in ["error", "critical"]
    
    def _is_recovery_action_available(self, recovery_action: Optional[str]) -> bool:
        """Check if recovery action is available for execution."""
        return recovery_action and recovery_action in self.recovery_actions
    
    async def _execute_recovery_action(self, recovery_action: str, alert: SystemAlert) -> None:
        """Execute the specified recovery action."""
        try:
            await self.recovery_actions[recovery_action](alert)
            logger.info(f"Recovery action executed: {recovery_action}")
        except Exception as e:
            logger.error(f"Recovery action failed: {recovery_action}, error: {e}")
    
    def _get_alert_severity(self, status: HealthStatus) -> str:
        """Get alert severity based on health status."""
        severity_map = {
            HealthStatus.HEALTHY: "info",
            HealthStatus.DEGRADED: "warning",
            HealthStatus.UNHEALTHY: "error",
            HealthStatus.CRITICAL: "critical"
        }
        return severity_map.get(status, "info")
    
    def _create_status_change_message(self, previous: ComponentHealth, current: ComponentHealth) -> str:
        """Create message for status change alert."""
        if current.status.value in ["unhealthy", "critical"]:
            return f"Component {current.name} health degraded from {previous.status.value} to {current.status.value}"
        elif current.status.value == "healthy" and previous.status.value != "healthy":
            return f"Component {current.name} recovered to {current.status.value} from {previous.status.value}"
        else:
            return f"Component {current.name} status changed from {previous.status.value} to {current.status.value}"
    
    def _create_status_metadata(self, previous: ComponentHealth, current: ComponentHealth) -> Dict[str, Any]:
        """Create metadata for status change alert."""
        return {
            "previous_status": previous.status.value,
            "current_status": current.status.value,
            "health_score": current.health_score,
            "error_count": current.error_count
        }
    
    def _determine_threshold_severity(self, value: float, threshold: float) -> str:
        """Determine severity based on threshold violation magnitude."""
        ratio = value / threshold
        if ratio > 2.0:
            return "critical"
        elif ratio > 1.6:
            return "error"
        else:
            return "warning"
    
    def _determine_recovery_action(self, alert: SystemAlert) -> Optional[str]:
        """Determine appropriate recovery action for alert."""
        component = alert.component.lower()
        
        if self._is_resource_related_component(component):
            return RecoveryAction.CLEAR_CACHE.value
        elif self._is_service_related_component(component):
            return RecoveryAction.RESTART_SERVICE.value
        elif self._is_critical_alert(alert):
            return RecoveryAction.NOTIFY_ADMIN.value
        
        return None
    
    def _is_resource_related_component(self, component: str) -> bool:
        """Check if component is resource-related (memory/CPU)."""
        return "memory" in component or "cpu" in component
    
    def _is_service_related_component(self, component: str) -> bool:
        """Check if component is service-related (database/redis)."""
        return "database" in component or "redis" in component
    
    def _is_critical_alert(self, alert: SystemAlert) -> bool:
        """Check if alert is critical severity."""
        return alert.severity == "critical"
    
    def _setup_default_recovery_actions(self) -> None:
        """Setup default recovery action handlers."""
        async def notify_admin_action(alert: SystemAlert):
            logger.critical(f"ADMIN NOTIFICATION: {alert.message}")
        
        async def clear_cache_action(alert: SystemAlert):
            logger.info(f"Cache clearing triggered by alert: {alert.alert_id}")
        
        self.recovery_actions[RecoveryAction.NOTIFY_ADMIN.value] = notify_admin_action
        self.recovery_actions[RecoveryAction.CLEAR_CACHE.value] = clear_cache_action