"""Strong type definitions for WebSocket Manager messages and communication."""

from typing import Any, Dict, Optional, List, Union, Literal
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from enum import Enum


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


class WebSocketMessage(BaseModel):
    """Base WebSocket message with common fields."""
    model_config = ConfigDict(extra="allow")
    
    type: WebSocketMessageType = Field(description="Message type")
    timestamp: Optional[float] = Field(default=None, description="Message timestamp")
    payload: Optional[Dict[str, Any]] = Field(default=None, description="Message payload")
    system: Optional[bool] = Field(default=False, description="Whether this is a system message")
    displayed_to_user: Optional[bool] = Field(default=None, description="Whether message should be displayed to user")


class ClientMessage(WebSocketMessage):
    """Base class for client-to-server messages."""
    pass


class ServerMessage(WebSocketMessage):
    """Base class for server-to-client messages."""
    pass


# Client-to-server message types
class StartAgentMessage(ClientMessage):
    """Message to start an agent."""
    type: Literal[WebSocketMessageType.START_AGENT] = WebSocketMessageType.START_AGENT
    payload: Dict[str, Any] = Field(description="Agent start parameters")


class UserMessage(ClientMessage):
    """User chat message."""
    type: Literal[WebSocketMessageType.USER_MESSAGE] = WebSocketMessageType.USER_MESSAGE
    payload: Dict[str, str] = Field(description="Must contain 'text' field with user message")


class StopAgentMessage(ClientMessage):
    """Message to stop agent processing."""
    type: Literal[WebSocketMessageType.STOP_AGENT] = WebSocketMessageType.STOP_AGENT
    payload: Optional[Dict[str, str]] = Field(default=None, description="Optional stop parameters")


class CreateThreadMessage(ClientMessage):
    """Message to create a new thread."""
    type: Literal[WebSocketMessageType.CREATE_THREAD] = WebSocketMessageType.CREATE_THREAD
    payload: Optional[Dict[str, str]] = Field(default=None, description="Thread creation parameters")


class SwitchThreadMessage(ClientMessage):
    """Message to switch to a different thread."""
    type: Literal[WebSocketMessageType.SWITCH_THREAD] = WebSocketMessageType.SWITCH_THREAD
    payload: Dict[str, str] = Field(description="Must contain 'thread_id' field")


class DeleteThreadMessage(ClientMessage):
    """Message to delete a thread."""
    type: Literal[WebSocketMessageType.DELETE_THREAD] = WebSocketMessageType.DELETE_THREAD
    payload: Dict[str, str] = Field(description="Must contain 'thread_id' field")


class ListThreadsMessage(ClientMessage):
    """Message to list available threads."""
    type: Literal[WebSocketMessageType.LIST_THREADS] = WebSocketMessageType.LIST_THREADS
    payload: Optional[Dict[str, Any]] = Field(default=None, description="Optional list parameters")


class GetThreadHistoryMessage(ClientMessage):
    """Message to get thread history."""
    type: Literal[WebSocketMessageType.GET_THREAD_HISTORY] = WebSocketMessageType.GET_THREAD_HISTORY
    payload: Dict[str, str] = Field(description="Must contain 'thread_id' field")


class PingMessage(ClientMessage):
    """Ping message for connection keepalive."""
    type: Literal[WebSocketMessageType.PING] = WebSocketMessageType.PING
    payload: Optional[Dict[str, Any]] = Field(default=None, description="Optional ping data")


class PongMessage(ClientMessage):
    """Pong response to server ping."""
    type: Literal[WebSocketMessageType.PONG] = WebSocketMessageType.PONG
    payload: Optional[Dict[str, Any]] = Field(default=None, description="Optional pong data")


# Server-to-client message types
class AgentStartedMessage(ServerMessage):
    """Message indicating agent has started."""
    type: Literal[WebSocketMessageType.AGENT_STARTED] = WebSocketMessageType.AGENT_STARTED
    payload: Dict[str, Any] = Field(description="Agent start confirmation data")


