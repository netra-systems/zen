"""Core health monitoring types and enums.

Centralized type definitions for system health monitoring components.
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, UTC

# Import shared types from their single sources of truth
from netra_backend.app.core.shared_health_types import HealthStatus, ComponentHealth, SystemAlert
from netra_backend.app.schemas.core_models import HealthCheckResult


@dataclass
class SystemResourceMetrics:
    """System resource usage metrics."""
    cpu_usage_percent: float
    memory_usage_percent: float
    disk_usage_percent: float
    network_connections: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class RecoveryAction(Enum):
    """Available recovery actions."""
    RESTART_SERVICE = "restart_service"
    CLEAR_CACHE = "clear_cache"
    SCALE_RESOURCES = "scale_resources"
    NOTIFY_ADMIN = "notify_admin"
    GRACEFUL_SHUTDOWN = "graceful_shutdown"