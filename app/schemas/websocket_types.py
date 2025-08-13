"""Strong type definitions for WebSocket messages and payloads.

This module provides TypedDict and Pydantic models for all WebSocket
message types to ensure type safety across the application.

NOTE: This module avoids duplicating types already defined in other schemas.
It imports and reuses existing types where possible.
"""

from typing import TypedDict, Literal, Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum

# Import existing types to avoid duplication
from app.schemas.Request import StartAgentPayload as StartAgentPayloadPydantic


# TypedDict definitions for WebSocket messages
class BaseMessagePayload(TypedDict):
    """Base payload structure"""
    pass


class UserMessagePayload(TypedDict):
    """Payload for user_message"""
    text: str
    references: Optional[List[str]]
    thread_id: Optional[str]


class ThreadMetadata(BaseModel):
    """Strongly typed thread metadata"""
    tags: List[str] = Field(default_factory=list)
    priority: Optional[int] = Field(default=None, ge=0, le=10)
    category: Optional[str] = None
    custom_fields: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)

class CreateThreadPayload(TypedDict):
    """Payload for create_thread"""
    name: Optional[str]
    metadata: Optional[ThreadMetadata]


class SwitchThreadPayload(TypedDict):
    """Payload for switch_thread"""
    thread_id: str


class DeleteThreadPayload(TypedDict):
    """Payload for delete_thread"""
    thread_id: str


class MessageData(BaseModel):
    """Strongly typed message data"""
    id: str
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    timestamp: datetime
    metadata: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)

class ThreadHistoryResponse(TypedDict):
    """Response structure for thread history"""
    thread_id: str
    messages: List[MessageData]


class AgentResponseData(BaseModel):
    """Strongly typed agent response"""
    success: bool
    message: str
    data: Optional[Union[str, dict, list]] = None
    metrics: Dict[str, Union[int, float]] = Field(default_factory=dict)

class AgentCompletedPayload(TypedDict):
    """Payload for agent_completed message"""
    response: AgentResponseData
    thread_id: Optional[str]
    run_id: Optional[str]


class AgentStoppedPayload(TypedDict):
    """Payload for agent_stopped message"""
    status: Literal["stopped"]


class ErrorCode(str, Enum):
    """Standard error codes"""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    RATE_LIMIT = "RATE_LIMIT"
    TIMEOUT = "TIMEOUT"
    DEPENDENCY_ERROR = "DEPENDENCY_ERROR"

class ErrorDetails(BaseModel):
    """Strongly typed error details"""
    field: Optional[str] = None
    reason: Optional[str] = None
    suggestion: Optional[str] = None
    trace_id: Optional[str] = None

class ErrorPayload(TypedDict):
    """Payload for error messages"""
    error: str
    code: Optional[ErrorCode]
    details: Optional[ErrorDetails]


# Message type literals
MessageTypeLiteral = Literal[
    "start_agent",
    "user_message",
    "get_thread_history",
    "stop_agent",
    "create_thread",
    "switch_thread",
    "delete_thread",
    "list_threads",
    "agent_completed",
    "agent_stopped",
    "thread_history",
    "error",
    "agent_update",
    "tool_started",
    "tool_completed",
    "subagent_started",
    "subagent_completed"
]


class WebSocketMessageIn(TypedDict):
    """Incoming WebSocket message structure"""
    type: MessageTypeLiteral
    payload: Optional[Union[UserMessagePayload, CreateThreadPayload, SwitchThreadPayload, DeleteThreadPayload, Dict[str, Union[str, int, float, bool, list, dict]]]]


class WebSocketMessageOut(TypedDict):
    """Outgoing WebSocket message structure"""
    type: MessageTypeLiteral
    payload: Union[ThreadHistoryResponse, AgentCompletedPayload, AgentStoppedPayload, ErrorPayload, Dict[str, Union[str, int, float, bool, list, dict]]]
    timestamp: Optional[str]


# Pydantic models for validation
class WebSocketRequest(BaseModel):
    """Base model for WebSocket requests"""
    type: MessageTypeLiteral
    payload: Optional[Dict[str, Union[str, int, float, bool, list, dict]]] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "user_message",
                "payload": {
                    "text": "Analyze my workload",
                    "thread_id": "thread-123"
                }
            }
        }


class WebSocketResponse(BaseModel):
    """Base model for WebSocket responses"""
    type: MessageTypeLiteral
    payload: Dict[str, Union[str, int, float, bool, list, dict]] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "agent_completed",
                "payload": {"response": "Analysis complete"},
                "timestamp": "2025-01-12T10:00:00Z"
            }
        }


class ThreadMessage(BaseModel):
    """Model for a message in a thread"""
    id: str
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None
    references: Optional[List[str]] = None


class ThreadInfo(BaseModel):
    """Model for thread information"""
    id: str
    name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    message_count: int = 0


class AgentUpdatePayload(BaseModel):
    """Payload for agent update messages"""
    status: Literal["thinking", "planning", "executing", "completed", "error"]
    message: Optional[str] = None
    progress: Optional[float] = None  # 0.0 to 1.0
    current_task: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ToolInput(BaseModel):
    """Strongly typed tool input"""
    parameters: Dict[str, Union[str, int, float, bool, list]] = Field(default_factory=dict)
    options: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)

