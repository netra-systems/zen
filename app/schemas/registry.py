"""
Type Registry: Single Source of Truth for All Python Types

This module serves as the central registry for all type definitions in the Netra platform,
eliminating duplication and ensuring consistency across the entire codebase.

CRITICAL ARCHITECTURAL COMPLIANCE:
- All type definitions MUST be imported from this registry
- NO duplicate type definitions allowed anywhere else in codebase
- This file maintains strong typing and single sources of truth
- Maximum file size: 300 lines (will be split if needed)

Usage:
    from app.schemas.registry import User, Message, AgentState, WebSocketMessage
"""

from typing import Dict, List, Optional, Union, Any, Literal, TypedDict
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, EmailStr, ConfigDict
import uuid

# ============================================================================
# CORE DOMAIN ENUMS
# ============================================================================

class MessageType(str, Enum):
    """Unified message type enum."""
    USER = "user"
    ASSISTANT = "assistant" 
    AGENT = "agent"
    SYSTEM = "system"
    ERROR = "error"
    TOOL = "tool"


class AgentStatus(str, Enum):
    """Unified agent status enum."""
    IDLE = "idle"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    THINKING = "thinking"
    PLANNING = "planning"
    EXECUTING = "executing"
    RUNNING = "running"
    WAITING = "waiting"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ERROR = "error"
    CANCELLED = "cancelled"
    SHUTDOWN = "shutdown"


class WebSocketMessageType(str, Enum):
    """Unified WebSocket message types."""
    # Client to server
    START_AGENT = "start_agent"
    USER_MESSAGE = "user_message"
    CHAT_MESSAGE = "chat_message"  # Alternative message type for compatibility
    STOP_AGENT = "stop_agent"
    CREATE_THREAD = "create_thread"
    SWITCH_THREAD = "switch_thread"
    DELETE_THREAD = "delete_thread"
    RENAME_THREAD = "rename_thread"
    LIST_THREADS = "list_threads"
    GET_THREAD_HISTORY = "get_thread_history"
    PING = "ping"
    PONG = "pong"
    
    # Server to client
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_STOPPED = "agent_stopped"
    AGENT_ERROR = "agent_error"
    AGENT_UPDATE = "agent_update"
    AGENT_LOG = "agent_log"
    AGENT_THINKING = "agent_thinking"
    AGENT_FALLBACK = "agent_fallback"
    TOOL_STARTED = "tool_started"
    TOOL_COMPLETED = "tool_completed"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    TOOL_EXECUTING = "tool_executing"
    SUBAGENT_STARTED = "subagent_started" 
    SUBAGENT_COMPLETED = "subagent_completed"
    SUB_AGENT_UPDATE = "sub_agent_update"
    THREAD_HISTORY = "thread_history"
    THREAD_CREATED = "thread_created"
    THREAD_UPDATED = "thread_updated"
    THREAD_DELETED = "thread_deleted"
    THREAD_LOADED = "thread_loaded"
    THREAD_RENAMED = "thread_renamed"
    STEP_CREATED = "step_created"
    PARTIAL_RESULT = "partial_result"
    FINAL_REPORT = "final_report"
    ERROR = "error"
    CONNECTION_ESTABLISHED = "connection_established"
    STREAM_CHUNK = "stream_chunk"
    STREAM_COMPLETE = "stream_complete"


