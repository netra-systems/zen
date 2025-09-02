"""Agent Execution Types

Core types for agent execution patterns.
Contains ExecutionContext and ExecutionResult for standardized execution.

Note: Legacy execution interface was removed as part of architecture simplification.
All agents now use single inheritance from BaseSubAgent only.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, Optional, Protocol, Union, runtime_checkable

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.schemas.agent_result_types import TypedAgentResult
from netra_backend.app.schemas.core_enums import ExecutionStatus
# Note: Direct bridge imports removed for SSOT compliance
# Use emit_* methods from BaseSubAgent's WebSocketBridgeAdapter instead


@dataclass
class ExecutionContext:
    """Standardized execution context for all agents."""
    run_id: str
    agent_name: str
    state: DeepAgentState
    stream_updates: bool = False
    thread_id: Optional[str] = None
    user_id: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    start_time: Optional[datetime] = None
    correlation_id: Optional[str] = None
    metadata: Optional[Dict[str, Union[str, int, float, bool, None]]] = None

    def __post_init__(self) -> None:
        """Initialize metadata if not provided."""
        if self.metadata is None:
            self.metadata = {}
        # Add timestamp property for compatibility with error handling
        if not hasattr(self, 'timestamp'):
            self.timestamp = self.start_time or datetime.now(timezone.utc)
    
    def __hash__(self) -> int:
        """Make ExecutionContext hashable using run_id and agent_name."""
        # Include both run_id and agent_name for unique hash
        return hash((self.run_id, self.agent_name))
    
    def __eq__(self, other: object) -> bool:
        """Compare ExecutionContext objects by run_id and agent_name."""
        if not isinstance(other, ExecutionContext):
            return False
        return self.run_id == other.run_id and self.agent_name == other.agent_name


@dataclass
class ExecutionResult:
    """Standardized execution result for all agents."""
    success: bool
    status: ExecutionStatus
    result: Optional[Dict[str, Union[str, int, float, bool, Dict, list, None]]] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    retry_count: int = 0
    fallback_used: bool = False
    metrics: Optional[Dict[str, Union[str, int, float, bool, None]]] = None

    def __post_init__(self) -> None:
        """Initialize metrics if not provided."""
        if self.metrics is None:
            self.metrics = {}


@runtime_checkable
class WebSocketManagerProtocol(Protocol):
    """Protocol for WebSocket manager interface."""
    
    async def send_agent_update(self, run_id: str, agent_name: str, 
                               update: Dict[str, Union[str, int, float, bool, Dict, list, None]]) -> None:
        """Send agent update via WebSocket."""
        ...


@runtime_checkable  
class ReliabilityManagerProtocol(Protocol):
    """Protocol for reliability manager interface."""
    
    async def execute_with_reliability(self, context: ExecutionContext,
                                     execute_func: Callable[..., Coroutine[Any, Any, Dict[str, Any]]]) -> ExecutionResult:
        """Execute function with reliability patterns."""
        ...
    
    def get_health_status(self) -> Dict[str, Union[str, bool, int, float]]:
        """Get reliability health status."""
        ...


# Note: Legacy execution interface and mixin classes have been removed
# as part of architecture simplification. All agents now use single inheritance
# from BaseSubAgent which already provides WebSocket functionality via WebSocketBridgeAdapter.