"""Core health monitoring types and enums.

Centralized type definitions for system health monitoring components.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

# Import shared types from their single sources of truth
from netra_backend.app.core.shared_health_types import (
    ComponentHealth,
    HealthStatus,
    SystemAlert,
)
from netra_backend.app.schemas.core_models import HealthCheckResult

# Re-export all types that other modules expect to import from this module
__all__ = [
    # Shared types from other modules (re-exported)
    'ComponentHealth',
    'HealthStatus', 
    'SystemAlert',
    'HealthCheckResult',
    
    # Types defined in this module
    'SystemResourceMetrics',
    'AlertSeverity',
    'RecoveryAction',
    'CheckType',
    'HealthCheckConfig',
    'StandardHealthResponse',
]


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


class CheckType(Enum):
    """Types of health checks."""
    LIVENESS = "liveness"      # Is the service alive?
    READINESS = "readiness"    # Is the service ready to serve traffic?
    STARTUP = "startup"        # Has the service finished starting up?
    COMPONENT = "component"    # Component-specific health check


@dataclass
class HealthCheckConfig:
    """Configuration for health check functions."""
    name: str
    description: str = ""
    check_function: Optional[Callable[[], Any]] = None
    timeout_seconds: float = 5.0
    check_type: CheckType = CheckType.LIVENESS
    critical: bool = True
    priority: int = 1  # Lower numbers = higher priority
    labels: Dict[str, str] = field(default_factory=dict)
    interval_seconds: float = 30.0
    retries: int = 3
    retry_delay_seconds: float = 1.0


@dataclass
class StandardHealthResponse:
    """Standard health check response format."""
    status: str
    service_name: str
    version: str
    timestamp: str
    environment: str
    checks: Optional[List[Dict[str, Any]]] = None
    summary: Optional[Dict[str, Any]] = None