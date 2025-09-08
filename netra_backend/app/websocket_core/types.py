"""
WebSocket Types and Data Models

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Development Velocity & Type Safety
- Value Impact: Centralized type definitions, eliminates duplication
- Strategic Impact: Single source of truth for WebSocket data structures

Consolidated types from 20+ files into single module.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import time
import uuid
from pydantic import BaseModel, Field


class WebSocketConnectionState(str, Enum):
    """WebSocket connection states."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    # Compatibility aliases for tests
    ACTIVE = "connected"  # Alias for CONNECTED
    CLOSING = "disconnecting"  # Alias for DISCONNECTING  
    CLOSED = "disconnected"  # Alias for DISCONNECTED
    FAILED = "error"  # Alias for ERROR


class ReconnectionState(str, Enum):
    """States for reconnection process."""
    IDLE = "idle"
    ATTEMPTING = "attempting"
    CONNECTED = "connected"
    FAILED = "failed"
    DISABLED = "disabled"


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
    CHAT = "chat"
    SYSTEM_MESSAGE = "system_message"
    ERROR_MESSAGE = "error_message"
    
    # Typing indicators
    USER_TYPING = "user_typing"
    AGENT_TYPING = "agent_typing"
    TYPING_STARTED = "typing_started"
    TYPING_STOPPED = "typing_stopped"
    
    # Agent communication
    START_AGENT = "start_agent"
    AGENT_REQUEST = "agent_request"
    AGENT_TASK = "agent_task"
    AGENT_TASK_ACK = "agent_task_ack"
    AGENT_RESPONSE = "agent_response"
    AGENT_RESPONSE_CHUNK = "agent_response_chunk"
    AGENT_RESPONSE_COMPLETE = "agent_response_complete"
    AGENT_STATUS_REQUEST = "agent_status_request"
    AGENT_STATUS_UPDATE = "agent_status_update"
    AGENT_PROGRESS = "agent_progress"
    AGENT_THINKING = "agent_thinking"  # Alias for AGENT_PROGRESS
    AGENT_ERROR = "agent_error"
    
    # Thread/conversation
    THREAD_UPDATE = "thread_update"
    THREAD_MESSAGE = "thread_message"
    
    # Broadcasting
    BROADCAST = "broadcast"
    BROADCAST_TEST = "broadcast_test"
    DIRECT_MESSAGE = "direct_message"
    ROOM_MESSAGE = "room_message"
    
    # JSON-RPC (MCP compatibility)
    JSONRPC_REQUEST = "jsonrpc_request"
    JSONRPC_RESPONSE = "jsonrpc_response"
    JSONRPC_NOTIFICATION = "jsonrpc_notification"
    
    # Testing/Resilience
    RESILIENCE_TEST = "resilience_test"
    RECOVERY_TEST = "recovery_test"


class ConnectionInfo(BaseModel):
    """WebSocket connection information."""
    model_config = {"arbitrary_types_allowed": True}
    
    connection_id: str = Field(default_factory=lambda: f"conn_{uuid.uuid4().hex[:8]}")
    user_id: str
    websocket: Optional[Any] = None  # WebSocket instance
    thread_id: Optional[str] = None
    connected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message_count: int = 0
    error_count: int = 0  # Track connection errors
    last_ping: Optional[datetime] = None  # Last ping timestamp
    is_healthy: bool = True
    is_closing: bool = False
    client_info: Optional[Dict[str, Any]] = None
    state: WebSocketConnectionState = WebSocketConnectionState.ACTIVE
    failure_count: int = 0  # Track state transition failures
    
    def transition_to_failed(self):
        """Transition connection to failed state."""
        self.state = WebSocketConnectionState.FAILED
        self.is_healthy = False
        self.failure_count += 1
        return True
    
    def transition_to_closing(self):
        """Transition connection to closing state."""
        # Cannot transition to closing if already closing or closed
        if self.state in [WebSocketConnectionState.CLOSING, WebSocketConnectionState.CLOSED]:
            return False
        self.state = WebSocketConnectionState.CLOSING
        self.is_closing = True
        return True
        
    def transition_to_closed(self):
        """Transition connection to closed state."""
        self.state = WebSocketConnectionState.CLOSED
        self.is_closing = False
        self.is_healthy = False
        return True


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


class TypingIndicator(BaseModel):
    """Typing indicator state."""
    user_id: str
    thread_id: str
    is_typing: bool
    started_at: Optional[float] = None
    last_activity: Optional[float] = None
    timeout_seconds: float = 5.0
    
    def is_expired(self) -> bool:
        """Check if typing indicator has expired."""
        if not self.is_typing or not self.last_activity:
            return False
        return (time.time() - self.last_activity) > self.timeout_seconds
    
    def update_activity(self) -> None:
        """Update activity timestamp."""
        self.last_activity = time.time()
        if not self.started_at:
            self.started_at = self.last_activity


class TypingMessage(BaseModel):
    """Typing indicator WebSocket message."""
    type: MessageType
    user_id: str
    thread_id: str
    is_typing: bool
    timestamp: float = Field(default_factory=time.time)


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


