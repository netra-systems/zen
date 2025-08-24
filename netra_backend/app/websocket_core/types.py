"""
WebSocket Types and Data Models

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Development Velocity & Type Safety
- Value Impact: Centralized type definitions, eliminates duplication
- Strategic Impact: Single source of truth for WebSocket data structures

Consolidated types from 20+ files into single module.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import time
from pydantic import BaseModel, Field


class WebSocketConnectionState(str, Enum):
    """WebSocket connection states."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class MessageType(str, Enum):
    """Standard WebSocket message types."""
    # Connection lifecycle
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    HEARTBEAT = "heartbeat"
    HEARTBEAT_ACK = "heartbeat_ack"
    PING = "ping"
    PONG = "pong"
    
    # User messages
    USER_MESSAGE = "user_message"
    SYSTEM_MESSAGE = "system_message"
    ERROR_MESSAGE = "error_message"
    
    # Agent communication
    START_AGENT = "start_agent"
    AGENT_RESPONSE = "agent_response"
    AGENT_PROGRESS = "agent_progress"
    AGENT_ERROR = "agent_error"
    
    # Thread/conversation
    THREAD_UPDATE = "thread_update"
    THREAD_MESSAGE = "thread_message"
    
    # Broadcasting
    BROADCAST = "broadcast"
    ROOM_MESSAGE = "room_message"
    
    # JSON-RPC (MCP compatibility)
    JSONRPC_REQUEST = "jsonrpc_request"
    JSONRPC_RESPONSE = "jsonrpc_response"
    JSONRPC_NOTIFICATION = "jsonrpc_notification"


class ConnectionInfo(BaseModel):
    """WebSocket connection information."""
    connection_id: str
    user_id: str
    thread_id: Optional[str] = None
    connected_at: datetime
    last_activity: datetime
    message_count: int = 0
    is_healthy: bool = True
    client_info: Optional[Dict[str, Any]] = None


class WebSocketMessage(BaseModel):
    """Standard WebSocket message format."""
    type: MessageType
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[float] = None
    message_id: Optional[str] = None
    user_id: Optional[str] = None
    thread_id: Optional[str] = None


class ServerMessage(BaseModel):
    """Server-to-client message format."""
    type: MessageType
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float
    server_id: Optional[str] = None
    correlation_id: Optional[str] = None


class ErrorMessage(BaseModel):
    """WebSocket error message."""
    type: MessageType = MessageType.ERROR_MESSAGE
    error_code: str
    error_message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: float
    recovery_suggestions: Optional[List[str]] = None


class BroadcastMessage(BaseModel):
    """Broadcast message format."""
    type: MessageType = MessageType.BROADCAST
    content: Dict[str, Any]
    target_room: Optional[str] = None
    exclude_users: Optional[List[str]] = None
    priority: str = "normal"  # low, normal, high, critical


class JsonRpcMessage(BaseModel):
    """JSON-RPC message format for MCP compatibility."""
    jsonrpc: str = "2.0"
    method: Optional[str] = None
    params: Optional[Union[Dict[str, Any], List[Any]]] = None
    id: Optional[Union[str, int]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class WebSocketStats(BaseModel):
    """WebSocket manager statistics."""
    active_connections: int
    total_connections: int
    messages_sent: int
    messages_received: int
    errors_handled: int
    uptime_seconds: float
    rooms_active: int
    broadcasts_sent: int


class BroadcastResult(BaseModel):
    """Result of broadcast operation."""
    success: bool
    delivered_count: int
    failed_count: int
    error_details: Optional[List[str]] = None


class WebSocketValidationError(BaseModel):
    """WebSocket message validation error."""
    error_type: str  # type_error, validation_error, format_error
    message: str
    field: str
    received_data: Dict[str, Any] = Field(default_factory=dict)


class RateLimitInfo(BaseModel):
    """Rate limiting information."""
    requests_count: int
    window_seconds: int
    remaining_requests: int
    reset_time: float
    is_limited: bool = False


class ConnectionMetrics(BaseModel):
    """Connection-specific metrics."""
    connection_id: str
    user_id: str
    connect_time: datetime
    last_message_time: Optional[datetime] = None
    total_messages_sent: int = 0
    total_messages_received: int = 0
    total_errors: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    average_response_time_ms: Optional[float] = None


class RoomInfo(BaseModel):
    """Room/channel information."""
    room_id: str
    member_count: int
    created_at: datetime
    last_activity: Optional[datetime] = None
    room_type: str = "general"  # general, thread, broadcast, private
    metadata: Optional[Dict[str, Any]] = None


class WebSocketConfig(BaseModel):
    """WebSocket configuration."""
    max_connections_per_user: int = 3
    max_message_rate_per_minute: int = 30
    max_message_size_bytes: int = 8192
    connection_timeout_seconds: int = 300
    heartbeat_interval_seconds: int = 45
    cleanup_interval_seconds: int = 60
    enable_compression: bool = False
    allowed_origins: List[str] = Field(default_factory=list)


class AuthInfo(BaseModel):
    """Authentication information for WebSocket connections."""
    user_id: str
    email: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)
    auth_method: str  # header, subprotocol, cookie
    token_expires: Optional[datetime] = None
    authenticated_at: datetime