class WebSocketConnectionState(str, Enum):
    """WebSocket connection states."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"


# Message type literals for WebSocket
MessageTypeLiteral = Literal[
    "start_agent",
    "user_message",
    "chat_message",
    "get_thread_history",
    "stop_agent",
    "create_thread",
    "switch_thread",
    "delete_thread",
    "rename_thread",
    "list_threads",
    "ping",
    "pong",
    "agent_started",
    "agent_completed",
    "agent_stopped",
    "agent_error",
    "agent_update",
    "agent_log",
    "agent_thinking",
    "agent_fallback",
    "tool_started",
    "tool_completed",
    "tool_call",
    "tool_result",
    "tool_executing",
    "subagent_started",
    "subagent_completed",
    "sub_agent_update",
    "thread_history",
    "thread_created",
    "thread_updated", 
    "thread_deleted",
    "thread_loaded",
    "thread_renamed",
    "step_created",
    "partial_result",
    "final_report",
    "error",
    "connection_established",
    "stream_chunk",
    "stream_complete"
]


# ============================================================================
# CORE DOMAIN MODELS
# ============================================================================

class UserBase(BaseModel):
    """Base user model."""
    email: EmailStr
    full_name: Optional[str] = None
    picture: Optional[str] = None


class UserCreate(UserBase):
    """User creation model."""
    password: str


class UserCreateOAuth(UserBase):
    """OAuth user creation model."""
    pass


class User(BaseModel):
    """Unified User model - single source of truth."""
    id: str
    email: EmailStr
    full_name: Optional[str] = None
    picture: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False
    hashed_password: Optional[str] = None
    access_token: Optional[str] = None
    token_type: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, extra="allow")


class MessageMetadata(BaseModel):
    """Unified message metadata."""
    model: Optional[str] = None
    tokens_used: Optional[int] = None
    processing_time: Optional[float] = None  
    agent_name: Optional[str] = None
    run_id: Optional[str] = None
    step_id: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    custom_fields: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)


class Message(BaseModel):
    """Unified Message model - single source of truth."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    content: str
    type: MessageType
    thread_id: Optional[str] = None
    sub_agent_name: Optional[str] = None
    tool_info: Optional[Dict[str, Any]] = None
    raw_data: Optional[Dict[str, Any]] = None
    displayed_to_user: bool = True
    metadata: Optional[MessageMetadata] = None
    references: Optional[List[str]] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )


class ThreadMetadata(BaseModel):
    """Unified thread metadata."""
    tags: List[str] = Field(default_factory=list)
    priority: Optional[int] = Field(default=None, ge=0, le=10)
    category: Optional[str] = None
    user_id: Optional[str] = None
    custom_fields: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)


class Thread(BaseModel):
    """Unified Thread model - single source of truth."""
    id: str
    name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    metadata: Optional[ThreadMetadata] = None
    message_count: int = 0
    is_active: bool = True
    last_message: Optional[Message] = None
    participants: Optional[List[str]] = None
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )


# ============================================================================
# AGENT MODELS - CONSOLIDATED
# ============================================================================

class ToolResultData(BaseModel):
    """Unified tool result data."""
    tool_name: str
    status: str
    output: Optional[Union[str, dict, list]] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None
    metadata: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)


