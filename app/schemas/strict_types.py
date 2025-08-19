"""Strictly typed interfaces for agent system with no Any types allowed.

This module defines all agent interfaces with complete type safety,
replacing all Any types with proper typed unions and concrete types.
"""

from typing import Protocol, Dict, List, Optional, Union, Literal
from abc import ABC, abstractmethod
from datetime import datetime, UTC
from pydantic import BaseModel, Field

from app.agents.triage_sub_agent.models import TriageResult
from app.schemas.shared_types import (
    DataAnalysisResponse, AnomalyDetectionResponse, PerformanceMetrics
)
from app.schemas.websocket_message_types import WebSocketMessage
from app.schemas.core_enums import ExecutionStatus
from app.schemas.agent_result_types import (
    TypedAgentResult, JsonCompatibleDict, ExecutionResult, AgentExecutionResult
)


class StrictAgentState(Protocol):
    """Strictly typed protocol for agent state objects."""
    
    user_request: str
    chat_thread_id: Optional[str]
    user_id: Optional[str]
    triage_result: Optional[TriageResult]
    data_result: Optional[Union[DataAnalysisResponse, AnomalyDetectionResponse]]
    optimizations_result: Optional[Dict[str, Union[str, float, List[str]]]]
    action_plan_result: Optional[Dict[str, Union[str, List[str]]]]
    report_result: Optional[Dict[str, Union[str, datetime, List[str]]]]
    
    def to_dict(self) -> Dict[str, Union[str, int, float, bool, None]]:
        """Convert state to dictionary with typed values."""
        ...
    
    def merge_from(self, other: "StrictAgentState") -> None:
        """Merge state from another state object."""
        ...


class StrictDatabaseSession(Protocol):
    """Strictly typed protocol for database session interface."""
    
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


class StrictLLMManager(Protocol):
    """Strictly typed protocol for LLM manager interface."""
    
    async def ask_llm(self, prompt: str, 
                     llm_config_name: str = 'default') -> str:
        """Ask LLM for response with typed inputs and output."""
        ...
    
    async def ask_llm_with_context(self, prompt: str, 
                                  context: Dict[str, str],
                                  llm_config_name: str = 'default') -> str:
        """Ask LLM with context dictionary."""
        ...


class StrictWebSocketManager(Protocol):
    """Strictly typed protocol for WebSocket manager interface."""
    
    async def send_agent_update(self, run_id: str, agent_name: str, 
                               update: Dict[str, Union[str, float, bool]]) -> None:
        """Send agent update via WebSocket with typed payload."""
        ...
    
    async def send_to_thread(self, thread_id: str, 
                            message: WebSocketMessage) -> None:
        """Send typed message to thread."""
        ...
    
    async def send_message(self, user_id: str,
                          message: Dict[str, Union[str, int, bool]]) -> None:
        """Send typed message to user."""
        ...


class StrictToolDispatcher(Protocol):
    """Strictly typed protocol for tool dispatcher interface."""
    
    def has_tool(self, tool_name: str) -> bool:
        """Check if tool exists."""
        ...
    
    async def dispatch_tool(self, tool_name: str, 
                           parameters: Dict[str, Union[str, int, float, bool]]
                           ) -> Dict[str, Union[str, int, float, bool, List[str]]]:
        """Dispatch a tool call with typed parameters and result."""
        ...
    
    async def list_available_tools(self) -> List[str]:
        """List all available tool names."""
        ...


class AgentExecutionContext(BaseModel):
    """Typed context for agent execution."""
    run_id: str = Field(min_length=1, max_length=255)
    agent_name: str = Field(min_length=1, max_length=100)
    user_id: Optional[str] = Field(default=None, max_length=255)
    thread_id: Optional[str] = Field(default=None, max_length=255)
    stream_updates: bool = Field(default=False)
    execution_start: datetime = Field(default_factory=lambda: datetime.now(UTC))
    timeout_seconds: int = Field(default=300, ge=1, le=3600)


class AgentExecutionMetrics(BaseModel):
    """Typed metrics for agent execution."""
    execution_time_ms: float = Field(ge=0.0)
    memory_usage_mb: Optional[float] = Field(default=None, ge=0.0)
    llm_tokens_used: int = Field(default=0, ge=0)
    database_queries: int = Field(default=0, ge=0)
    websocket_messages_sent: int = Field(default=0, ge=0)
    errors_encountered: int = Field(default=0, ge=0)


