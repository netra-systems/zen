"""Shared health monitoring types - single source of truth.

Consolidates all health-related types used across core modules to eliminate
duplication and ensure consistency. All functions  <= 8 lines.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, TYPE_CHECKING

from netra_backend.app.logging_config import central_logger

if TYPE_CHECKING:
    from netra_backend.app.schemas.core_models import HealthCheckResult

logger = central_logger.get_logger(__name__)


@dataclass
class HealthCheckResult:
    """Result of a health check operation - simplified to avoid circular imports."""
    component_name: str
    success: bool
    health_score: float
    response_time_ms: float
    status: Optional[str] = None
    response_time: Optional[float] = None  # Legacy field for compatibility
    error_message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)


class HealthStatus(Enum):
    """Health check statuses."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    CRITICAL = "critical"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    # Legacy values for backward compatibility
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class HealthChecker(ABC):
    """Abstract base for health check implementations."""
    
    @abstractmethod
    async def check_health(self) -> HealthCheckResult:
        """Perform health check and return result."""
        pass


class DatabaseHealthChecker(HealthChecker):
    """Unified health checker for database connections."""
    
    def __init__(self, db_pool):
        """Initialize with database pool."""
        self.db_pool = db_pool
    
    async def check_health(self) -> HealthCheckResult:
        """Check database connection health."""
        start_time = datetime.now()
        return await self._execute_health_check(start_time)
    
    async def _execute_health_check(self, start_time: datetime) -> HealthCheckResult:
        """Execute the actual health check."""
        try:
            return await self._perform_db_check(start_time)
        except Exception as e:
            return self._create_unhealthy_result(start_time, e)
    
    async def _perform_db_check(self, start_time: datetime) -> HealthCheckResult:
        """Perform database connectivity check."""
        async with self.db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        response_time = self._calculate_response_time(start_time)
        return self._create_healthy_result(response_time)
    
    def _calculate_response_time(self, start_time: datetime) -> float:
        """Calculate response time in seconds."""
        return (datetime.now() - start_time).total_seconds()
    
    def _create_healthy_result(self, response_time: float) -> HealthCheckResult:
        """Create healthy result with response time."""
        status = HealthStatus.HEALTHY if response_time < 1.0 else HealthStatus.DEGRADED
        return HealthCheckResult(
            component_name="database",
            success=True,
            health_score=95.0 if status == HealthStatus.HEALTHY else 75.0,
            response_time_ms=response_time * 1000,
            status=status.value,
            response_time=response_time,
            details={'connection_count': getattr(self.db_pool, 'size', 0)}
        )
    
    def _create_unhealthy_result(self, start_time: datetime, error: Exception) -> HealthCheckResult:
        """Create unhealthy result with error details."""
        response_time = self._calculate_response_time(start_time)
        return HealthCheckResult(
            component_name="database",
            success=False,
            health_score=0.0,
            response_time_ms=response_time * 1000,
            status=HealthStatus.UNHEALTHY.value,
            response_time=response_time,
            error_message=str(error),
            details={'error': str(error)}
        )


@dataclass
class ComponentHealth:
    """Health information for a system component."""
    name: str
    status: HealthStatus
    health_score: float
    last_check: datetime
    error_count: int = 0
    uptime: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize metadata if None."""
        if self.metadata is None:
            self.metadata = {}


@dataclass
class SystemAlert:
    """System-wide alert information."""
    alert_id: str
    component: str
    severity: str
    message: str
    timestamp: datetime
    resolved: bool = False
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize metadata if None."""
        if self.metadata is None:
            self.metadata = {}