class AgentMetadata(BaseModel):
    """Unified agent metadata."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    execution_context: Dict[str, str] = Field(default_factory=dict)
    custom_fields: Dict[str, str] = Field(default_factory=dict)
    priority: Optional[int] = Field(default=None, ge=0, le=10)
    retry_count: int = 0
    parent_agent_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class AgentResult(BaseModel):
    """Unified agent result model."""
    success: bool
    output: Optional[Union[str, dict, list]] = None
    error: Optional[str] = None
    metrics: Dict[str, Union[int, float]] = Field(default_factory=dict)
    artifacts: List[str] = Field(default_factory=list)
    execution_time_ms: Optional[float] = None


class DeepAgentState(BaseModel):
    """Unified Deep Agent State - single source of truth (replaces old AgentState)."""
    user_request: str
    chat_thread_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # Results from different agent types
    triage_result: Optional[Any] = None
    data_result: Optional[Any] = None
    optimizations_result: Optional[Any] = None
    action_plan_result: Optional[Any] = None
    report_result: Optional[Any] = None
    synthetic_data_result: Optional[Any] = None
    supply_research_result: Optional[Any] = None
    corpus_admin_result: Optional[Any] = None
    
    # Execution tracking
    final_report: Optional[str] = None
    step_count: int = 0
    metadata: AgentMetadata = Field(default_factory=AgentMetadata)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        return self.model_dump(exclude_none=True)
    
    def copy_with_updates(self, **updates: Any) -> 'DeepAgentState':
        """Create a new instance with updated fields (immutable pattern)."""
        current_data = self.model_dump()
        current_data.update(updates)
        return DeepAgentState(**current_data)
    
    def increment_step_count(self) -> 'DeepAgentState':
        """Create a new instance with incremented step count."""
        return self.copy_with_updates(step_count=self.step_count + 1)
    
    def add_metadata(self, key: str, value: str) -> 'DeepAgentState':
        """Create a new instance with additional metadata."""
        updated_custom = self.metadata.custom_fields.copy()
        updated_custom[key] = value
        new_metadata = self.metadata.model_copy(
            update={'custom_fields': updated_custom, 'last_updated': datetime.utcnow()}
        )
        return self.copy_with_updates(metadata=new_metadata)
    
    def clear_sensitive_data(self) -> 'DeepAgentState':
        """Create a new instance with sensitive data cleared."""
        return self.copy_with_updates(
            triage_result=None,
            data_result=None,
            optimizations_result=None,
            action_plan_result=None,
            report_result=None,
            synthetic_data_result=None,
            supply_research_result=None,
            final_report=None,
            metadata=AgentMetadata()
        )
    
    def merge_from(self, other_state: 'DeepAgentState') -> 'DeepAgentState':
        """Create new state with data merged from another state (immutable)."""
        if not isinstance(other_state, DeepAgentState):
            raise TypeError("other_state must be a DeepAgentState instance")
        
        merged_custom = self.metadata.custom_fields.copy()
        merged_context = self.metadata.execution_context.copy()
        
        if other_state.metadata:
            merged_custom.update(other_state.metadata.custom_fields)
            merged_context.update(other_state.metadata.execution_context)
        
        merged_metadata = AgentMetadata(
            execution_context=merged_context,
            custom_fields=merged_custom
        )
        
        return self.copy_with_updates(
            triage_result=other_state.triage_result or self.triage_result,
            data_result=other_state.data_result or self.data_result,
            optimizations_result=other_state.optimizations_result or self.optimizations_result,
            action_plan_result=other_state.action_plan_result or self.action_plan_result,
            report_result=other_state.report_result or self.report_result,
            synthetic_data_result=other_state.synthetic_data_result or self.synthetic_data_result,
            supply_research_result=other_state.supply_research_result or self.supply_research_result,
            final_report=other_state.final_report or self.final_report,
            step_count=max(self.step_count, other_state.step_count),
            metadata=merged_metadata
        )


# Backward compatibility alias  
AgentState = DeepAgentState


# ============================================================================
# WEBSOCKET MODELS - CONSOLIDATED  
# ============================================================================

class BaseWebSocketPayload(BaseModel):
    """Base class for all WebSocket payloads."""
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    
    model_config = ConfigDict(
        extra="forbid",
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )


class StartAgentPayload(BaseWebSocketPayload):
    """Payload for starting an agent."""
    agent_id: str
    prompt: str
    thread_id: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None


class CreateThreadPayload(BaseWebSocketPayload):
    """Payload for creating a thread."""
    name: Optional[str] = None
    metadata: Optional[ThreadMetadata] = None


class SwitchThreadPayload(BaseWebSocketPayload):
    """Payload for switching threads."""
    thread_id: str


class DeleteThreadPayload(BaseWebSocketPayload):
    """Payload for deleting a thread."""
    thread_id: str


class WebSocketMessageIn(TypedDict):
    """Incoming WebSocket message structure"""
    type: MessageTypeLiteral
    payload: Optional[Dict[str, Any]]


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
    data: Optional[Union[str, Dict[str, Any], List[Any]]] = None
    metrics: Dict[str, Union[int, float]] = Field(default_factory=dict)


# Backward compatibility alias
AgentResponse = AgentResponseData


class AgentCompletedPayload(TypedDict):
    """Payload for agent_completed message"""
    response: AgentResponseData
    thread_id: Optional[str]
    run_id: Optional[str]


class AgentStoppedPayload(TypedDict):
    """Payload for agent_stopped message"""
    status: Literal["stopped"]


class WebSocketError(BaseModel):
    """Unified WebSocket error model."""
    message: str
    error_type: Optional[str] = None
    code: Optional[str] = None
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    details: Optional[Dict[str, Any]] = None
    trace_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )


class UserMessagePayload(BaseWebSocketPayload):
    """User message WebSocket payload."""
    text: str
    references: Optional[List[str]] = Field(default_factory=list)
    thread_id: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None


class AgentUpdatePayload(BaseWebSocketPayload):
    """Agent update WebSocket payload."""
    run_id: str
    agent_id: str
    status: AgentStatus
    message: Optional[str] = None
    progress: Optional[float] = Field(default=None, ge=0, le=100)
    current_task: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class WebSocketMessage(BaseModel):
    """Unified WebSocket message - single source of truth."""
    type: WebSocketMessageType
    payload: Union[Dict[str, Any], BaseWebSocketPayload, UserMessagePayload, AgentUpdatePayload]
    sender: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )


# Additional WebSocket message types for backward compatibility
class MessageToUser(BaseModel):
    """Message to user payload."""
    content: str
    message_type: MessageType = MessageType.ASSISTANT
    metadata: Optional[Dict[str, Any]] = None


class AnalysisRequest(BaseModel):
    """Analysis request payload."""
    query: str
    context: Optional[Dict[str, Any]] = None
    options: Optional[Dict[str, Any]] = None


class UserMessage(BaseModel):
    """User message payload."""
    content: str
    thread_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AgentMessage(BaseModel):
    """Agent message payload."""
    content: str
    agent_id: str
    status: AgentStatus
    metadata: Optional[Dict[str, Any]] = None


class StopAgent(BaseModel):
    """Stop agent payload."""
    agent_id: str
    reason: Optional[str] = None


class StopAgentPayload(BaseWebSocketPayload):
    """Stop agent WebSocket payload."""
    agent_id: str
    reason: Optional[str] = None


class AgentUpdate(BaseWebSocketPayload):
    """Agent update message payload."""
    agent_id: str
    status: str
    message: Optional[str] = None
    progress: Optional[float] = None


class AgentLog(BaseWebSocketPayload):
    """Agent log message payload."""
    agent_id: str
    level: str
    message: str
    metadata: Optional[Dict[str, Any]] = None


class ToolCall(BaseWebSocketPayload):
    """Tool call message payload."""
    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    call_id: str


class ToolResult(BaseWebSocketPayload):
    """Tool result message payload."""
    call_id: str
    result: Optional[Union[str, Dict[str, Any]]] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None


class StreamChunk(BaseWebSocketPayload):
    """Stream chunk message payload."""
    chunk_id: str
    content: str
    is_final: bool = False


class StreamComplete(BaseWebSocketPayload):
    """Stream complete message payload."""
    stream_id: str
    total_chunks: int
    metadata: Optional[Dict[str, Any]] = None


class StreamEvent(BaseModel):
    """Stream event payload."""
    event_type: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentStarted(BaseWebSocketPayload):
    """Agent started WebSocket payload."""
    agent_id: str
    agent_type: str
    run_id: str
    status: AgentStatus = AgentStatus.ACTIVE
    message: Optional[str] = None


class SubAgentUpdate(BaseWebSocketPayload):
    """Sub-agent update WebSocket payload."""
    agent_id: str
    sub_agent_name: str
    status: AgentStatus
    message: Optional[str] = None
    progress: Optional[float] = Field(default=None, ge=0, le=100)
    current_task: Optional[str] = None


class AgentCompleted(BaseWebSocketPayload):
    """Agent completed WebSocket payload."""
    agent_id: str
    run_id: str
    result: AgentResult
    status: AgentStatus = AgentStatus.COMPLETED
    message: Optional[str] = None


# ============================================================================
# AUDIT MODELS - CORPUS OPERATIONS
# ============================================================================

class CorpusAuditAction(str, Enum):
    """Unified corpus audit action types."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SEARCH = "search"
    GENERATE = "generate"
    UPLOAD = "upload"
    VALIDATE = "validate"
    EXPORT = "export"
    IMPORT = "import"
    BACKUP = "backup"
    RESTORE = "restore"


