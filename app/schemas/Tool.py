import enum
import time
from typing import List, Any, Optional, Dict, Union, TypeVar, Generic
from pydantic import BaseModel, Field, ConfigDict

class ToolStatus(str, enum.Enum):
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL_SUCCESS = "partial_success"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"

class ToolPayload(BaseModel):
    """Base class for structured tool payloads"""
    model_config = ConfigDict(extra='forbid')

class SimpleToolPayload(ToolPayload):
    """Payload for simple tool results"""
    result: Union[str, int, float, bool, dict, list, None] = None

class ToolArguments(BaseModel):
    """Structured arguments for tool invocation"""
    model_config = ConfigDict(extra='allow')

T = TypeVar('T', bound=ToolPayload)

class ToolInput(BaseModel, Generic[T]):
    tool_name: str
    args: List[Union[str, int, float, bool, dict, list]] = Field(default_factory=list)
    kwargs: Dict[str, Union[str, int, float, bool, dict, list]] = Field(default_factory=dict)
    structured_args: Optional[ToolArguments] = None

class ToolResult(BaseModel, Generic[T]):
    tool_input: ToolInput[T]
    status: ToolStatus = ToolStatus.IN_PROGRESS
    message: str = ""
    payload: Optional[T] = None
    error_details: Optional[Dict[str, Union[str, int, dict]]] = None
    start_time: float = Field(default_factory=time.time)
    end_time: Optional[float] = None
    execution_metadata: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)

    def complete(self, status: ToolStatus, message: str, payload: Optional[T] = None, error_details: Optional[Dict[str, Union[str, int, dict]]] = None):
        self.status = status
        self.message = message
        self.payload = payload
        self.error_details = error_details
        self.end_time = time.time()

class ToolInvocation(BaseModel, Generic[T]):
    tool_result: ToolResult[T]

    def __init__(self, tool_name: str, *args, **kwargs):
        structured_args = kwargs.pop('structured_args', None)
        super().__init__(tool_result=ToolResult(
            tool_input=ToolInput(
                tool_name=tool_name, 
                args=list(args), 
                kwargs=kwargs,
                structured_args=structured_args
            )
        ))

    def set_result(self, status: ToolStatus, message: str, payload: Optional[T] = None, error_details: Optional[Dict[str, Union[str, int, dict]]] = None):
        self.tool_result.complete(status, message, payload, error_details)

class ToolStarted(BaseModel):
    tool_name: str

class ToolCompletionData(BaseModel):
    """Structured data for tool completion"""
    output: Optional[Union[str, dict, list]] = None
    metrics: Optional[Dict[str, Union[int, float]]] = None
    artifacts: Optional[List[str]] = None

class ToolCompleted(BaseModel):
    tool_name: str
    result: Union[ToolCompletionData, str, dict]
    status: ToolStatus
    execution_time_ms: Optional[float] = None
