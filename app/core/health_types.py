"""Core health monitoring types and enums.

Centralized type definitions for system health monitoring components.
"""

from typing import Dict, Any
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field


class HealthStatus(Enum):
    """Overall health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class ComponentHealth:
    """Health status for a system component."""
    name: str
    status: HealthStatus
    health_score: float  # 0.0 to 1.0
    last_check: datetime
    error_count: int = 0
    uptime: float = 0.0  # in seconds
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemAlert:
    """System health alert."""
    alert_id: str
    component: str
    severity: str
    message: str
    timestamp: datetime
    resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthCheckResult:
    """Result of a health check operation."""
    component_name: str
    success: bool
    health_score: float
    response_time_ms: float
    error_message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemResourceMetrics:
    """System resource usage metrics."""
    cpu_usage_percent: float
    memory_usage_percent: float
    disk_usage_percent: float
    network_connections: int
    timestamp: datetime = field(default_factory=datetime.utcnow)


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