class CorpusAuditStatus(str, Enum):
    """Unified corpus audit status types."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    IN_PROGRESS = "in_progress"
    CANCELLED = "cancelled"


class CorpusAuditMetadata(BaseModel):
    """Unified corpus audit metadata."""
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    configuration: Dict[str, Any] = Field(default_factory=dict)
    performance_metrics: Dict[str, float] = Field(default_factory=dict)
    error_details: Optional[Dict[str, Any]] = None
    compliance_flags: List[str] = Field(default_factory=list)


class CorpusAuditRecord(BaseModel):
    """Unified corpus audit record - single source of truth."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    action: CorpusAuditAction
    status: CorpusAuditStatus
    corpus_id: Optional[str] = None
    resource_type: str
    resource_id: Optional[str] = None
    operation_duration_ms: Optional[float] = None
    result_data: Optional[Dict[str, Any]] = None
    metadata: CorpusAuditMetadata = Field(default_factory=CorpusAuditMetadata)
    
    model_config = ConfigDict(from_attributes=True)


class CorpusAuditSearchFilter(BaseModel):
    """Unified corpus audit search filter."""
    user_id: Optional[str] = None
    action: Optional[CorpusAuditAction] = None
    status: Optional[CorpusAuditStatus] = None
    corpus_id: Optional[str] = None
    resource_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class CorpusAuditReport(BaseModel):
    """Unified corpus audit report."""
    total_records: int
    records: List[CorpusAuditRecord]
    summary: Dict[str, int] = Field(default_factory=dict)
    time_range: Dict[str, Optional[datetime]] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# EXPORTS - EXPLICIT TYPE REGISTRY
