import uuid
import enum
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Literal
from pydantic import BaseModel, Field
from .Message import Message
from .Tool import ToolStarted, ToolCompleted
from .Run import RunComplete
from .Agent import AgentStarted, AgentCompleted, AgentErrorMessage, SubAgentUpdate, SubAgentStatus
from .Request import RequestModel

class WebSocketError(BaseModel):
    message: str

class MessageToUser(BaseModel):
    sender: str  # e.g., "user", "agent"
    content: str
    references: Optional[List[str]] = None
    raw_json: Optional[Dict] = None
    error: Optional[str] = None

class AnalysisRequest(BaseModel):
    request_model: RequestModel

class UserMessage(BaseModel):
    text: str
    references: List[str] = []

class AgentMessage(BaseModel):
    text: str

class StopAgent(BaseModel):
    run_id: str

class StreamEvent(BaseModel):
    event_type: str
    data: Dict[str, Any]

class WebSocketMessage(BaseModel):
    type: Literal["analysis_request", "error", "stream_event", "run_complete", "sub_agent_update", "agent_started", "agent_completed", "agent_error", "user_message", "agent_message", "tool_started", "tool_completed", "stop_agent", "message", "sub_agent_status"]
    payload: Union[AnalysisRequest, WebSocketError, StreamEvent, RunComplete, SubAgentUpdate, AgentStarted, AgentCompleted, AgentErrorMessage, UserMessage, AgentMessage, ToolStarted, ToolCompleted, StopAgent, Message, SubAgentStatus]