# Type aliases for common patterns
MessagePayload = Dict[str, Any]
ConnectionId = str
UserId = str
RoomId = str
ThreadId = str
MessageId = str

# Message type mappings for backward compatibility
LEGACY_MESSAGE_TYPE_MAP = {
    "ping": MessageType.PING,
    "pong": MessageType.PONG,
    "heartbeat": MessageType.HEARTBEAT,
    "user_input": MessageType.USER_MESSAGE,
    "agent_response": MessageType.AGENT_RESPONSE,
    "error": MessageType.ERROR_MESSAGE,
    "system": MessageType.SYSTEM_MESSAGE,
    "broadcast": MessageType.BROADCAST
}


def normalize_message_type(message_type: Union[str, MessageType]) -> MessageType:
    """Normalize legacy message types to standard MessageType."""
    if isinstance(message_type, MessageType):
        return message_type
    
    # Check legacy mappings first
    if message_type in LEGACY_MESSAGE_TYPE_MAP:
        return LEGACY_MESSAGE_TYPE_MAP[message_type]
    
    # Try direct enum conversion
    try:
        return MessageType(message_type)
    except ValueError:
        # Default to user message for unknown types
        return MessageType.USER_MESSAGE


def create_standard_message(msg_type: Union[str, MessageType], 
                          payload: Dict[str, Any],
                          user_id: Optional[str] = None,
                          thread_id: Optional[str] = None) -> WebSocketMessage:
    """Create standardized WebSocket message."""
    import time
    import uuid
    
    normalized_type = normalize_message_type(msg_type)
    
    return WebSocketMessage(
        type=normalized_type,
        payload=payload,
        timestamp=time.time(),
        message_id=str(uuid.uuid4()),
        user_id=user_id,
        thread_id=thread_id
    )


def create_error_message(error_code: str, 
                        error_message: str,
                        details: Optional[Dict[str, Any]] = None,
                        suggestions: Optional[List[str]] = None) -> ErrorMessage:
    """Create standardized error message."""
    import time
    
    return ErrorMessage(
        error_code=error_code,
        error_message=error_message,
        details=details or {},
        timestamp=time.time(),
        recovery_suggestions=suggestions
    )


def create_server_message(msg_type: Union[str, MessageType],
                         data: Dict[str, Any],
                         correlation_id: Optional[str] = None) -> ServerMessage:
    """Create standardized server message."""
    import time
    
    normalized_type = normalize_message_type(msg_type)
    
    return ServerMessage(
        type=normalized_type,
        data=data,
        timestamp=time.time(),
        correlation_id=correlation_id
    )


def is_jsonrpc_message(message: Dict[str, Any]) -> bool:
    """Check if message is JSON-RPC format."""
    return (
        isinstance(message, dict) and
        message.get("jsonrpc") == "2.0" and
        ("method" in message or "result" in message or "error" in message)
    )


def convert_jsonrpc_to_websocket_message(jsonrpc_msg: Dict[str, Any]) -> WebSocketMessage:
    """Convert JSON-RPC message to WebSocket message format."""
    if "method" in jsonrpc_msg:
        msg_type = MessageType.JSONRPC_REQUEST
    elif "result" in jsonrpc_msg or "error" in jsonrpc_msg:
        msg_type = MessageType.JSONRPC_RESPONSE
    else:
        msg_type = MessageType.JSONRPC_NOTIFICATION
    
    return WebSocketMessage(
        type=msg_type,
        payload=jsonrpc_msg,
        timestamp=time.time()
    )


# Batch Message Processing Types

class MessageState(str, Enum):
    """Message processing states for batch operations."""
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"


class BatchingStrategy(str, Enum):
    """Batching strategy options."""
    SIZE_BASED = "size_based"
    TIME_BASED = "time_based"
    ADAPTIVE = "adaptive"
    PRIORITY_BASED = "priority_based"


class BatchConfig(BaseModel):
    """Configuration for batch message processing."""
    max_batch_size: int = 10
    max_wait_time: float = 0.1
    strategy: BatchingStrategy = BatchingStrategy.ADAPTIVE
    enable_compression: bool = False
    retry_attempts: int = 3
    retry_delay_seconds: float = 0.5
    priority_threshold: int = 100


class PendingMessage(BaseModel):
    """A message pending in the batch queue."""
    content: Dict[str, Any]
    connection_id: str
    user_id: str
    thread_id: Optional[str] = None
    priority: int = 0
    created_at: float = Field(default_factory=time.time)
    state: MessageState = MessageState.PENDING
    retry_count: int = 0
    max_retries: int = 3
    last_retry_time: float = Field(default_factory=time.time)
    message_id: Optional[str] = None


class MessageBatch(BaseModel):
    """A batch of messages ready for sending."""
    messages: List[PendingMessage]
    connection_id: str
    user_id: str
    batch_id: str
    created_at: float = Field(default_factory=time.time)
    total_size_bytes: int = 0
    compression_enabled: bool = False