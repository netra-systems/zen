"""
Diagnostic Types Schema
Strong typing for startup diagnostics interface following type_safety.xml
"""

from datetime import datetime
from typing import List, Dict, Optional, Any, Union
from enum import Enum
from pydantic import BaseModel, Field


class DiagnosticSeverity(str, Enum):
    """Error severity levels for diagnostics"""
    CRITICAL = "critical"
    HIGH = "high" 
    MEDIUM = "medium"
    LOW = "low"


class ServiceType(str, Enum):
    """Service types for error categorization"""
    BACKEND = "backend"
    FRONTEND = "frontend"
    DATABASE = "database"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class StartupPhase(str, Enum):
    """Startup phase for error context"""
    STARTUP = "startup"
    RUNTIME = "runtime"
    SHUTDOWN = "shutdown"
    VALIDATION = "validation"


class DiagnosticError(BaseModel):
    """Individual diagnostic error with context"""
    service: ServiceType
    phase: StartupPhase
    severity: DiagnosticSeverity
    message: str
    context: Dict[str, Any] = Field(default_factory=dict)
    suggested_fix: str
    can_auto_fix: bool
    timestamp: datetime = Field(default_factory=datetime.now)


class SystemState(BaseModel):
    """Current system state snapshot"""
    processes: List[Dict[str, Any]] = Field(default_factory=list)
    ports: List[int] = Field(default_factory=list)
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    disk_usage: float = 0.0


class DiagnosticConfiguration(BaseModel):
    """System configuration snapshot"""
    environment_variables: Dict[str, str] = Field(default_factory=dict)
    config_files: Dict[str, bool] = Field(default_factory=dict)
    dependencies: Dict[str, str] = Field(default_factory=dict)


class DiagnosticResult(BaseModel):
    """Complete diagnostic result output"""
    timestamp: datetime = Field(default_factory=datetime.now)
    success: bool
    errors: List[DiagnosticError] = Field(default_factory=list)
    system_state: SystemState = Field(default_factory=SystemState)
    configuration: DiagnosticConfiguration = Field(default_factory=DiagnosticConfiguration)
    recommendations: List[str] = Field(default_factory=list)
    execution_time_ms: int = 0


class FixResult(BaseModel):
    """Result of applying a fix"""
    error_id: str
    attempted: bool
    successful: bool
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)