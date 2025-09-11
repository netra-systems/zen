import enum
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Generic, List, Optional, TypeVar, Union

from pydantic import BaseModel, ConfigDict, Field

# Import types only for type checking to avoid circular dependencies  
if TYPE_CHECKING:
    # DeepAgentState deprecated - use UserExecutionContext pattern instead
    from netra_backend.app.services.user_execution_context import UserExecutionContext

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
        tool_input = self._create_tool_input(tool_name, args, kwargs, structured_args)
        super().__init__(tool_result=ToolResult(tool_input=tool_input))
    
    def _create_tool_input(self, tool_name: str, args: tuple, kwargs: dict, 
                          structured_args: Optional[ToolArguments]) -> ToolInput:
        """Create ToolInput object from parameters."""
        return ToolInput(
            tool_name=tool_name, args=list(args), 
            kwargs=kwargs, structured_args=structured_args
        )

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


# Tool System Core Types (Single Source of Truth)
class ToolExecuteResponse(BaseModel):
    """Typed response for tool execution - consolidated from duplicates"""
    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ToolDispatchResponse(BaseModel):
    """Typed response for tool dispatch - consolidated from duplicates"""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Tool System Interface Definitions
class BaseTool(ABC):
    """Base interface for all tools"""
    
    @abstractmethod
    async def execute(
        self, 
        parameters: Dict[str, Any], 
        state: Optional["DeepAgentState"], 
        run_id: Optional[str]
    ) -> Dict[str, Any]:
        """Execute the tool with given parameters"""
        pass


class ToolRegistryInterface(ABC):
    """Interface for tool registry implementations"""
    
    @abstractmethod
    def register_tool(self, tool: BaseTool) -> None:
        """Register a single tool"""
        pass
    
    @abstractmethod
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name"""
        pass


class ToolExecutionEngineInterface(ABC):
    """Interface for tool execution engine implementations"""
    
    @abstractmethod
    async def execute_tool(
        self, 
        tool_name: str, 
        parameters: Dict[str, Any]
    ) -> ToolExecuteResponse:
        """Execute a tool by name with parameters"""
        pass


class ToolDispatcherInterface(ABC):
    """Interface for tool dispatcher implementations"""
    
    @abstractmethod
    async def dispatch(
        self, 
        tool_name: str, 
        parameters: Dict[str, Any]
    ) -> ToolDispatchResponse:
        """Dispatch a tool execution request"""
        pass
