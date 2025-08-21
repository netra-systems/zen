"""
Startup Status Management Types - Strong Pydantic Models

Single source of truth for startup status tracking data structures.
Implements schema defined in SPEC/startup_coverage.xml GAP-005.

CRITICAL ARCHITECTURAL COMPLIANCE:
- ALL startup status types MUST be imported from this module
- NO duplicate startup type definitions allowed elsewhere
- Maintains strong typing and follows type_safety.xml
- Maximum file size: 300 lines (currently under limit)

Usage:
    from netra_backend.app.schemas.startup_types import StartupStatus, LastStartup, MigrationStatus
"""

from typing import Dict, List, Optional, Union, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class ServiceType(str, Enum):
    """Service types for startup tracking."""
    BACKEND = "backend"
    FRONTEND = "frontend"


class Environment(str, Enum):
    """Environment types for startup tracking."""
    DEV = "dev"
    TEST = "test"
    STAGING = "staging"
    PROD = "prod"


class LastStartup(BaseModel):
    """Last startup attempt information."""
    timestamp: datetime
    success: bool
    duration_ms: int = Field(ge=0)
    environment: Environment
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class MigrationStatus(BaseModel):
    """Database migration status tracking."""
    last_run: Optional[datetime] = None
    current_version: Optional[str] = None
    pending_migrations: List[str] = Field(default_factory=list)
    failed_migrations: List[str] = Field(default_factory=list)
    auto_run: bool = True


class ServiceConfig(BaseModel):
    """Service configuration validation status."""
    hash: Optional[str] = None
    last_validated: Optional[datetime] = None
    validation_errors: List[str] = Field(default_factory=list)


class CrashEntry(BaseModel):
    """Individual crash record."""
    service: ServiceType
    timestamp: datetime
    error: str
    stack_trace: Optional[str] = None
    recovery_attempted: bool = False
    recovery_success: bool = False


class HealthCheckHistory(BaseModel):
    """Health check status history."""
    consecutive_failures: Dict[str, int] = Field(default_factory=dict)
    last_healthy: Dict[str, Optional[datetime]] = Field(default_factory=dict)


class StartupStatus(BaseModel):
    """Complete startup status tracking model - single source of truth."""
    last_startup: Optional[LastStartup] = None
    migration_status: MigrationStatus = Field(default_factory=MigrationStatus)
    service_config: ServiceConfig = Field(default_factory=ServiceConfig)
    crash_history: List[CrashEntry] = Field(default_factory=list)
    health_check_history: HealthCheckHistory = Field(default_factory=HealthCheckHistory)

    @field_validator('crash_history')
    @classmethod
    def limit_crash_history(cls, v: List[CrashEntry]) -> List[CrashEntry]:
        """Limit crash history to last 50 entries."""
        return v[-50:] if len(v) > 50 else v


class StartupEvent(BaseModel):
    """Individual startup event for tracking."""
    event_type: str
    timestamp: datetime
    success: bool
    message: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class ErrorPhase(str, Enum):
    """Error phase during startup."""
    STARTUP = "startup"
    RUNTIME = "runtime" 
    SHUTDOWN = "shutdown"


class ErrorType(str, Enum):
    """Error type classification."""
    CONNECTION = "connection"
    CONFIGURATION = "configuration"
    DEPENDENCY = "dependency"
    MIGRATION = "migration"
    TIMEOUT = "timeout"
    PERMISSION = "permission"
    RESOURCE = "resource"
    OTHER = "other"


class StartupError(BaseModel):
    """Single error record for aggregation database."""
    id: Optional[int] = None
    timestamp: datetime
    service: str
    phase: ErrorPhase
    severity: str
    error_type: ErrorType
    message: str
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    resolved: bool = False
    resolution: Optional[str] = None


class ErrorPattern(BaseModel):
    """Detected error pattern with frequency tracking."""
    pattern_id: Optional[int] = None
    pattern: str
    frequency: int = Field(default=1, ge=1)
    last_seen: datetime
    suggested_fix: Optional[str] = None
    auto_fixable: bool = False


class ErrorTrend(BaseModel):
    """Error trend analysis results."""
    period: str
    total_errors: int
    error_types: Dict[str, int] = Field(default_factory=dict)
    services: Dict[str, int] = Field(default_factory=dict)
    severity_breakdown: Dict[str, int] = Field(default_factory=dict)
    patterns: List[ErrorPattern] = Field(default_factory=list)


# Export all startup types
__all__ = [
    "ServiceType",
    "Environment", 
    "LastStartup",
    "MigrationStatus",
    "ServiceConfig",
    "CrashEntry",
    "HealthCheckHistory",
    "StartupStatus",
    "StartupEvent",
    "ErrorPhase",
    "ErrorType",
    "StartupError",
    "ErrorPattern",
    "ErrorTrend"
]