class AgentCompletedMessage(ServerMessage):
    """Message indicating agent has completed."""
    type: Literal[WebSocketMessageType.AGENT_COMPLETED] = WebSocketMessageType.AGENT_COMPLETED
    payload: Dict[str, Any] = Field(description="Agent completion data and results")


class AgentStoppedMessage(ServerMessage):
    """Message indicating agent was stopped."""
    type: Literal[WebSocketMessageType.AGENT_STOPPED] = WebSocketMessageType.AGENT_STOPPED
    payload: Dict[str, Any] = Field(description="Agent stop confirmation")


class AgentErrorMessage(ServerMessage):
    """Message indicating agent error."""
    type: Literal[WebSocketMessageType.AGENT_ERROR] = WebSocketMessageType.AGENT_ERROR
    payload: Dict[str, Any] = Field(description="Error details")


class AgentUpdateMessage(ServerMessage):
    """Real-time agent status update."""
    type: Literal[WebSocketMessageType.AGENT_UPDATE] = WebSocketMessageType.AGENT_UPDATE
    payload: Dict[str, Any] = Field(description="Agent status and progress data")


class AgentLogMessage(ServerMessage):
    """Agent log message for monitoring."""
    type: Literal[WebSocketMessageType.AGENT_LOG] = WebSocketMessageType.AGENT_LOG
    payload: Dict[str, Any] = Field(description="Log data with level, message, sub_agent_name")


class ToolStartedMessage(ServerMessage):
    """Message indicating tool execution started."""
    type: Literal[WebSocketMessageType.TOOL_STARTED] = WebSocketMessageType.TOOL_STARTED
    payload: Dict[str, Any] = Field(description="Tool execution start data")


class ToolCompletedMessage(ServerMessage):
    """Message indicating tool execution completed."""
    type: Literal[WebSocketMessageType.TOOL_COMPLETED] = WebSocketMessageType.TOOL_COMPLETED
    payload: Dict[str, Any] = Field(description="Tool execution completion data")


class ToolCallMessage(ServerMessage):
    """Message indicating tool is being called."""
    type: Literal[WebSocketMessageType.TOOL_CALL] = WebSocketMessageType.TOOL_CALL
    payload: Dict[str, Any] = Field(description="Tool call data with name, args, sub_agent_name")


class ToolResultMessage(ServerMessage):
    """Message with tool execution result."""
    type: Literal[WebSocketMessageType.TOOL_RESULT] = WebSocketMessageType.TOOL_RESULT
    payload: Dict[str, Any] = Field(description="Tool result data with name, result, sub_agent_name")


class SubAgentStartedMessage(ServerMessage):
    """Message indicating sub-agent started."""
    type: Literal[WebSocketMessageType.SUBAGENT_STARTED] = WebSocketMessageType.SUBAGENT_STARTED
    payload: Dict[str, Any] = Field(description="Sub-agent start data")


class SubAgentCompletedMessage(ServerMessage):
    """Message indicating sub-agent completed."""
    type: Literal[WebSocketMessageType.SUBAGENT_COMPLETED] = WebSocketMessageType.SUBAGENT_COMPLETED
    payload: Dict[str, Any] = Field(description="Sub-agent completion data")


class ThreadHistoryMessage(ServerMessage):
    """Message containing thread history."""
    type: Literal[WebSocketMessageType.THREAD_HISTORY] = WebSocketMessageType.THREAD_HISTORY
    payload: Dict[str, Any] = Field(description="Thread history data")


class ErrorMessage(ServerMessage):
    """Error message."""
    type: Literal[WebSocketMessageType.ERROR] = WebSocketMessageType.ERROR
    payload: Dict[str, Any] = Field(description="Error details with error, code, sub_agent_name")


class ConnectionEstablishedMessage(ServerMessage):
    """Message confirming connection establishment."""
    type: Literal[WebSocketMessageType.CONNECTION_ESTABLISHED] = WebSocketMessageType.CONNECTION_ESTABLISHED
    payload: Dict[str, Any] = Field(description="Connection details")


