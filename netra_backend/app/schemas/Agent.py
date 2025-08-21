"""Agent type definitions - imports from single source of truth in registry.py"""

import enum
from datetime import datetime
from typing import List, Optional, Dict, Any, TypedDict, Union, TypeVar, Generic
from pydantic import BaseModel, Field, ConfigDict
from langchain_core.messages import BaseMessage

# Import unified agent types from single source of truth
from netra_backend.app.schemas.registry import AgentStatus, AgentResult, AgentMetadata, ToolResultData, DeepAgentState, AgentState

class SubAgentLifecycle(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SHUTDOWN = "shutdown"

class TodoStatus(str, enum.Enum):
    """Strongly typed todo status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"

# ToolResultData and AgentState imported from registry.py

# Local AgentState compatible with LangChain
class LangChainAgentState(BaseModel):
    """LangChain-compatible agent state."""
    messages: List[BaseMessage]
    next_node: str
    tool_results: Optional[List[ToolResultData]] = None
    metadata: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)

class TodoItem(BaseModel):
    """Individual todo item"""
    id: str
    description: str
    completed: bool = False

class Todo(BaseModel):
    """Strongly typed todo with proper status enum"""
    id: str
    task: str
    status: TodoStatus
    items: List[TodoItem] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

class SubAgentState(BaseModel):
    messages: List[BaseMessage]
    next_node: str
    tool_results: Optional[List[ToolResultData]] = None
    lifecycle: SubAgentLifecycle = SubAgentLifecycle.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Union[str, int, dict]]] = None
    performance_metrics: Dict[str, Union[int, float]] = Field(default_factory=dict)

    def start(self):
        self.lifecycle = SubAgentLifecycle.RUNNING
        self.start_time = datetime.now()

    def complete(self):
        self.lifecycle = SubAgentLifecycle.COMPLETED
        self.end_time = datetime.now()

    def fail(self, error_message: str):
        self.lifecycle = SubAgentLifecycle.FAILED
        self.error_message = error_message
        self.end_time = datetime.now()

    def shutdown(self):
        self.lifecycle = SubAgentLifecycle.SHUTDOWN
        self.end_time = datetime.now()

class AgentStarted(BaseModel):
    run_id: str
    agent_name: str = "Supervisor"
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())

# AgentResult imported from registry.py

class AgentCompleted(BaseModel):
    run_id: str
    result: AgentResult
    execution_time_ms: float
    final_state: Optional[AgentState] = None

class AgentErrorMessage(BaseModel):
    run_id: str
    message: str

class SubAgentUpdate(BaseModel):
    sub_agent_name: str
    state: "SubAgentState"

class SubAgentStatus(BaseModel):
    agent_name: str
    tools: List[str]
    status: AgentStatus
    lifecycle: SubAgentLifecycle
    metrics: Dict[str, Union[int, float]] = Field(default_factory=dict)


