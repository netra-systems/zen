"""Interface definitions to break circular dependencies."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Protocol, Union

from netra_backend.app.agents.triage_sub_agent.models import TriageResult
from netra_backend.app.schemas.shared_types import (
    AnomalyDetectionResponse,
    DataAnalysisResponse,
)
from netra_backend.app.schemas.strict_types import (
    AgentExecutionContext,
    AgentExecutionMetrics,
    StrictParameterType,
    StrictReturnType,
    TypedAgentResult,
)


class AgentStateProtocol(Protocol):
    """Protocol for agent state objects."""
    
    user_request: str
    chat_thread_id: Optional[str]
    user_id: Optional[str]
    triage_result: Optional[TriageResult]
    data_result: Optional[Union[DataAnalysisResponse, AnomalyDetectionResponse]]
    optimizations_result: Optional[Dict[str, Union[str, float, List[str]]]]
    action_plan_result: Optional[Dict[str, Union[str, List[str]]]]
    report_result: Optional[Dict[str, Union[str, datetime, List[str]]]]
    
    def to_dict(self) -> Dict[str, Union[str, int, float, bool, None]]:
        """Convert state to dictionary."""
        ...
    
    def merge_from(self, other: "AgentStateProtocol") -> None:
        """Merge state from another state object."""
        ...


class BaseAgentProtocol(Protocol):
    """Protocol for base agent interface."""
    
    name: str
    description: str
    
    async def execute(self, state: AgentStateProtocol, 
                     run_id: str, stream_updates: bool = False) -> TypedAgentResult:
        """Execute the agent with typed return."""
        ...
    
    def get_execution_metrics(self) -> AgentExecutionMetrics:
        """Get execution metrics for the agent."""
        ...


class ToolDispatcherProtocol(Protocol):
    """Protocol for tool dispatcher interface."""
    
    def has_tool(self, tool_name: str) -> bool:
        """Check if tool exists."""
        ...
    
    async def dispatch_tool(self, tool_name: str, 
                           parameters: Dict[str, StrictParameterType]
                           ) -> Dict[str, StrictReturnType]:
        """Dispatch a tool call with typed parameters."""
        ...
    
    async def list_available_tools(self) -> List[str]:
        """List all available tool names."""
        ...


class WebSocketManagerProtocol(Protocol):
    """Protocol for WebSocket manager interface."""
    
    async def send_agent_update(self, run_id: str, agent_name: str, 
                               update: Dict[str, Union[str, float, bool]]) -> None:
        """Send agent update via WebSocket."""
        ...
    
    async def send_to_thread(self, thread_id: str, 
                            message: Dict[str, Union[str, int, bool]]) -> None:
        """Send message to thread."""
        ...


class DatabaseSessionProtocol(Protocol):
    """Protocol for database session interface."""
    
    async def execute(self, query: str, 
                     parameters: Optional[Dict[str, Union[str, int, float]]] = None
                     ) -> List[Dict[str, Union[str, int, float, datetime]]]:
        """Execute database query with typed parameters."""
        ...
    
    async def commit(self) -> None:
        """Commit transaction."""
        ...
    
    async def rollback(self) -> None:
        """Rollback transaction."""
        ...


class LLMManagerProtocol(Protocol):
    """Protocol for LLM manager interface."""
    
    async def ask_llm(self, prompt: str, 
                     llm_config_name: str = 'default') -> str:
        """Ask LLM for response."""
        ...


# Abstract base classes for stronger typing when needed
class BaseAgent(ABC):
    """Abstract base class for agents."""
    
    def __init__(self, llm_manager: LLMManagerProtocol, 
                 name: str, description: str):
        self.llm_manager = llm_manager
        self.name = name
        self.description = description
    
    @abstractmethod
    async def execute(self, state: AgentStateProtocol, 
                     run_id: str, stream_updates: bool = False) -> TypedAgentResult:
        """Execute the agent - must be implemented by subclasses."""
        pass
    
    def get_execution_metrics(self) -> AgentExecutionMetrics:
        """Get execution metrics for the agent."""
        return AgentExecutionMetrics(
            execution_time_ms=0.0,
            llm_tokens_used=0,
            database_queries=0,
            websocket_messages_sent=0
        )


class StatePersistenceProtocol(Protocol):
    """Protocol for state persistence service."""
    
    async def save_agent_state(self, run_id: str, thread_id: str, 
                              user_id: str, state: AgentStateProtocol, 
                              db_session: DatabaseSessionProtocol) -> bool:
        """Save agent state with typed return."""
        ...
    
    async def load_agent_state(self, run_id: str, 
                              db_session: DatabaseSessionProtocol) -> Optional[AgentStateProtocol]:
        """Load agent state."""
        ...
    
    async def get_thread_context(self, thread_id: str
                                ) -> Optional[Dict[str, Union[str, int, datetime]]]:
        """Get thread context with typed return."""
        ...