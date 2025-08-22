"""
Strong Pydantic models for crash recovery system.

Defines all type-safe models used in crash detection and recovery,
following type_safety.xml requirements for single source of truth.

ARCHITECTURE COMPLIANCE:
- File size: ≤300 lines (currently under limit)
- Strong typing with Pydantic models
- Single source of truth for crash-related types
- No duplicate type definitions
"""

import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DetectionMethod(str, Enum):
    """Crash detection methods."""
    PROCESS_MONITORING = "process_monitoring"
    HEALTH_ENDPOINT = "health_endpoint"
    LOG_ANALYSIS = "log_analysis"


class RecoveryStage(str, Enum):
    """Recovery process stages."""
    ERROR_CAPTURE = "error_capture"
    DIAGNOSE = "diagnose"
    RECOVERY_ATTEMPT = "recovery_attempt"
    FALLBACK = "fallback"


class CrashSeverity(str, Enum):
    """Crash severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DetectionResult(BaseModel):
    """Result from crash detection."""
    method: DetectionMethod
    is_crashed: bool
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DiagnosisResult(BaseModel):
    """Result from system diagnosis."""
    port_conflicts: List[int] = Field(default_factory=list)
    database_issues: List[str] = Field(default_factory=list)
    memory_issues: bool = False
    config_issues: List[str] = Field(default_factory=list)
    zombie_processes: List[int] = Field(default_factory=list)
    temp_file_issues: List[str] = Field(default_factory=list)


class RecoveryAttempt(BaseModel):
    """Single recovery attempt record."""
    attempt_number: int
    stage: RecoveryStage
    actions_taken: List[str] = Field(default_factory=list)
    success: bool = False
    error_message: Optional[str] = None
    duration_seconds: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CrashReport(BaseModel):
    """Complete crash incident report."""
    service_name: str
    crash_id: str = Field(default_factory=lambda: f"crash_{int(time.time())}")
    severity: CrashSeverity
    detection_results: List[DetectionResult] = Field(default_factory=list)
    diagnosis: DiagnosisResult = Field(default_factory=DiagnosisResult)
    recovery_attempts: List[RecoveryAttempt] = Field(default_factory=list)
    last_logs: List[str] = Field(default_factory=list)
    stack_trace: Optional[str] = None
    suggestions: List[str] = Field(default_factory=list)
    resolved: bool = False
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ServiceConfig(BaseModel):
    """Configuration for monitored service."""
    name: str
    health_url: Optional[str] = None
    log_file: Optional[str] = None
    restart_command: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)
    critical: bool = True


class MonitoringConfig(BaseModel):
    """Configuration for crash monitoring."""
    process_check_interval: int = Field(default=5)  # seconds
    health_check_interval: int = Field(default=30)  # seconds
    log_check_interval: int = Field(default=10)  # seconds
    max_recovery_attempts: int = Field(default=3)
    backoff_delays: List[int] = Field(default=[5, 15, 45])  # seconds
    reports_directory: str = Field(default=".netra/crash_reports")


class CrashStatistics(BaseModel):
    """Statistics for crash monitoring."""
    total_crashes: int = 0
    resolved_crashes: int = 0
    unresolved_crashes: int = 0
    average_recovery_time: float = 0.0
    most_common_causes: List[str] = Field(default_factory=list)
    uptime_percentage: float = 100.0
    last_crash: Optional[datetime] = None


# Export all models
__all__ = [
    "DetectionMethod",
    "RecoveryStage", 
    "CrashSeverity",
    "DetectionResult",
    "DiagnosisResult",
    "RecoveryAttempt",
    "CrashReport",
    "ServiceConfig",
    "MonitoringConfig",
    "CrashStatistics"
]