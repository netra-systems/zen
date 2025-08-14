"""Unified WebSocket type definitions for the Netra platform.

This module consolidates all WebSocket-related type definitions into a single source of truth,
eliminating duplication and confusion from multiple overlapping type files.

Supersedes:
- websocket_types.py
- websocket_message_types.py  
- WebSocket.py
"""

from typing import Any, Dict, Optional, List, Union, Literal, TypedDict
from pydantic import BaseModel, Field, ConfigDict, validator
from datetime import datetime
from enum import Enum
import uuid

# Import existing domain types to avoid duplication
from app.schemas.Message import Message
from app.schemas.Tool import ToolStarted, ToolCompleted
from app.schemas.Run import RunComplete
from app.schemas.Agent import (
    AgentStarted, 
    AgentCompleted, 
    AgentErrorMessage, 
    SubAgentUpdate, 
    SubAgentStatus
)
from app.schemas.Request import RequestModel, StartAgentPayload as StartAgentPayloadPydantic


# ============================================================================
# ENUMS
# ============================================================================

class WebSocketMessageType(str, Enum):
    """All supported WebSocket message types."""
    # Client to server messages
    START_AGENT = "start_agent"
    USER_MESSAGE = "user_message"
    GET_THREAD_HISTORY = "get_thread_history"
    STOP_AGENT = "stop_agent"
    CREATE_THREAD = "create_thread"
    SWITCH_THREAD = "switch_thread"
    DELETE_THREAD = "delete_thread"
    RENAME_THREAD = "rename_thread"
    LIST_THREADS = "list_threads"
    PING = "ping"
    PONG = "pong"
    
    # Server to client messages
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_STOPPED = "agent_stopped"
    AGENT_ERROR = "agent_error"
    AGENT_UPDATE = "agent_update"
    AGENT_LOG = "agent_log"
    TOOL_STARTED = "tool_started"
    TOOL_COMPLETED = "tool_completed"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    SUBAGENT_STARTED = "subagent_started"
    SUBAGENT_COMPLETED = "subagent_completed"
    THREAD_HISTORY = "thread_history"
    THREAD_CREATED = "thread_created"
    THREAD_SWITCHED = "thread_switched"
    THREAD_DELETED = "thread_deleted"
    THREAD_RENAMED = "thread_renamed"
    THREAD_LIST = "thread_list"
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
    ERROR = "error"


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================================
# BASE MODELS
# ============================================================================

class BaseWebSocketPayload(BaseModel):
    """Base class for all WebSocket payloads."""
    model_config = ConfigDict(extra="forbid")
    
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))


class WebSocketError(BaseModel):
    """Standard error response."""
    message: str
    error_type: Optional[str] = None
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# CONNECTION MANAGEMENT
# ============================================================================

class ConnectionInfo(BaseModel):
    """WebSocket connection information."""
    connection_id: str
    client_id: str
    user_id: Optional[str] = None
    connected_at: datetime = Field(default_factory=datetime.utcnow)
    last_ping: Optional[datetime] = None
    state: WebSocketConnectionState = WebSocketConnectionState.CONNECTING
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConnectionEstablished(BaseWebSocketPayload):
    """Sent when connection is established."""
    connection_id: str
    session_id: str
    capabilities: List[str] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# THREAD MANAGEMENT
# ============================================================================

class ThreadMetadata(BaseModel):
    """Thread metadata with strong typing."""
    tags: List[str] = Field(default_factory=list)
    priority: Optional[int] = Field(default=None, ge=0, le=10)
    category: Optional[str] = None
    custom_fields: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)


class Thread(BaseModel):
    """Thread model."""
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    metadata: Optional[ThreadMetadata] = None
    message_count: int = 0
    is_active: bool = True


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


class RenameThreadPayload(BaseWebSocketPayload):
    """Payload for renaming a thread."""
    thread_id: str
    new_name: str


class ThreadCreated(BaseWebSocketPayload):
    """Response when thread is created."""
    thread: Thread


class ThreadSwitched(BaseWebSocketPayload):
    """Response when thread is switched."""
    thread: Thread
    previous_thread_id: Optional[str] = None


class ThreadDeleted(BaseWebSocketPayload):
    """Response when thread is deleted."""
    thread_id: str


class ThreadRenamed(BaseWebSocketPayload):
    """Response when thread is renamed."""
    thread_id: str
    old_name: str
    new_name: str


class ThreadList(BaseWebSocketPayload):
    """List of threads."""
    threads: List[Thread]
    total: int
    page: int = 1
    page_size: int = 50


# ============================================================================
# MESSAGE HANDLING
# ============================================================================

class UserMessagePayload(BaseWebSocketPayload):
    """User message payload."""
    text: str
    references: Optional[List[str]] = Field(default_factory=list)
    thread_id: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None


class AgentMessagePayload(BaseWebSocketPayload):
    """Agent message payload."""
    text: str
    agent_id: str
    thread_id: str
    metadata: Optional[Dict[str, Any]] = None


class MessageToUser(BaseModel):
    """Message formatted for user display."""
    sender: str  # "user", "agent", "system"
    content: str
    references: Optional[List[str]] = None
    raw_json: Optional[Dict] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# AGENT CONTROL
# ============================================================================

class StartAgentPayload(BaseWebSocketPayload):
    """Payload for starting an agent."""
    agent_id: str
    prompt: str
    thread_id: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class StopAgentPayload(BaseWebSocketPayload):
    """Payload for stopping an agent."""
    run_id: str
    reason: Optional[str] = None


