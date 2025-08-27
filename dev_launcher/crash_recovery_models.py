"""
Data models for crash recovery system.

This module provides the data models and enums used by the crash recovery system
for tracking crashes, recovery attempts, and service configurations.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class CrashSeverity(Enum):
    """Severity levels for detected crashes."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DetectionMethod(Enum):
    """Methods used to detect crashes."""
    PROCESS_MONITORING = "process_monitoring"
    PORT_MONITORING = "port_monitoring"
    HEALTH_CHECK = "health_check"
    MEMORY_MONITORING = "memory_monitoring"
    LOG_ANALYSIS = "log_analysis"
    MANUAL = "manual"


class RecoveryStage(Enum):
    """Stages in the recovery process."""
    ERROR_CAPTURE = "error_capture"
    DIAGNOSE = "diagnose"
    RECOVERY_ATTEMPT = "recovery_attempt"
    FALLBACK = "fallback"
    COMPLETED = "completed"


@dataclass
class DetectionResult:
    """Result of a crash detection check."""
    method: DetectionMethod
    is_crashed: bool
    error_message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    
@dataclass
class ServiceConfig:
    """Configuration for a service being monitored."""
    name: str
    port: Optional[int] = None
    health_check_url: Optional[str] = None
    process_name: Optional[str] = None
    restart_command: Optional[str] = None
    environment: Dict[str, str] = field(default_factory=dict)
    monitoring_interval: int = 30  # seconds
    max_recovery_attempts: int = 3
    
    def model_dump(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'name': self.name,
            'port': self.port,
            'health_check_url': self.health_check_url,
            'process_name': self.process_name,
            'restart_command': self.restart_command,
            'environment': self.environment,
            'monitoring_interval': self.monitoring_interval,
            'max_recovery_attempts': self.max_recovery_attempts,
        }


@dataclass 
class MonitoringConfig:
    """Configuration for the crash monitoring system."""
    check_interval: int = 30  # seconds
    max_concurrent_recoveries: int = 3
    recovery_timeout: int = 300  # seconds
    enable_auto_restart: bool = True
    enable_fallback_recovery: bool = True
    log_retention_hours: int = 24
    

@dataclass
class RecoveryAttempt:
    """Details of a single recovery attempt."""
    attempt_number: int
    stage: RecoveryStage
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    success: bool = False
    actions_taken: List[str] = field(default_factory=list)
    error_message: str = ""
    stage_results: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> Optional[float]:
        """Get duration of the recovery attempt."""
        if self.end_time:
            return self.end_time - self.start_time
        return None


@dataclass
class CrashReport:
    """Complete report of a crash and recovery process."""
    service_name: str
    severity: CrashSeverity
    detection_results: List[DetectionResult] = field(default_factory=list)
    crash_time: float = field(default_factory=time.time)
    
    # Error information
    last_logs: List[str] = field(default_factory=list)
    diagnosis: Dict[str, Any] = field(default_factory=dict)
    
    # Recovery tracking
    recovery_attempts: List[RecoveryAttempt] = field(default_factory=list)
    recovery_successful: bool = False
    total_recovery_time: Optional[float] = None
    
    # Additional context
    system_state: Dict[str, Any] = field(default_factory=dict)
    environment_info: Dict[str, str] = field(default_factory=dict)
    
    def add_recovery_attempt(self, attempt: RecoveryAttempt):
        """Add a recovery attempt to the report."""
        self.recovery_attempts.append(attempt)
        
    def mark_recovery_complete(self, successful: bool):
        """Mark the recovery process as complete."""
        self.recovery_successful = successful
        if self.recovery_attempts:
            first_attempt = self.recovery_attempts[0]
            last_attempt = self.recovery_attempts[-1]
            if last_attempt.end_time:
                self.total_recovery_time = last_attempt.end_time - first_attempt.start_time
                
    @property
    def total_attempts(self) -> int:
        """Get total number of recovery attempts."""
        return len(self.recovery_attempts)
        
    @property
    def current_stage(self) -> Optional[RecoveryStage]:
        """Get the current recovery stage."""
        if self.recovery_attempts:
            return self.recovery_attempts[-1].stage
        return None