class StreamChunkMessage(ServerMessage):
    """Streaming response chunk."""
    type: Literal[WebSocketMessageType.STREAM_CHUNK] = WebSocketMessageType.STREAM_CHUNK
    payload: Dict[str, Any] = Field(description="Stream chunk data")


class StreamCompleteMessage(ServerMessage):
    """Stream completion message."""
    type: Literal[WebSocketMessageType.STREAM_COMPLETE] = WebSocketMessageType.STREAM_COMPLETE
    payload: Dict[str, Any] = Field(description="Stream completion data")


# Union types for message validation
ClientMessageUnion = Union[
    StartAgentMessage,
    UserMessage,
    StopAgentMessage,
    CreateThreadMessage,
    SwitchThreadMessage,
    DeleteThreadMessage,
    ListThreadsMessage,
    GetThreadHistoryMessage,
    PingMessage,
    PongMessage
]

ServerMessageUnion = Union[
    AgentStartedMessage,
    AgentCompletedMessage,
    AgentStoppedMessage,
    AgentErrorMessage,
    AgentUpdateMessage,
    AgentLogMessage,
    ToolStartedMessage,
    ToolCompletedMessage,
    ToolCallMessage,
    ToolResultMessage,
    SubAgentStartedMessage,
    SubAgentCompletedMessage,
    ThreadHistoryMessage,
    ErrorMessage,
    ConnectionEstablishedMessage,
    StreamChunkMessage,
    StreamCompleteMessage
]

WebSocketMessageUnion = Union[ClientMessageUnion, ServerMessageUnion]


class ConnectionInfo(BaseModel):
    """Typed connection information."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    user_id: str = Field(description="User ID for this connection")
    connection_id: str = Field(description="Unique connection identifier")
    connected_at: datetime = Field(description="Connection timestamp")
    last_ping: datetime = Field(description="Last ping timestamp")
    last_pong: Optional[datetime] = Field(default=None, description="Last pong timestamp")
    message_count: int = Field(default=0, description="Number of messages sent")
    error_count: int = Field(default=0, description="Number of errors encountered")
    last_message_time: datetime = Field(description="Time of last message")
    rate_limit_count: int = Field(default=0, description="Current rate limit counter")
    rate_limit_window_start: datetime = Field(description="Rate limit window start time")


class RateLimitInfo(BaseModel):
    """Rate limiting information."""
    max_requests: int = Field(description="Maximum requests allowed")
    window_seconds: int = Field(description="Time window in seconds")
    current_count: int = Field(description="Current request count")
    window_start: datetime = Field(description="Current window start time")
    is_limited: bool = Field(description="Whether currently rate limited")


class WebSocketStats(BaseModel):
    """WebSocket manager statistics."""
    total_connections: int = Field(default=0, description="Total connections made")
    active_connections: int = Field(default=0, description="Currently active connections")
    active_users: int = Field(default=0, description="Number of users with active connections")
    total_messages_sent: int = Field(default=0, description="Total messages sent")
    total_messages_received: int = Field(default=0, description="Total messages received")
    total_errors: int = Field(default=0, description="Total errors encountered")
    connection_failures: int = Field(default=0, description="Connection establishment failures")
    rate_limited_requests: int = Field(default=0, description="Rate limited requests")
    rate_limit_settings: RateLimitInfo = Field(description="Rate limit configuration")
    connections_by_user: Dict[str, int] = Field(default_factory=dict, description="Connections per user")


class BroadcastResult(BaseModel):
    """Result of broadcast operation."""
    successful: int = Field(description="Number of successful sends")
    failed: int = Field(description="Number of failed sends")
    total_connections: int = Field(description="Total connections attempted")
    message_type: str = Field(description="Type of message broadcast")


class WebSocketValidationError(BaseModel):
    """WebSocket message validation error."""
    error_type: Literal["format_error", "type_error", "validation_error", "security_error"] = Field(description="Error type")
    message: str = Field(description="Error message")
    field: Optional[str] = Field(default=None, description="Field that caused error")
    received_data: Optional[Dict[str, Any]] = Field(default=None, description="Data that failed validation")