class ToolOutput(BaseModel):
    """Strongly typed tool output"""
    success: bool
    data: Optional[Union[str, dict, list]] = None
    error: Optional[str] = None
    metadata: Dict[str, Union[str, int, float]] = Field(default_factory=dict)

class ToolInvocationPayload(BaseModel):
    """Payload for tool invocation messages"""
    tool_name: str
    tool_input: ToolInput
    tool_id: str
    status: Literal["started", "completed", "error"]
    result: Optional[ToolOutput] = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None


class SubAgentResult(BaseModel):
    """Strongly typed sub-agent result"""
    success: bool
    output: Optional[Union[str, dict, list]] = None
    artifacts: List[str] = Field(default_factory=list)
    metrics: Dict[str, Union[int, float]] = Field(default_factory=dict)

class SubAgentMetadata(BaseModel):
    """Strongly typed sub-agent metadata"""
    priority: Optional[int] = Field(default=None, ge=0, le=10)
    retry_count: int = Field(default=0)
    parent_agent_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

class SubAgentPayload(BaseModel):
    """Payload for sub-agent messages"""
    agent_name: str
    agent_id: str
    status: Literal["started", "running", "completed", "error"]
    task: Optional[str] = None
    result: Optional[SubAgentResult] = None
    error: Optional[str] = None
    metadata: Optional[SubAgentMetadata] = None


# Type aliases for better readability
ParsedMessage = Union[WebSocketMessageIn, Dict[str, Union[str, int, float, bool, list, dict]]]
MessageHandler = Dict[MessageTypeLiteral, callable]  # Maps message types to handler functions


# Enhanced strong typing for WebSocket operations
class WebSocketMessageType(str, Enum):
    """All supported WebSocket message types as enum for type safety"""
    # Client -> Server
    USER_MESSAGE = "user_message"
    START_AGENT = "start_agent"
    STOP_AGENT = "stop_agent"
    CREATE_THREAD = "create_thread"
    SWITCH_THREAD = "switch_thread"
    DELETE_THREAD = "delete_thread"
    LIST_THREADS = "list_threads"
    GET_THREAD_HISTORY = "get_thread_history"
    
    # Server -> Client
    AGENT_COMPLETED = "agent_completed"
    AGENT_STOPPED = "agent_stopped"
    AGENT_UPDATE = "agent_update"
    THREAD_HISTORY = "thread_history"
    ERROR = "error"
    
    # Tool and SubAgent events
    TOOL_STARTED = "tool_started"
    TOOL_COMPLETED = "tool_completed"
    SUBAGENT_STARTED = "subagent_started"
    SUBAGENT_COMPLETED = "subagent_completed"


class ConnectionInfo(BaseModel):
    """Strongly typed information about a WebSocket connection"""
    connection_id: str
    user_id: Optional[str] = Field(default=None)
    session_id: str
    connected_at: datetime
    last_activity: datetime
    ip_address: str
    user_agent: Optional[str] = Field(default=None)
    subscriptions: List[str] = Field(default_factory=list)
    active_thread_id: Optional[str] = Field(default=None)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def is_active(self, timeout_seconds: int = 300) -> bool:
        """Check if connection is still active"""
        age = (datetime.utcnow() - self.last_activity).total_seconds()
        return age < timeout_seconds


class WebSocketStats(BaseModel):
    """Comprehensive statistics for WebSocket connections"""
    total_connections: int
    active_connections: int
    messages_sent: int
    messages_received: int
    bytes_sent: int
    bytes_received: int
    errors_count: int
    average_latency_ms: float
    uptime_seconds: float
    connections_by_user: Dict[str, int] = Field(default_factory=dict)
    message_type_counts: Dict[WebSocketMessageType, int] = Field(default_factory=dict)
    peak_connections: int = Field(default=0)
    total_reconnections: int = Field(default=0)


class BroadcastResult(BaseModel):
    """Result of a broadcast operation with strong typing"""
    message_id: str
    message_type: WebSocketMessageType
    recipients_count: int
    successful_count: int
    failed_count: int
    failures: List[Dict[str, str]] = Field(default_factory=list)
    execution_time_ms: float


class MessageValidationResult(BaseModel):
    """Strongly typed result of message validation"""
    is_valid: bool
    message_type: Optional[WebSocketMessageType] = Field(default=None)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    parsed_payload: Optional[Dict[str, Any]] = Field(default=None)
    
    @validator('message_type', pre=True)
    def validate_message_type(cls, v: Any) -> Optional[WebSocketMessageType]:
        if isinstance(v, str):
            try:
                return WebSocketMessageType(v)
            except ValueError:
                return None
        return v


class EnhancedWebSocketMessage(BaseModel):
    """Enhanced base model with strong typing for all WebSocket messages"""
    type: WebSocketMessageType
    payload: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = Field(default=None)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    retry_count: int = Field(default=0)
    priority: int = Field(default=0, ge=0, le=10)
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }