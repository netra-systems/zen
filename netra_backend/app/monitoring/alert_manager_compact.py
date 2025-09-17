"""
Compact alert management system.
Provides minimal alert management functionality with reduced overhead.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, UTC

from netra_backend.app.logging_config import central_logger
from netra_backend.app.monitoring.alert_models import Alert, AlertLevel, AlertRule

logger = central_logger.get_logger(__name__)


class CompactAlertManager:
    """Compact version of alert manager with minimal functionality."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._active_alerts: List[Alert] = []
        self._rules: List[AlertRule] = []
        logger.debug("Initialized CompactAlertManager")
    
    async def initialize(self) -> None:
        """Initialize the alert manager."""
        logger.info("CompactAlertManager initialized")
    
    async def process_alert(self, alert: Alert) -> None:
        """Process and store an alert."""
        self._active_alerts.append(alert)
        logger.info(f"Processed alert: {alert.alert_id} - {alert.title}")
    
    async def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        self._rules.append(rule)
        logger.debug(f"Added alert rule: {rule.rule_id}")
    
    async def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        return self._active_alerts.copy()
    
    async def clear_alert(self, alert_id: str) -> bool:
        """Clear an alert by ID."""
        initial_count = len(self._active_alerts)
        self._active_alerts = [a for a in self._active_alerts if a.alert_id != alert_id]
        cleared = len(self._active_alerts) < initial_count
        if cleared:
            logger.info(f"Cleared alert: {alert_id}")
        return cleared
    
    async def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of current alerts."""
        return {
            "total_alerts": len(self._active_alerts),
            "critical_alerts": len([a for a in self._active_alerts if a.level == AlertLevel.CRITICAL]),
            "warning_alerts": len([a for a in self._active_alerts if a.level == AlertLevel.WARNING]),
            "info_alerts": len([a for a in self._active_alerts if a.level == AlertLevel.INFO]),
            "timestamp": datetime.now(UTC)
        }


# Global instance
alert_manager = CompactAlertManager()


__all__ = [
    "CompactAlertManager",
    "alert_manager",
]