# ============================================================================

# Core domain types
__all__ = [
    # Enums
    "MessageType", "AgentStatus", "WebSocketMessageType", "WebSocketConnectionState",
    "CorpusAuditAction", "CorpusAuditStatus",
    
    # Core models  
    "UserBase", "UserCreate", "UserCreateOAuth", "User", "Message", "Thread", "MessageMetadata", "ThreadMetadata",
    
    # Agent models
    "DeepAgentState", "AgentState", "AgentResult", "AgentMetadata", "ToolResultData",
    
    # WebSocket models
    "WebSocketMessage", "WebSocketError", "BaseWebSocketPayload", 
    "UserMessagePayload", "AgentUpdatePayload", "MessageToUser", "AnalysisRequest",
    "UserMessage", "AgentMessage", "StopAgent", "StopAgentPayload", "StreamEvent",
    "AgentStarted", "SubAgentUpdate", "AgentCompleted", "StartAgentPayload",
    "WebSocketMessageIn", "MessageTypeLiteral", "CreateThreadPayload", 
    "SwitchThreadPayload", "DeleteThreadPayload", "MessageData", "ThreadHistoryResponse",
    "AgentResponseData", "AgentResponse", "AgentCompletedPayload", "AgentStoppedPayload",
    "AgentUpdate", "AgentLog", "ToolCall", "ToolResult", "StreamChunk", "StreamComplete",
    
    # Audit models
    "CorpusAuditRecord", "CorpusAuditMetadata", "CorpusAuditSearchFilter", 
    "CorpusAuditReport",
]


# Type registry for programmatic access
TYPE_REGISTRY = {
    "UserBase": UserBase,
    "UserCreate": UserCreate,
    "UserCreateOAuth": UserCreateOAuth,
    "User": User,
    "Message": Message, 
    "Thread": Thread,
    "DeepAgentState": DeepAgentState,
    "AgentState": AgentState,  # Backward compatibility
    "AgentResult": AgentResult,
    "WebSocketMessage": WebSocketMessage,
    "WebSocketError": WebSocketError,
    "MessageType": MessageType,
    "AgentStatus": AgentStatus,
    "WebSocketMessageType": WebSocketMessageType,
    "WebSocketConnectionState": WebSocketConnectionState,
    "WebSocketMessageIn": WebSocketMessageIn,
    "MessageTypeLiteral": MessageTypeLiteral,
    "CreateThreadPayload": CreateThreadPayload,
    "SwitchThreadPayload": SwitchThreadPayload,
    "DeleteThreadPayload": DeleteThreadPayload,
    "MessageData": MessageData,
    "ThreadHistoryResponse": ThreadHistoryResponse,
    "AgentResponseData": AgentResponseData,
    "AgentResponse": AgentResponse,
    "AgentCompletedPayload": AgentCompletedPayload,
    "AgentStoppedPayload": AgentStoppedPayload,
    "CorpusAuditRecord": CorpusAuditRecord,
    "CorpusAuditMetadata": CorpusAuditMetadata,
    "CorpusAuditSearchFilter": CorpusAuditSearchFilter,
    "CorpusAuditReport": CorpusAuditReport,
    "CorpusAuditAction": CorpusAuditAction,
    "CorpusAuditStatus": CorpusAuditStatus,
    "StopAgentPayload": StopAgentPayload,
    "AgentUpdate": AgentUpdate,
    "AgentLog": AgentLog,
    "ToolCall": ToolCall,
    "ToolResult": ToolResult,
    "StreamChunk": StreamChunk,
    "StreamComplete": StreamComplete,
}


def get_type(type_name: str) -> Optional[type]:
    """Get a type from the registry by name."""
    return TYPE_REGISTRY.get(type_name)


def list_registered_types() -> List[str]:
    """List all registered type names."""
    return list(TYPE_REGISTRY.keys())