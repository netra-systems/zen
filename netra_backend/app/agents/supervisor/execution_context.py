"""Execution context and result types for supervisor agent."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, TYPE_CHECKING

# DeepAgentState removed - using UserExecutionContext pattern
# from netra_backend.app.agents.state import DeepAgentState

# Import ExecutionStrategy from the authoritative source for compatibility
from netra_backend.app.core.interfaces_execution import ExecutionStrategy

if TYPE_CHECKING:
    from netra_backend.app.core.unified_trace_context import UnifiedTraceContext
    from netra_backend.app.services.user_execution_context import UserExecutionContext


class AgentExecutionStrategy(Enum):
    """Execution strategies for agent pipelines"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"


class PipelineStep(Enum):
    """Pipeline execution step states"""
    INITIALIZATION = "initialization"
    VALIDATION = "validation"
    EXECUTION = "execution"
    PROCESSING = "processing"
    COMPLETION = "completion"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class AgentExecutionContext:
    """Context for agent execution with trace propagation"""
    run_id: str
    thread_id: str
    user_id: str
    agent_name: str
    retry_count: int = 0
    max_retries: int = 3
    timeout: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[str] = None
    trace_context: Optional['UnifiedTraceContext'] = None
    # Additional parameters for pipeline execution
    request_id: Optional[str] = None
    step: Optional[PipelineStep] = None
    execution_timestamp: Optional[datetime] = None
    pipeline_step_num: Optional[int] = None
    
    def with_trace_context(self, trace_context: 'UnifiedTraceContext') -> 'AgentExecutionContext':
        """Create a copy of this context with the given trace context."""
        import copy
        new_context = copy.copy(self)
        new_context.trace_context = trace_context
        new_context.correlation_id = trace_context.correlation_id
        return new_context


@dataclass
class AgentExecutionResult:
    """Result of agent execution"""
    success: bool
    agent_name: Optional[str] = None  # The name of the agent that was executed
    user_context: Optional['UserExecutionContext'] = None
    error: Optional[str] = None
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    metrics: Optional[Dict[str, Any]] = None  # Performance metrics
    data: Optional[Any] = None  # Result data from execution


@dataclass
class PipelineStepConfig:
    """Represents a step configuration in an execution pipeline"""
    agent_name: str
    strategy: AgentExecutionStrategy = AgentExecutionStrategy.SEQUENTIAL
    condition: Optional[callable] = None
    dependencies: list = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)