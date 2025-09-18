"""Agent Base Interface Definitions

Core interface types for agent execution patterns.
Provides standardized execution context and result structures.
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime, UTC
from dataclasses import dataclass

# SSOT: Import ExecutionStatus from core_enums to prevent duplication
from netra_backend.app.schemas.core_enums import ExecutionStatus


@dataclass
class ExecutionContext:
    """Standardized execution context for agent operations
    
    Provides consistent context structure across all agent types.
    """
    request_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None
    
    # Agent-specific context
    run_id: Optional[str] = None
    agent_name: Optional[str] = None
    state: Optional[Any] = None
    stream_updates: bool = False
    
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
            self.created_at = datetime.now(UTC)


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
        return self.status == ExecutionStatus.COMPLETED
    
    @property
    def is_failed(self) -> bool:
        """Check if execution failed"""
        return self.status == ExecutionStatus.FAILED
    
    @property
    def is_complete(self) -> bool:
        """Check if execution is complete (success or failed)"""
        return self.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED]
    
    @property
    def error(self) -> Optional[str]:
        """Get error message (compatibility property)"""
        return self.error_message
    
    @property
    def result(self) -> Optional[Dict[str, Any]]:
        """Get result data (compatibility property)"""
        return self.data
    
    @property
    def success(self) -> bool:
        """Get success status (compatibility property)"""
        return self.is_success


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