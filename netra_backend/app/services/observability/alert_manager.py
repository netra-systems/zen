"""
Alert Manager for Observability Services.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Enable test execution and prevent import errors
- Value Impact: Ensures alert management functionality is available
- Strategic Impact: Maintains compatibility for health monitoring systems
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Basic alert structure."""
    id: str
    message: str
    severity: AlertSeverity = AlertSeverity.MEDIUM
    source: str = "system"
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class AlertManager:
    """Basic alert management for observability."""
    
    def __init__(self):
        """Initialize alert manager."""
        self._alerts: Dict[str, Alert] = {}
        self._alert_count = 0
        logger.debug("AlertManager initialized")
    
    def create_alert(
        self, 
        message: str, 
        severity: AlertSeverity = AlertSeverity.MEDIUM,
        source: str = "system",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new alert."""
        self._alert_count += 1
        alert_id = f"alert_{self._alert_count}"
        
        alert = Alert(
            id=alert_id,
            message=message,
            severity=severity,
            source=source,
            metadata=metadata or {}
        )
        
        self._alerts[alert_id] = alert
        logger.info(f"Alert created: {alert_id} - {message} (severity: {severity.value})")
        return alert_id
    
    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get alert by ID."""
        return self._alerts.get(alert_id)
    
    def get_alerts_by_severity(self, severity: AlertSeverity) -> List[Alert]:
        """Get all alerts with specified severity."""
        return [alert for alert in self._alerts.values() if alert.severity == severity]
    
    def clear_alert(self, alert_id: str) -> bool:
        """Clear/dismiss an alert."""
        if alert_id in self._alerts:
            del self._alerts[alert_id]
            logger.info(f"Alert cleared: {alert_id}")
            return True
        return False
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of all alerts."""
        severity_counts = {}
        for severity in AlertSeverity:
            severity_counts[severity.value] = len(self.get_alerts_by_severity(severity))
        
        return {
            "total_alerts": len(self._alerts),
            "by_severity": severity_counts,
            "alert_ids": list(self._alerts.keys())
        }


class HealthAlertManager(AlertManager):
    """Specialized alert manager for health monitoring."""
    
    def __init__(self):
        """Initialize health alert manager."""
        super().__init__()
        self._service_health_alerts: Dict[str, str] = {}
        logger.debug("HealthAlertManager initialized")
    
    def create_health_alert(
        self,
        service_name: str, 
        health_status: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.HIGH
    ) -> str:
        """Create a health-specific alert."""
        metadata = {
            "service_name": service_name,
            "health_status": health_status,
            "alert_type": "health_check"
        }
        
        alert_id = self.create_alert(
            message=f"Service {service_name}: {message}",
            severity=severity,
            source=f"health_monitor_{service_name}",
            metadata=metadata
        )
        
        # Track service-specific alerts
        self._service_health_alerts[service_name] = alert_id
        return alert_id
    
    def clear_service_health_alert(self, service_name: str) -> bool:
        """Clear health alert for a specific service."""
        if service_name in self._service_health_alerts:
            alert_id = self._service_health_alerts[service_name]
            success = self.clear_alert(alert_id)
            if success:
                del self._service_health_alerts[service_name]
            return success
        return False
    
    def get_service_health_status(self) -> Dict[str, Any]:
        """Get health status for all monitored services."""
        service_statuses = {}
        for service_name, alert_id in self._service_health_alerts.items():
            alert = self.get_alert(alert_id)
            if alert:
                service_statuses[service_name] = {
                    "alert_id": alert_id,
                    "severity": alert.severity.value,
                    "message": alert.message,
                    "health_status": alert.metadata.get("health_status", "unknown")
                }
        
        return {
            "services_with_alerts": service_statuses,
            "services_count": len(self._service_health_alerts),
            "summary": self.get_alert_summary()
        }


# Global instances for convenience
_alert_manager: Optional[AlertManager] = None
_health_alert_manager: Optional[HealthAlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get global alert manager instance."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


def get_health_alert_manager() -> HealthAlertManager:
    """Get global health alert manager instance."""
    global _health_alert_manager
    if _health_alert_manager is None:
        _health_alert_manager = HealthAlertManager()
    return _health_alert_manager


__all__ = [
    'AlertManager', 
    'HealthAlertManager', 
    'Alert', 
    'AlertSeverity',
    'get_alert_manager',
    'get_health_alert_manager'
]