"""Agent Base Interface Definitions

Core interface types for agent execution patterns.
Provides standardized execution context and result structures.
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum


class ExecutionStatus(Enum):
    """Execution status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExecutionContext:
    """Standardized execution context for agent operations
    
    Provides consistent context structure across all agent types.
    """
    request_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None
    
    # Execution parameters
    parameters: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    
    # Timing information
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Configuration overrides
    timeout_seconds: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        """Initialize default values"""
        if self.parameters is None:
            self.parameters = {}
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class ExecutionResult:
    """Standardized execution result for agent operations
    
    Provides consistent result structure across all agent types.
    """
    status: ExecutionStatus
    request_id: str
    
    # Result data
    data: Optional[Dict[str, Any]] = None
    artifacts: Optional[List[str]] = None
    
    # Execution metadata
    execution_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    
    # Metrics and telemetry
    metrics: Optional[Dict[str, Union[int, float, str]]] = None
    trace_id: Optional[str] = None
    
    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize default values"""
        if self.data is None:
            self.data = {}
        if self.artifacts is None:
            self.artifacts = []
        if self.metrics is None:
            self.metrics = {}
    
    @property
    def is_success(self) -> bool:
        """Check if execution was successful"""
        return self.status == ExecutionStatus.SUCCESS
    
    @property
    def is_failed(self) -> bool:
        """Check if execution failed"""
        return self.status == ExecutionStatus.FAILED
    
    @property
    def is_complete(self) -> bool:
        """Check if execution is complete (success or failed)"""
        return self.status in [ExecutionStatus.SUCCESS, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]


# Type aliases for backward compatibility
AgentExecutionContext = ExecutionContext
AgentExecutionResult = ExecutionResult


__all__ = [
    'ExecutionContext',
    'ExecutionResult', 
    'ExecutionStatus',
    'AgentExecutionContext',  # Backward compatibility
    'AgentExecutionResult',   # Backward compatibility
]