class AgentUpdate(BaseWebSocketPayload):
    """Agent status update."""
    run_id: str
    agent_id: str
    status: str
    message: Optional[str] = None
    progress: Optional[float] = Field(default=None, ge=0, le=100)
    metadata: Optional[Dict[str, Any]] = None


class AgentLog(BaseWebSocketPayload):
    """Agent log message."""
    run_id: str
    agent_id: str
    level: Literal["debug", "info", "warning", "error", "critical"]
    message: str
    details: Optional[Dict[str, Any]] = None


# ============================================================================
# TOOL EXECUTION
# ============================================================================

class ToolCall(BaseWebSocketPayload):
    """Tool call notification."""
    tool_id: str
    tool_name: str
    parameters: Dict[str, Any]
    run_id: str
    agent_id: str


class ToolResult(BaseWebSocketPayload):
    """Tool execution result."""
    tool_id: str
    tool_name: str
    result: Union[Dict[str, Any], List[Any], str, int, float, bool, None]
    run_id: str
    agent_id: str
    success: bool = True
    error: Optional[str] = None
    duration_ms: Optional[float] = None


# ============================================================================
# STREAMING
# ============================================================================

class StreamChunk(BaseWebSocketPayload):
    """Streaming data chunk."""
    stream_id: str
    chunk_index: int
    content: str
    is_final: bool = False
    metadata: Optional[Dict[str, Any]] = None


class StreamComplete(BaseWebSocketPayload):
    """Stream completion notification."""
    stream_id: str
    total_chunks: int
    duration_ms: float
    metadata: Optional[Dict[str, Any]] = None


# ============================================================================
# MAIN MESSAGE WRAPPER
# ============================================================================

class WebSocketMessage(BaseModel):
    """Main WebSocket message wrapper."""
    type: WebSocketMessageType
    payload: Union[
        Dict[str, Any],  # For backward compatibility
        BaseWebSocketPayload,
        UserMessagePayload,
        AgentMessagePayload,
        StartAgentPayload,
        StopAgentPayload,
        CreateThreadPayload,
        SwitchThreadPayload,
        DeleteThreadPayload,
        RenameThreadPayload,
        ThreadCreated,
        ThreadSwitched,
        ThreadDeleted,
        ThreadRenamed,
        ThreadList,
        AgentUpdate,
        AgentLog,
        ToolCall,
        ToolResult,
        StreamChunk,
        StreamComplete,
        ConnectionEstablished,
        WebSocketError
    ]
    sender: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @validator("payload", pre=True)
    def validate_payload(cls, v: Union[dict, BaseModel], values: Dict[str, Any]) -> Union[dict, BaseModel]:
        """Ensure payload matches expected type."""
        if isinstance(v, dict):
            # For backward compatibility - convert dict to appropriate model
            msg_type = values.get("type")
            if msg_type:
                # Map message types to payload classes
                payload_map = {
                    WebSocketMessageType.USER_MESSAGE: UserMessagePayload,
                    WebSocketMessageType.START_AGENT: StartAgentPayload,
                    WebSocketMessageType.STOP_AGENT: StopAgentPayload,
                    WebSocketMessageType.CREATE_THREAD: CreateThreadPayload,
                    WebSocketMessageType.SWITCH_THREAD: SwitchThreadPayload,
                    WebSocketMessageType.DELETE_THREAD: DeleteThreadPayload,
                    WebSocketMessageType.RENAME_THREAD: RenameThreadPayload,
                    # Add more mappings as needed
                }
                
                payload_class = payload_map.get(msg_type)
                if payload_class:
                    try:
                        return payload_class(**v)
                    except Exception:
                        # Fallback to dict if conversion fails
                        pass
        return v


# ============================================================================
# TYPED DICT ALTERNATIVES (for gradual migration)
# ============================================================================

class WebSocketMessageDict(TypedDict, total=False):
    """TypedDict version for gradual migration."""
    type: str
    payload: Dict[str, Any]
    sender: Optional[str]
    timestamp: Optional[str]


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_error_message(
    error: str,
    error_type: Optional[str] = None,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    details: Optional[Dict[str, Any]] = None
) -> WebSocketMessage:
    """Create a standardized error message."""
    return WebSocketMessage(
        type=WebSocketMessageType.ERROR,
        payload=WebSocketError(
            message=error,
            error_type=error_type,
            severity=severity,
            details=details
        )
    )


def create_success_response(
    message_type: WebSocketMessageType,
    payload: BaseWebSocketPayload
) -> WebSocketMessage:
    """Create a standardized success response."""
    return WebSocketMessage(
        type=message_type,
        payload=payload
    )


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Enums
    "WebSocketMessageType",
    "WebSocketConnectionState",
    "ErrorSeverity",
    
    # Base models
    "BaseWebSocketPayload",
    "WebSocketError",
    "WebSocketMessage",
    
    # Connection
    "ConnectionInfo",
    "ConnectionEstablished",
    
    # Threads
    "Thread",
    "ThreadMetadata",
    "CreateThreadPayload",
    "SwitchThreadPayload",
    "DeleteThreadPayload",
    "RenameThreadPayload",
    "ThreadCreated",
    "ThreadSwitched",
    "ThreadDeleted",
    "ThreadRenamed",
    "ThreadList",
    
    # Messages
    "UserMessagePayload",
    "AgentMessagePayload",
    "MessageToUser",
    
    # Agent control
    "StartAgentPayload",
    "StopAgentPayload",
    "AgentUpdate",
    "AgentLog",
    
    # Tools
    "ToolCall",
    "ToolResult",
    
    # Streaming
    "StreamChunk",
    "StreamComplete",
    
    # TypedDict
    "WebSocketMessageDict",
    
    # Utilities
    "create_error_message",
    "create_success_response",
]