class StrictAgentProtocol(Protocol):
    """Strictly typed protocol for base agent interface."""
    
    name: str
    description: str
    
    async def execute(self, state: StrictAgentState, 
                     context: AgentExecutionContext) -> AgentExecutionResult:
        """Execute the agent with strictly typed parameters."""
        ...
    
    async def validate_inputs(self, state: StrictAgentState,
                             context: AgentExecutionContext) -> bool:
        """Validate inputs before execution."""
        ...
    
    def get_execution_metrics(self) -> AgentExecutionMetrics:
        """Get execution metrics for the agent."""
        ...



class StrictStatePersistence(Protocol):
    """Strictly typed protocol for state persistence service."""
    
    async def save_agent_state(self, run_id: str, thread_id: str, 
                              user_id: str, state: StrictAgentState, 
                              db_session: StrictDatabaseSession) -> bool:
        """Save agent state with typed parameters."""
        ...
    
    async def load_agent_state(self, run_id: str, 
                              db_session: StrictDatabaseSession
                              ) -> Optional[StrictAgentState]:
        """Load agent state with typed return."""
        ...
    
    async def get_thread_context(self, thread_id: str
                                ) -> Optional[Dict[str, Union[str, int, datetime]]]:
        """Get thread context with typed return."""
        ...


class TriageAgentProtocol(StrictAgentProtocol, Protocol):
    """Strictly typed protocol for triage agent."""
    
    async def execute(self, state: StrictAgentState, 
                     context: AgentExecutionContext) -> TypedAgentResult:
        """Execute triage with TriageResult."""
        ...
    
    async def classify_request(self, user_request: str) -> TriageResult:
        """Classify user request and return typed result."""
        ...


class DataAgentProtocol(StrictAgentProtocol, Protocol):
    """Strictly typed protocol for data agent."""
    
    async def execute(self, state: StrictAgentState, 
                     context: AgentExecutionContext) -> TypedAgentResult:
        """Execute data analysis with DataAnalysisResponse."""
        ...
    
    async def analyze_data(self, query: str, 
                          parameters: Dict[str, Union[str, int, float]]
                          ) -> DataAnalysisResponse:
        """Analyze data with typed parameters."""
        ...
    
    async def detect_anomalies(self, dataset: str,
                              threshold: float) -> AnomalyDetectionResponse:
        """Detect anomalies with typed threshold."""
        ...


class SupervisorAgentProtocol(StrictAgentProtocol, Protocol):
    """Strictly typed protocol for supervisor agent."""
    
    async def orchestrate_agents(self, state: StrictAgentState,
                                context: AgentExecutionContext,
                                agent_sequence: List[str]) -> TypedAgentResult:
        """Orchestrate multiple agents with typed sequence."""
        ...
    
    async def monitor_execution(self, run_id: str) -> Dict[str, Union[str, float, bool]]:
        """Monitor agent execution with typed status."""
        ...


# Type aliases for better readability
StrictAgentResultType = Union[TriageResult, DataAnalysisResponse, AnomalyDetectionResponse]
StrictParameterType = Union[str, int, float, bool]
StrictReturnType = Union[str, int, float, bool, List[str], Dict[str, StrictParameterType]]


class AgentTypeRegistry:
    """Registry for agent type mappings."""
    
    AGENT_RESULT_TYPES = {
        'triage': TriageResult,
        'data': Union[DataAnalysisResponse, AnomalyDetectionResponse],
        'optimization': Dict[str, Union[str, float, List[str]]],
        'action_plan': Dict[str, Union[str, List[str]]],
        'report': Dict[str, Union[str, datetime, List[str]]]
    }
    
    @classmethod
    def get_result_type(cls, agent_name: str) -> type:
        """Get expected result type for agent."""
        return cls.AGENT_RESULT_TYPES.get(agent_name.lower(), Dict)
    
    @classmethod
    def validate_result_type(cls, agent_name: str, result) -> bool:
        """Validate result matches expected type for agent."""
        expected_type = cls.get_result_type(agent_name)
        return isinstance(result, expected_type)