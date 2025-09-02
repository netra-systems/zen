"""Agent Execution Types

Core types for agent execution patterns.
Contains ExecutionContext and ExecutionResult for standardized execution.

Note: Legacy execution interface was removed as part of architecture simplification.
All agents now use single inheritance from BaseAgent only.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, Optional, Protocol, Union, runtime_checkable

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.schemas.agent_result_types import TypedAgentResult
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.core.id_manager import IDManager
# Note: Direct bridge imports removed for SSOT compliance
# Use emit_* methods from BaseAgent's WebSocketBridgeAdapter instead


@dataclass
class ExecutionContext:
    """Standardized execution context for all agents.
    
    CRITICAL: thread_id is now derived from run_id to ensure SSOT compliance.
    The IDManager handles all ID generation and extraction.
    """
    run_id: str
    agent_name: str
    state: DeepAgentState
    stream_updates: bool = False
    user_id: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    start_time: Optional[datetime] = None
    correlation_id: Optional[str] = None
    metadata: Optional[Dict[str, Union[str, int, float, bool, None]]] = None
    thread_id: Optional[str] = None  # For backwards compatibility in __init__
    _cached_thread_id: Optional[str] = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize metadata and validate ID consistency."""
        if self.metadata is None:
            self.metadata = {}
        
        # Add timestamp property for compatibility with error handling
        if not hasattr(self, 'timestamp'):
            self.timestamp = self.start_time or datetime.now(timezone.utc)
        
        # Store the explicitly provided thread_id for validation
        self._explicit_thread_id = self.thread_id
        
        # Validate run_id format
        if not IDManager.validate_run_id(self.run_id):
            # For backwards compatibility, allow invalid run_ids but log warning
            # This allows gradual migration of existing code
            import logging
            logging.warning(f"Invalid run_id format: '{self.run_id}'. Should be 'run_{{thread_id}}_{{uuid8}}'")
        
        # If explicit thread_id was provided, validate consistency
        if self._explicit_thread_id:
            extracted = IDManager.extract_thread_id(self.run_id)
            if extracted and extracted != self._explicit_thread_id:
                import logging
                logging.warning(
                    f"Thread ID mismatch: run_id contains '{extracted}' but "
                    f"explicit thread_id is '{self._explicit_thread_id}'. Using extracted value."
                )
        
        # Clear thread_id to force property getter logic
        self.thread_id = None
    
    @property
    def thread_id(self) -> Optional[str]:
        """Get thread_id, deriving from run_id if needed (SSOT pattern)."""
        if self._cached_thread_id is None:
            # Try to extract from run_id first (SSOT priority)
            extracted = IDManager.extract_thread_id(self.run_id)
            if extracted:
                self._cached_thread_id = extracted
            elif self._explicit_thread_id:
                # Fall back to explicitly provided thread_id for backwards compatibility
                self._cached_thread_id = self._explicit_thread_id
            elif hasattr(self.state, 'chat_thread_id') and self.state.chat_thread_id:
                # Final fallback to state's chat_thread_id for legacy support
                self._cached_thread_id = self.state.chat_thread_id
        
        return self._cached_thread_id
    
    @thread_id.setter
    def thread_id(self, value: Optional[str]) -> None:
        """Set thread_id with validation warning."""
        if value:
            # Check consistency with run_id
            extracted = IDManager.extract_thread_id(self.run_id)
            if extracted and extracted != value:
                import logging
                logging.warning(
                    f"Setting thread_id='{value}' but run_id contains '{extracted}'. "
                    "This violates SSOT. Consider regenerating run_id."
                )
        self._cached_thread_id = value
    
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
# from BaseAgent which already provides WebSocket functionality via WebSocketBridgeAdapter.