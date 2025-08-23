"""Strong type definitions for WebSocket Manager messages and communication."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

# Import WebSocketMessage and WebSocketMessageType from single source of truth
from netra_backend.app.schemas.registry import WebSocketMessage, WebSocketMessageType

# WebSocketMessageType is imported from registry.py - using that as single source


class WebSocketConnectionState(str, Enum):
    """WebSocket connection states."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


# WebSocketMessage is imported from app.schemas.registry (single source of truth)

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


# Import server-to-client message types from dedicated module
from netra_backend.app.schemas.websocket_server_messages import (
    AgentCompletedMessage,
    AgentErrorMessage,
    AgentLogMessage,
    AgentStartedMessage,
    AgentStoppedMessage,
    AgentThinkingMessage,
    AgentUpdateMessage,
    ConnectionEstablishedMessage,
    ErrorMessage,
    FinalReportMessage,
    PartialResultMessage,
    ServerMessageUnion,
    StepCreatedMessage,
    StreamChunkMessage,
    StreamCompleteMessage,
    SubAgentCompletedMessage,
    SubAgentStartedMessage,
    ThreadCreatedMessage,
    ThreadDeletedMessage,
    ThreadHistoryMessage,
    ThreadLoadedMessage,
    ThreadRenamedMessage,
    ThreadUpdatedMessage,
    ToolCallMessage,
    ToolCompletedMessage,
    ToolExecutingMessage,
    ToolResultMessage,
    ToolStartedMessage,
)

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

# ServerMessageUnion is imported from websocket_server_messages module

WebSocketMessageUnion = Union[ClientMessageUnion, ServerMessageUnion]


class ConnectionInfo(BaseModel):
    """Typed connection information."""
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )
    
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
    
    model_config = ConfigDict(
    )


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