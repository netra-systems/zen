from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Union

class WebSocketMessage(BaseModel):
    event: str
    data: Any
    run_id: str

class RunCompleteMessage(WebSocketMessage):
    event: str = "run_complete"

class ErrorData(BaseModel):
    type: str
    message: str

class ErrorMessage(WebSocketMessage):
    event: str = "error"
    data: ErrorData

class StreamEventMessage(WebSocketMessage):
    event: str = "stream_event"
    event_type: str

class ToolStatus(BaseModel):
    tool_name: str
    status: str
    message: Optional[str] = None

class AgentUpdateData(BaseModel):
    agent: str
    messages: List[Dict[str, Any]]
    tools_status: List[ToolStatus]

class AgentUpdateMessage(WebSocketMessage):
    event: str = "agent_update"
    data: AgentUpdateData
