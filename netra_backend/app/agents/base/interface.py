"""Base Agent Execution Interface

Core interface defining standardized agent execution patterns.
Provides consistent execution workflow for all agent types.

Business Value: Standardizes 40+ agent execute() methods.
"""

from abc import ABC, abstractmethod
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


class BaseExecutionInterface(ABC):
    """Base interface for standardized agent execution.
    
    Provides consistent execution patterns across all agent types.
    Eliminates duplicate execute() methods and ensures standardization.
    """
    
    def __init__(self, agent_name: str) -> None:
        self.agent_name = agent_name
        # WebSocket functionality is handled via WebSocketBridgeAdapter pattern
        # set_websocket_bridge() should be called to configure WebSocket events
        
    @abstractmethod
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Union[str, int, float, bool, Dict, list, None]]:
        """Execute agent-specific core logic.
        
        Args:
            context: Execution context with state and parameters
            
        Returns:
            Dict containing agent-specific execution results
        """
        pass
    
    @abstractmethod
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions.
        
        Args:
            context: Execution context
            
        Returns:
            True if preconditions are met
        """
        pass
    
    async def send_status_update(self, context: ExecutionContext, 
                               status: str, message: str) -> None:
        """Send status update via WebSocket."""
        if not self.websocket_manager or not context.stream_updates:
            return
        await self._send_websocket_update(context, {"status": status, "message": message})
        
    
    
    
    
    
    def _create_legacy_execution_context(self, run_id: str) -> ExecutionContext:
        """Create ExecutionContext for legacy run_id-based method calls."""
        return ExecutionContext(
            run_id=run_id,
            agent_name=self.agent_name,
            state=None,  # Not available in legacy context
            stream_updates=True,  # Assume streaming since methods are being called
            thread_id=None,
            user_id=None,
            retry_count=0,
            max_retries=3,
            start_time=None,
            correlation_id=None,
            metadata={}
        )


class AgentExecutionMixin:
    """Mixin providing common execution functionality.
    
    Can be combined with existing agent classes for backward compatibility.
    """
    
    def create_execution_context(self, state: DeepAgentState, run_id: str,
                               stream_updates: bool = False) -> ExecutionContext:
        """Create standardized execution context."""
        return ExecutionContext(
            run_id=run_id,
            agent_name=getattr(self, 'name', self.__class__.__name__),
            state=state,
            stream_updates=stream_updates,
            thread_id=getattr(state, 'chat_thread_id', None),
            user_id=getattr(state, 'user_id', None),
            start_time=datetime.now(timezone.utc),
            correlation_id=getattr(self, 'correlation_id', None)
        )
    
    def create_success_result(self, result: Dict[str, Union[str, int, float, bool, Dict, list, None]], 
                           execution_time_ms: float) -> ExecutionResult:
        """Create successful execution result."""
        return ExecutionResult(
            success=True,
            status=ExecutionStatus.COMPLETED,
            result=result,
            execution_time_ms=execution_time_ms
        )
    
    def create_error_result(self, error: str, execution_time_ms: float,
                          retry_count: int = 0) -> ExecutionResult:
        """Create error execution result."""
        return ExecutionResult(
            success=False,
            status=ExecutionStatus.FAILED,
            error=error,
            execution_time_ms=execution_time_ms,
            retry_count=retry_count
        )