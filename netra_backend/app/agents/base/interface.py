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
    
    def __init__(self, agent_name: str, websocket_manager: Optional[WebSocketManagerProtocol] = None) -> None:
        self.agent_name = agent_name
        self.websocket_manager = websocket_manager
        
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
        
    async def _send_websocket_update(self, context: ExecutionContext, 
                                   update: Dict[str, Union[str, int, float, bool, Dict, list, None]]) -> None:
        """Send WebSocket update with error handling."""
        try:
            bridge = await get_agent_websocket_bridge()
            
            # Route updates through Bridge based on type
            update_type = update.get("type")
            if update_type == "agent_thinking":
                await bridge.notify_agent_thinking(
                    context.run_id, 
                    context.agent_name, 
                    update["payload"]["thought"],
                    update["payload"].get("step_number")
                )
            elif update_type == "partial_result":
                await bridge.notify_progress_update(
                    context.run_id,
                    context.agent_name,
                    {
                        "message": update["payload"]["content"],
                        "status": "completed" if update["payload"]["is_complete"] else "in_progress",
                        "progress_type": "partial_result"
                    }
                )
            elif update_type == "tool_executing":
                await bridge.notify_tool_executing(
                    context.run_id,
                    context.agent_name,
                    update["payload"]["tool_name"]
                )
            else:
                # Default status updates
                status = update.get("status", "")
                message = update.get("message", "")
                if status == "starting":
                    await bridge.notify_agent_started(context.run_id, context.agent_name, {"message": message})
                elif status == "completed":
                    await bridge.notify_agent_completed(context.run_id, context.agent_name, {"message": message})
                elif status == "error":
                    await bridge.notify_agent_error(context.run_id, context.agent_name, message)
                else:
                    await bridge.notify_agent_thinking(context.run_id, context.agent_name, message)
        except Exception:
            # Fail silently for WebSocket errors to not break execution
            pass
    
    async def send_agent_thinking(self, context_or_run_id: Union[ExecutionContext, str], thought: str, step_number: Optional[int] = None) -> None:
        """Send agent thinking notification via WebSocket.
        
        Args:
            context_or_run_id: ExecutionContext object OR legacy run_id string
            thought: The thinking content
            step_number: Optional step number
        """
        # Handle legacy run_id-based calls for backward compatibility
        if isinstance(context_or_run_id, str):
            context = self._create_legacy_execution_context(context_or_run_id)
        else:
            context = context_or_run_id
            
        if not self.websocket_manager or not context.stream_updates:
            return
        update = {
            "type": "agent_thinking",
            "payload": {
                "thought": thought,
                "agent_name": context.agent_name,
                "step_number": step_number,
                "timestamp": datetime.now(timezone.utc).timestamp()
            }
        }
        await self._send_websocket_update(context, update)
    
    async def send_partial_result(self, context_or_run_id: Union[ExecutionContext, str], content: str, is_complete: bool = False) -> None:
        """Send partial result notification via WebSocket.
        
        Args:
            context_or_run_id: ExecutionContext object OR legacy run_id string
            content: The partial result content
            is_complete: Whether this is the final result
        """
        # Handle legacy run_id-based calls for backward compatibility
        if isinstance(context_or_run_id, str):
            context = self._create_legacy_execution_context(context_or_run_id)
        else:
            context = context_or_run_id
            
        if not self.websocket_manager or not context.stream_updates:
            return
        update = {
            "type": "partial_result", 
            "payload": {
                "content": content,
                "agent_name": context.agent_name,
                "is_complete": is_complete,
                "timestamp": datetime.now(timezone.utc).timestamp()
            }
        }
        await self._send_websocket_update(context, update)
    
    async def send_tool_executing(self, context_or_run_id: Union[ExecutionContext, str], tool_name: str) -> None:
        """Send tool executing notification via WebSocket.
        
        Args:
            context_or_run_id: ExecutionContext object OR legacy run_id string
            tool_name: The name of the executing tool
        """
        # Handle legacy run_id-based calls for backward compatibility
        if isinstance(context_or_run_id, str):
            context = self._create_legacy_execution_context(context_or_run_id)
        else:
            context = context_or_run_id
            
        if not self.websocket_manager or not context.stream_updates:
            return
        update = {
            "type": "tool_executing",
            "payload": {
                "tool_name": tool_name,
                "agent_name": context.agent_name,
                "timestamp": datetime.now(timezone.utc).timestamp()
            }
        }
        await self._send_websocket_update(context, update)
    
    async def send_final_report(self, context_or_run_id: Union[ExecutionContext, str], report: Dict[str, Union[str, int, float, bool, Dict, list, None]], duration_ms: float) -> None:
        """Send final report notification via WebSocket.
        
        Args:
            context_or_run_id: ExecutionContext object OR legacy run_id string
            report: The final report data
            duration_ms: Execution duration in milliseconds
        """
        # Handle legacy run_id-based calls for backward compatibility
        if isinstance(context_or_run_id, str):
            context = self._create_legacy_execution_context(context_or_run_id)
        else:
            context = context_or_run_id
            
        if not self.websocket_manager or not context.stream_updates:
            return
        update = {
            "type": "final_report",
            "payload": {
                "report": report,
                "total_duration_ms": duration_ms,
                "agent_name": context.agent_name,
                "timestamp": datetime.now(timezone.utc).timestamp()
            }
        }
        await self._send_websocket_update(context, update)
    
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