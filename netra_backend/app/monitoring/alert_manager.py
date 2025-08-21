"""
Alert management system for agent failures and system issues.
Re-export from modular alert system components.
"""

# Import types for backward compatibility
from netra_backend.app.alert_models import Alert, AlertRule, AlertLevel, NotificationChannel, NotificationConfig

# Import the main alert manager from the modular core
from netra_backend.app.alert_manager_core import AlertManager, alert_manager

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