class ReconnectionConfig(BaseModel):
    """Configuration for WebSocket reconnection behavior."""
    enabled: bool = True
    max_attempts: int = 5
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    backoff_multiplier: float = 2.0
    jitter_enabled: bool = True
    max_jitter_seconds: float = 2.0
    connection_timeout_seconds: float = 10.0
    ping_interval_seconds: float = 30.0
    ping_timeout_seconds: float = 5.0
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number."""
        import random
        if attempt <= 0:
            return self.initial_delay_seconds
            
        delay = min(
            self.initial_delay_seconds * (self.backoff_multiplier ** (attempt - 1)),
            self.max_delay_seconds
        )
        
        if self.jitter_enabled:
            jitter = random.uniform(0, min(self.max_jitter_seconds, delay * 0.1))
            delay += jitter
            
        return delay


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
    # Connection lifecycle
    "ping": MessageType.PING,
    "pong": MessageType.PONG,
    "heartbeat": MessageType.HEARTBEAT,
    "connect": MessageType.CONNECT,
    "disconnect": MessageType.DISCONNECT,
    "connected": MessageType.CONNECT,
    "connection_established": MessageType.CONNECT,
    
    # User messages
    "user": MessageType.USER_MESSAGE,  # Map 'user' to USER_MESSAGE
    "user_input": MessageType.USER_MESSAGE,
    "user_message": MessageType.USER_MESSAGE,
    "chat": MessageType.CHAT,
    "message": MessageType.USER_MESSAGE,
    
    # Agent/AI messages - CRITICAL for business value
    "agent": MessageType.AGENT_REQUEST,  # Map 'agent' to AGENT_REQUEST
    "agent_request": MessageType.AGENT_REQUEST,
    "agent_response": MessageType.AGENT_RESPONSE,
    "agent_task": MessageType.AGENT_TASK,
    "agent_task_ack": MessageType.AGENT_TASK_ACK,
    "agent_response_chunk": MessageType.AGENT_RESPONSE_CHUNK,
    "agent_response_complete": MessageType.AGENT_RESPONSE_COMPLETE,
    "agent_status_request": MessageType.AGENT_STATUS_REQUEST,
    "agent_status_update": MessageType.AGENT_STATUS_UPDATE,
    "agent_status": MessageType.AGENT_STATUS_UPDATE,
    "agent_update": MessageType.AGENT_STATUS_UPDATE,
    "agent_progress": MessageType.AGENT_PROGRESS,
    "agent_error": MessageType.AGENT_ERROR,
    "start_agent": MessageType.START_AGENT,
    
    # Critical agent event types (for frontend chat UI)
    "agent_started": MessageType.START_AGENT,
    "agent_thinking": MessageType.AGENT_PROGRESS,
    "agent_completed": MessageType.AGENT_RESPONSE_COMPLETE,
    "agent_failed": MessageType.AGENT_ERROR,
    "agent_fallback": MessageType.AGENT_ERROR,
    "tool_executing": MessageType.AGENT_PROGRESS,
    "tool_completed": MessageType.AGENT_PROGRESS,
    
    # Typing indicators
    "typing": MessageType.USER_TYPING,
    "typing_started": MessageType.TYPING_STARTED,
    "typing_stopped": MessageType.TYPING_STOPPED,
    
    # Thread messages
    "thread": MessageType.THREAD_UPDATE,
    "thread_update": MessageType.THREAD_UPDATE,
    "thread_message": MessageType.THREAD_MESSAGE,
    
    # System/error messages
    "error": MessageType.ERROR_MESSAGE,
    "error_message": MessageType.ERROR_MESSAGE,
    "system": MessageType.SYSTEM_MESSAGE,
    "system_message": MessageType.SYSTEM_MESSAGE,
    
    # Broadcasting
    "broadcast": MessageType.BROADCAST,
    "broadcast_test": MessageType.BROADCAST_TEST,
    "direct_message": MessageType.DIRECT_MESSAGE,
    "room_message": MessageType.ROOM_MESSAGE,
    
    # Testing
    "resilience_test": MessageType.RESILIENCE_TEST,
    "recovery_test": MessageType.RECOVERY_TEST
}

# Frontend compatibility mapping - maps backend types to frontend-expected types
FRONTEND_MESSAGE_TYPE_MAP = {
    MessageType.AGENT_RESPONSE: "agent_completed",
    MessageType.AGENT_PROGRESS: "agent_update",
    MessageType.THREAD_UPDATE: "thread_updated",
    MessageType.ERROR_MESSAGE: "error",
    # Keep others as-is
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


def get_frontend_message_type(message_type: Union[str, MessageType]) -> str:
    """Get frontend-compatible message type string."""
    # Critical agent event types that must pass through unchanged
    AGENT_EVENT_TYPES = {
        "agent_started", "agent_thinking", "agent_completed", 
        "agent_fallback", "agent_failed", "agent_error",
        "tool_executing", "tool_completed", "tool_started",
        "partial_result", "final_report", "stream_chunk",
        "agent_registered", "agent_unregistered", "agent_cancelled",
        "agent_status_changed", "agent_metrics_updated",
        "agent_manager_shutdown", "agent_stopped", "agent_log"
    }
    
    # If it's a string and it's an agent event, pass it through unchanged
    if isinstance(message_type, str) and message_type in AGENT_EVENT_TYPES:
        return message_type
    
    # First normalize to MessageType enum
    normalized = normalize_message_type(message_type)
    
    # Check if we have a frontend mapping
    if normalized in FRONTEND_MESSAGE_TYPE_MAP:
        return FRONTEND_MESSAGE_TYPE_MAP[normalized]
    
    # Otherwise return the enum value as string
    return normalized.value


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


# Backward compatibility aliases
ConnectionState = WebSocketConnectionState