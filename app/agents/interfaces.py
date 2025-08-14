"""Interface definitions to break circular dependencies."""

from typing import Protocol, Dict, Any, Optional, List
from abc import ABC, abstractmethod


class AgentStateProtocol(Protocol):
    """Protocol for agent state objects."""
    
    user_request: str
    chat_thread_id: Optional[str]
    user_id: Optional[str]
    triage_result: Optional[Dict[str, Any]]
    data_result: Optional[Dict[str, Any]]
    optimizations_result: Optional[Dict[str, Any]]
    action_plan_result: Optional[Dict[str, Any]]
    report_result: Optional[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
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
                     run_id: str, stream_updates: bool = False) -> None:
        """Execute the agent."""
        ...


class ToolDispatcherProtocol(Protocol):
    """Protocol for tool dispatcher interface."""
    
    def has_tool(self, tool_name: str) -> bool:
        """Check if tool exists."""
        ...
    
    async def dispatch_tool(self, tool_name: str, 
                           parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch a tool call."""
        ...


class WebSocketManagerProtocol(Protocol):
    """Protocol for WebSocket manager interface."""
    
    async def send_agent_update(self, run_id: str, agent_name: str, 
                               update: Dict[str, Any]) -> None:
        """Send agent update via WebSocket."""
        ...
    
    async def send_to_thread(self, thread_id: str, 
                            message: Dict[str, Any]) -> None:
        """Send message to thread."""
        ...


class DatabaseSessionProtocol(Protocol):
    """Protocol for database session interface."""
    
    async def execute(self, query: str, parameters: Dict[str, Any] = None) -> Any:
        """Execute database query."""
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
                     run_id: str, stream_updates: bool = False) -> None:
        """Execute the agent - must be implemented by subclasses."""
        pass


class StatePersistenceProtocol(Protocol):
    """Protocol for state persistence service."""
    
    async def save_agent_state(self, run_id: str, thread_id: str, 
                              user_id: str, state: AgentStateProtocol, 
                              db_session: DatabaseSessionProtocol) -> None:
        """Save agent state."""
        ...
    
    async def load_agent_state(self, run_id: str, 
                              db_session: DatabaseSessionProtocol) -> Optional[AgentStateProtocol]:
        """Load agent state."""
        ...
    
    async def get_thread_context(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get thread context."""
        ...