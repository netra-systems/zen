"""
Alert management system for agent failures and system issues.
Re-export from modular alert system components.
"""

# Import types for backward compatibility
# Import the main alert manager from the compact SSOT implementation
from netra_backend.app.monitoring.alert_manager_compact import CompactAlertManager as AlertManager

# Create singleton instance for backward compatibility
alert_manager = AlertManager()
from netra_backend.app.monitoring.alert_models import (
    Alert,
    AlertLevel,
    AlertRule,
    NotificationChannel,
    NotificationConfig,
)

# Re-export for backward compatibility
__all__ = [
    "Alert",
    "AlertRule", 
    "AlertLevel",
    "NotificationChannel",
    "NotificationConfig",
    "AlertManager",
    "alert_manager"
]