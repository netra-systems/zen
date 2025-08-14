"""
Shared production types and classes to eliminate duplicate type definitions.
Single source of truth for production types used across multiple modules.
"""

from typing import Dict, Optional, List, AsyncGenerator, Union, Any
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import asyncio

# Avoid circular imports by using TYPE_CHECKING
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.agents.state import DeepAgentState
    from app.llm.llm_manager import LLMManager
    from app.agents.base import BaseSubAgent
    from app.agents.tool_dispatcher import ToolDispatcher

# Type aliases for common patterns to replace Any usage
PrimitiveType = Union[str, int, float, bool, None]
JsonCompatibleDict = Dict[str, PrimitiveType]
NestedJsonDict = Dict[str, Union[PrimitiveType, List[PrimitiveType], Dict[str, PrimitiveType]]]
ExecutionResult = Union[JsonCompatibleDict, List[JsonCompatibleDict], str, bool, None]
ToolParameters = Dict[str, Union[str, int, float, bool]]
ToolResult = Dict[str, Union[str, int, float, bool, List[str]]]
AgentState = 'DeepAgentState'  # Forward reference
# AgentExecutionResult moved to strict_types.py to avoid circular imports


class AgentStatus(str, Enum):
    """Standard agent status enumeration"""
    INITIALIZING = "initializing"
    READY = "ready"
    PROCESSING = "processing"
    ERROR = "error"
    STOPPED = "stopped"


class ProcessingResult(BaseModel):
    """Standard processing result structure"""
    status: str = Field(..., description="Processing status")
    data: Optional[Dict[str, Union[str, int, float, bool]]] = Field(default=None, description="Result data")
    metadata: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict, description="Processing metadata")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Processing timestamp")


class ErrorContext(BaseModel):
    """Standard error context for consistent error handling across all modules"""
    # Core identifiers  
    trace_id: str = Field(..., description="Unique trace identifier")
    operation: str = Field(..., description="Operation being performed")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    user_id: Optional[str] = Field(default=None, description="User identifier")
    
    # Additional context for compatibility with existing code
    correlation_id: Optional[str] = Field(default=None, description="Correlation identifier")
    request_id: Optional[str] = Field(default=None, description="Request identifier")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    
    # Agent-specific context
    agent_name: Optional[str] = Field(default=None, description="Agent name")
    operation_name: Optional[str] = Field(default=None, description="Operation name")
    run_id: Optional[str] = Field(default=None, description="Run identifier")
    retry_count: int = Field(default=0, description="Retry count")
    max_retries: int = Field(default=3, description="Maximum retries")
    
    # General context data
    details: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict, description="Error details")
    additional_data: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict, description="Additional context data")
    
    # Compatibility fields for existing code
    component: Optional[str] = Field(default=None, description="Component name")
    severity: Optional[str] = Field(default=None, description="Error severity")
    error_code: Optional[str] = Field(default=None, description="Error code")


class BaseAgentInterface(ABC):
    """Base interface for agent implementations to ensure consistency"""
    
    @abstractmethod
    def __init__(self, llm_manager: 'LLMManager', tool_dispatcher: 'ToolDispatcher') -> None:
        pass
    
    @abstractmethod
    async def execute(self, state: 'DeepAgentState', session_id: str, **kwargs) -> Any:
        pass
    
    @abstractmethod
    def _init_components(self) -> None:
        pass


class ToolExecutionContext(BaseModel):
    """Context for tool execution with permissions"""
    user_id: str = Field(..., description="User identifier")
    tool_name: str = Field(..., description="Tool being executed")
    requested_action: str = Field(..., description="Requested action")
    user_plan: str = Field(..., description="User subscription plan")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    permissions: Dict[str, Any] = Field(default_factory=dict, description="User permissions")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context")


class CacheKey(BaseModel):
    """Standard cache key structure"""
    prefix: str = Field(..., description="Cache key prefix")
    identifier: str = Field(..., description="Unique identifier")
    version: str = Field(default="v1", description="Cache version")
    
    def to_string(self) -> str:
        """Convert to cache key string"""
        return f"{self.prefix}:{self.version}:{self.identifier}"


class ServiceHealth(BaseModel):
    """Standard service health check response"""
    service_name: str = Field(..., description="Service name")
    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    dependencies: Dict[str, str] = Field(default_factory=dict, description="Dependency statuses")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Health metrics")


class ApiResponse(BaseModel):
    """Standard API response structure"""
    success: bool = Field(..., description="Operation success status")
    data: Optional[Any] = Field(default=None, description="Response data")
    message: Optional[str] = Field(default=None, description="Response message")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Response metadata")


class EventContext(BaseModel):
    """Context for event processing"""
    event_id: str = Field(..., description="Unique event identifier")
    event_type: str = Field(..., description="Event type")
    source: str = Field(..., description="Event source")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(..., description="Event data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Event metadata")


# Common constants and utilities
DEFAULT_CACHE_TTL = 300  # 5 minutes
DEFAULT_TIMEOUT = 30  # 30 seconds
DEFAULT_RETRY_ATTEMPTS = 3

# Type aliases for common patterns
AgentConfigDict = Dict[str, Any]
ProcessingContextDict = Dict[str, Any]
MetadataDict = Dict[str, Any]