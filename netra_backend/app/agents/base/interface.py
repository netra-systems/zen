"""Base Agent Execution Interface

Core interface defining standardized agent execution patterns.
Provides consistent execution workflow for all agent types.

Business Value: Standardizes 40+ agent execute() methods.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Protocol, runtime_checkable
from dataclasses import dataclass
from datetime import datetime

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.schemas.agent_result_types import TypedAgentResult


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
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize metadata if not provided."""
        if self.metadata is None:
            self.metadata = {}
    
    def __hash__(self):
        """Make ExecutionContext hashable using run_id and agent_name."""
        # Include both run_id and agent_name for unique hash
        return hash((self.run_id, self.agent_name))
    
    def __eq__(self, other):
        """Compare ExecutionContext objects by run_id and agent_name."""
        if not isinstance(other, ExecutionContext):
            return False
        return self.run_id == other.run_id and self.agent_name == other.agent_name


@dataclass
class ExecutionResult:
    """Standardized execution result for all agents."""
    success: bool
    status: ExecutionStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    retry_count: int = 0
    fallback_used: bool = False
    metrics: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize metrics if not provided."""
        if self.metrics is None:
            self.metrics = {}


@runtime_checkable
class WebSocketManagerProtocol(Protocol):
    """Protocol for WebSocket manager interface."""
    
    async def send_agent_update(self, run_id: str, agent_name: str, 
                               update: Dict[str, Any]) -> None:
        """Send agent update via WebSocket."""
        ...


@runtime_checkable  
class ReliabilityManagerProtocol(Protocol):
    """Protocol for reliability manager interface."""
    
    async def execute_with_reliability(self, context: ExecutionContext,
                                     execute_func) -> ExecutionResult:
        """Execute function with reliability patterns."""
        ...
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get reliability health status."""
        ...


class BaseExecutionInterface(ABC):
    """Base interface for standardized agent execution.
    
    Provides consistent execution patterns across all agent types.
    Eliminates duplicate execute() methods and ensures standardization.
    """
    
    def __init__(self, agent_name: str, websocket_manager: Optional[WebSocketManagerProtocol] = None):
        self.agent_name = agent_name
        self.websocket_manager = websocket_manager
        
    @abstractmethod
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
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
        
    async def _send_websocket_update(self, context: ExecutionContext, 
                                   update: Dict[str, Any]) -> None:
        """Send WebSocket update with error handling."""
        try:
            await self.websocket_manager.send_agent_update(
                context.run_id, context.agent_name, update
            )
        except Exception:
            # Fail silently for WebSocket errors to not break execution
            pass


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
            start_time=datetime.utcnow(),
            correlation_id=getattr(self, 'correlation_id', None)
        )
    
    def create_success_result(self, result: Dict[str, Any], 
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