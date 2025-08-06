from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
import enum

class AgentState(BaseModel):
    messages: List[BaseMessage]
    next_node: str
    tool_results: Optional[List[Dict]] = None

class ToolStatus(str, enum.Enum):
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL_SUCCESS = "partial_success"

class IndividualToolResult(BaseModel):
    status: ToolStatus
    message: str
    payload: Optional[Any] = None

class ToolResult(BaseModel):
    status: ToolStatus
    message: str
    results: Optional[List[IndividualToolResult]] = None
    payload: Optional[Any] = None

class DataSource(BaseModel):
    source_table: str
    filters: Optional[Dict[str, Any]] = None

class TimeRange(BaseModel):
    start_time: str
    end_time: str