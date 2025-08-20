"""
WebSocket Models: Single Source of Truth for WebSocket Message Types and Payloads

This module contains all WebSocket-related models and payloads used across 
the Netra platform, ensuring consistency and preventing duplication.

CRITICAL ARCHITECTURAL COMPLIANCE:
- All WebSocket model definitions MUST be imported from this module
- NO duplicate WebSocket model definitions allowed anywhere else in codebase
- This file maintains strong typing and single sources of truth
- Maximum file size: 300 lines (currently under limit)

Usage:
    from app.schemas.websocket_models import WebSocketMessage, BaseWebSocketPayload
"""

from typing import Dict, List, Optional, Union, Any, TypedDict, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict
import uuid

# Import enums and other dependencies from the dedicated modules
from app.schemas.core_enums import WebSocketMessageType, MessageType, AgentStatus
from app.schemas.core_models import ThreadMetadata, Message
from app.schemas.agent_models import AgentResult


class BaseWebSocketPayload(BaseModel):
    """Base class for all WebSocket payloads."""
    timestamp: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    
    model_config = ConfigDict(
        extra="forbid"
    )


class StartAgentPayload(BaseWebSocketPayload):
    """Payload for starting an agent."""
    query: str
    user_id: str
    thread_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


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


class UserMessagePayload(BaseWebSocketPayload):
    """User message WebSocket payload."""
    content: str
    thread_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AgentUpdatePayload(BaseWebSocketPayload):
    """Agent update WebSocket payload."""
    run_id: str
    agent_id: str
    status: AgentStatus
    message: Optional[str] = None
    progress: Optional[float] = Field(default=None, ge=0, le=100)
    current_task: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


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
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


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


class WebSocketError(BaseModel):
    """Unified WebSocket error model."""
    message: str
    error_type: Optional[str] = None
    code: Optional[str] = None
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    details: Optional[Dict[str, Any]] = None
    trace_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict()


class WebSocketMessage(BaseModel):
    """Unified WebSocket message - single source of truth."""
    type: WebSocketMessageType
    payload: Union[Dict[str, Any], BaseWebSocketPayload, UserMessagePayload, AgentUpdatePayload]
    sender: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(
        use_enum_values=True
    )


class WebSocketMessageIn(TypedDict):
    """Incoming WebSocket message structure"""
    type: str  # MessageTypeLiteral would create circular import
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


# Backward compatibility aliases
AgentResponse = AgentResponseData
MessageToUser = UserMessagePayload
AnalysisRequest = StartAgentPayload
UserMessage = UserMessagePayload
AgentMessage = AgentUpdatePayload
StopAgent = StopAgentPayload


class AgentCompletedPayload(TypedDict):
    """Payload for agent_completed message"""
    response: AgentResponseData
    thread_id: Optional[str]
    run_id: Optional[str]


class AgentStoppedPayload(TypedDict):
    """Payload for agent_stopped message"""
    status: Literal["stopped"]


class ServerMessage(BaseModel):
    """Server-to-client WebSocket message."""
    type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    server_id: Optional[str] = None
    correlation_id: Optional[str] = None
    
    model_config = ConfigDict(
        extra="allow"
    )


class RateLimitInfo(BaseModel):
    """Rate limit configuration info."""
    max_connections_per_user: int = Field(default=5)
    max_messages_per_minute: int = Field(default=60)
    max_message_size: int = Field(default=10240)
    window_seconds: int = Field(default=60)


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
    rate_limit_settings: RateLimitInfo = Field(default_factory=RateLimitInfo)


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


# Export all WebSocket models
__all__ = [
    "BaseWebSocketPayload",
    "StartAgentPayload",
    "CreateThreadPayload", 
    "SwitchThreadPayload",
    "DeleteThreadPayload",
    "UserMessagePayload",
    "AgentUpdatePayload",
    "StopAgentPayload",
    "AgentUpdate",
    "AgentLog",
    "ToolCall",
    "ToolResult",
    "StreamChunk",
    "StreamComplete",
    "StreamEvent",
    "AgentStarted",
    "SubAgentUpdate", 
    "AgentCompleted",
    "WebSocketError",
    "WebSocketMessage",
    "WebSocketMessageIn",
    "MessageData",
    "ThreadHistoryResponse",
    "AgentResponseData",
    "AgentResponse",
    "MessageToUser",
    "AnalysisRequest", 
    "UserMessage",
    "AgentMessage",
    "StopAgent",
    "AgentCompletedPayload",
    "AgentStoppedPayload",
    "ServerMessage",
    "RateLimitInfo",
    "WebSocketStats",
    "BroadcastResult",
    "WebSocketValidationError"
]