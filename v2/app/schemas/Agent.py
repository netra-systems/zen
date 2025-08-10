import enum
from datetime import datetime
from typing import List, Optional, Dict, Any, TypedDict
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage

class SubAgentLifecycle(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SHUTDOWN = "shutdown"

class AgentState(BaseModel):
    messages: List[BaseMessage]
    next_node: str
    tool_results: Optional[List[Dict]] = None

class Todo(TypedDict):
    id: str
    task: str
    status: str
    items: List[str]

class SubAgentState(BaseModel):
    messages: List[BaseMessage]
    next_node: str
    tool_results: Optional[List[Dict]] = None
    lifecycle: SubAgentLifecycle = SubAgentLifecycle.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None

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

class AgentCompleted(BaseModel):
    run_id: str
    result: Any

class AgentErrorMessage(BaseModel):
    run_id: str
    message: str

class SubAgentUpdate(BaseModel):
    sub_agent_name: str
    state: "SubAgentState"

class SubAgentStatus(BaseModel):
    agent_name: str
    tools: List[str]
    status: str