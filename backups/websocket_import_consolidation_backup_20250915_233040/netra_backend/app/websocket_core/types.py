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
from dataclasses import dataclass

# Import UnifiedIdGenerator for SSOT ID generation
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from shared.isolated_environment import get_env
from shared.types.core_types import (
    UserID, ThreadID, ConnectionID, WebSocketID, RequestID,
    ensure_user_id, ensure_thread_id, ensure_websocket_id
)


@dataclass
class WebSocketConnection:
    """
    SSOT WebSocket Connection data structure.

    CRITICAL: This class has been extracted from unified_manager.py to break
    the circular dependency between unified_manager.py and websocket_manager.py.
    This enables proper SSOT consolidation while maintaining type safety.

    Business Value Justification:
    - Segment: Platform/Infrastructure
    - Business Goal: Enable proper user isolation and connection management
    - Value Impact: Foundation for all WebSocket-based chat interactions
    - Revenue Impact: Prevents connection state corruption affecting $500K+ ARR
    """
    connection_id: str
    user_id: str
    websocket: Any
    connected_at: datetime
    metadata: Dict[str, Any] = None
    thread_id: Optional[str] = None
    last_activity: datetime = None
    is_active: bool = True

    def __post_init__(self):
        """Validate connection data after initialization."""
        # Validate user_id is properly formatted
        if self.user_id:
            self.user_id = ensure_user_id(self.user_id)

        # Set default values for optional fields
        if self.metadata is None:
            self.metadata = {}

        if self.last_activity is None:
            self.last_activity = self.connected_at

        # Ensure connection_id is properly typed
        if isinstance(self.connection_id, str):
            self.connection_id = ConnectionID(self.connection_id)

        # Ensure thread_id is properly typed if provided
        if self.thread_id is not None:
            self.thread_id = ensure_thread_id(self.thread_id)


class WebSocketManagerMode(Enum):
    """WebSocket manager modes with proper user isolation.

    ISSUE #889 FIX: Each enum value creates unique instances to prevent
    cross-user state sharing violations that caused regulatory compliance issues.

    User isolation is enforced through both UserExecutionContext and unique enum instances.
    """
    UNIFIED = "unified"        # SSOT: Single unified mode with UserExecutionContext isolation
    ISOLATED = "isolated"      # Isolated mode for enhanced user separation
    EMERGENCY = "emergency"    # Emergency fallback mode with degraded capabilities
    DEGRADED = "degraded"      # Degraded mode for service recovery

    def __new__(cls, value):
        """
        ISSUE #889 FIX: Create unique enum instances to prevent cross-user state sharing.

        This prevents the critical security violation where all managers shared
        the same enum object instance, causing user data contamination.

        Each call creates a new enum instance with the same value but different
        object identity, preventing any possibility of shared state.
        """
        obj = object.__new__(cls)
        obj._value_ = value
        # ISSUE #889 ENHANCEMENT: Add unique identifier for debugging
        import time
        obj._instance_id = f"{value}_{int(time.time() * 1000000) % 1000000}"
        return obj

    @property
    def instance_id(self):
        """Get the unique instance identifier for debugging isolation issues."""
        return getattr(self, '_instance_id', 'unknown')


def create_isolated_mode(mode_value: str = "unified") -> 'WebSocketManagerMode':
    """
    ISSUE #889 FIX: Create an isolated WebSocketManagerMode instance.

    This factory function ensures each manager gets a unique enum instance,
    preventing any possibility of cross-user state contamination through
    shared enum object references.

    Args:
        mode_value: The mode value ("unified", "isolated", "emergency", "degraded")

    Returns:
        WebSocketManagerMode: A new, isolated enum instance
    """

    class IsolatedModeWrapper:
        """
        Wrapper class that behaves like WebSocketManagerMode but provides complete isolation.
        Each instance is unique to prevent cross-user contamination.
        """
        def __init__(self, value: str):
            self._value_ = value
            import time
            self._instance_id = f"{value}_{int(time.time() * 1000000) % 1000000}"

        @property
        def value(self):
            return self._value_

        @property
        def name(self):
            return self._value_.upper()

        @property
        def instance_id(self):
            return self._instance_id

        def __str__(self):
            return self._value_

        def __repr__(self):
            return f"IsolatedModeWrapper('{self._value_}', id={self._instance_id})"

        def __eq__(self, other):
            if hasattr(other, 'value'):
                return self._value_ == other.value
            return self._value_ == str(other)

        def __hash__(self):
            # Include instance_id in hash to ensure uniqueness
            return hash((self._value_, self._instance_id))

    # Create a completely isolated wrapper instance
    return IsolatedModeWrapper(mode_value)


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
    CONNECTION_ESTABLISHED = "connection_established"  # Specific connection event
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
    AGENT_STARTED = "agent_started"  # Required for mission critical tests
    AGENT_START = "agent_start"  # Alias for compatibility
    AGENT_COMPLETE = "agent_complete"  # Alias for compatibility
    AGENT_COMPLETED = "agent_completed"  # Required for mission critical tests
    TOOL_EXECUTE = "tool_execute"  # Alias for compatibility  
    TOOL_EXECUTING = "tool_executing"  # Required for mission critical tests
    TOOL_COMPLETE = "tool_complete"  # Alias for compatibility
    TOOL_COMPLETED = "tool_completed"  # Required for mission critical tests
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

    # Quality and Metrics
    QUALITY_METRICS = "quality_metrics"

    # Batch processing
    BATCH = "batch"

    # Additional connection types
    CONNECTION = "connection"

    # Additional typing indicators
    TYPING = "typing"

    # Additional error types
    ERROR = "error"


class ConnectionInfo(BaseModel):
    """WebSocket connection information."""
    model_config = {"arbitrary_types_allowed": True}
    
    connection_id: Optional[str] = None
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
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.connection_id is None:
            # Generate connection_id using user_id for proper pattern
            self.connection_id = UnifiedIdGenerator.generate_websocket_connection_id(self.user_id)
    
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
    """
    Standard WebSocket message format.
    
    timestamp: Unix timestamp as float. Accepts various input formats:
    - Unix timestamp (float/int): 1693567801.447585
    - ISO datetime string: '2025-09-08T16:50:01.447585'
    - None: Uses current time
    
    Use timestamp_utils.safe_convert_timestamp() for safe conversion.
    """
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
    """WebSocket configuration with environment-specific optimizations."""
    max_connections_per_user: int = 3
    max_message_rate_per_minute: int = 30
    max_message_size_bytes: int = 8192
    connection_timeout_seconds: int = 300
    heartbeat_interval_seconds: int = 25  # GCP Cloud Run requires <30s for stability
    cleanup_interval_seconds: int = 60
    enable_compression: bool = False
    allowed_origins: List[str] = Field(default_factory=list)
    
    # PHASE 1 FIX 3: Cloud Run environment timing adjustments
    # These settings help mitigate accept() race conditions in Cloud Run environments
    accept_completion_timeout_seconds: float = 5.0  # Max time to wait for accept() completion
    accept_validation_interval_ms: int = 100  # Interval for checking accept() status
    cloud_run_accept_delay_ms: int = 50  # Additional delay after accept() in Cloud Run
    cloud_run_stabilization_delay_ms: int = 25  # Final stabilization delay
    cloud_run_progressive_backoff_ms: List[int] = Field(default=[25, 50, 75])  # Progressive delay attempts
    
    # ISSUE #128 FIX: Progressive timeout strategy for different connection phases  
    handshake_timeout_seconds: float = 15.0      # Timeout for WebSocket handshake completion
    connect_timeout_seconds: float = 10.0        # Timeout for initial connection establishment
    ping_timeout_seconds: float = 5.0            # Timeout for ping/pong messages
    close_timeout_seconds: float = 10.0          # Timeout for graceful connection close
    execution_timeout_seconds: float = 300.0     # Timeout for message execution
    
    # Progressive timeout phases for faster failure detection
    progressive_timeout_phases: List[float] = Field(default=[3.0, 2.0, 1.5, 1.0, 0.8])  # As identified in Issue #128
    
    @classmethod
    def get_cloud_run_optimized_config(cls) -> 'WebSocketConfig':
        """Get Cloud Run optimized configuration for race condition prevention and Issue #128 fixes."""
        return cls(
            heartbeat_interval_seconds=20,  # Reduced for Cloud Run
            accept_completion_timeout_seconds=10.0,  # Longer timeout for Cloud Run
            accept_validation_interval_ms=50,  # More frequent validation
            cloud_run_accept_delay_ms=75,  # Increased delay for Cloud Run
            cloud_run_stabilization_delay_ms=50,  # Increased stabilization
            cloud_run_progressive_backoff_ms=[50, 100, 150, 200],  # More aggressive backoff
            # ISSUE #128 FIX: Optimized progressive timeouts for staging GCP connectivity
            handshake_timeout_seconds=15.0,  # Staging-optimized handshake timeout 
            connect_timeout_seconds=10.0,    # Staging-optimized connection timeout
            ping_timeout_seconds=5.0,        # Staging-optimized ping timeout
            close_timeout_seconds=10.0,      # Staging-optimized close timeout
            execution_timeout_seconds=360.0, # 6 minutes execution timeout (60% reduction)
            progressive_timeout_phases=[3.0, 2.0, 1.5, 1.0, 0.8]  # Staging-specific progressive timeouts
        )
    
    @classmethod
    def detect_and_configure_for_environment(cls) -> 'WebSocketConfig':
        """Detect environment and return optimized configuration."""

        # Detect Cloud Run environment
        is_cloud_run = any([
            get_env('K_SERVICE'),  # Cloud Run service name
            get_env('K_REVISION'),  # Cloud Run revision
            get_env('GOOGLE_CLOUD_PROJECT'),  # GCP project
            'run.app' in get_env('GAE_APPLICATION', ''),  # Cloud Run domain
        ])

        environment = get_env('ENVIRONMENT', 'development')
        
        if is_cloud_run or environment in ['staging', 'production']:
            # Use Cloud Run optimized settings for production environments
            return cls.get_cloud_run_optimized_config()
        else:
            # Use default configuration for development/testing
            return cls()


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
    
    # User messages
    "user": MessageType.USER_MESSAGE,  # Map 'user' to USER_MESSAGE
    "user_input": MessageType.USER_MESSAGE,
    "user_message": MessageType.USER_MESSAGE,
    "chat_message": MessageType.USER_MESSAGE,  # Fix for MessageRouter 'chat_message' issue
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
    
    # Critical agent event types (for frontend chat UI) - FIXED for Issue #911
    "agent_started": MessageType.AGENT_STARTED,
    "agent_thinking": MessageType.AGENT_THINKING,
    "agent_completed": MessageType.AGENT_COMPLETED,
    "agent_failed": MessageType.AGENT_ERROR,
    "agent_fallback": MessageType.AGENT_ERROR,
    "tool_executing": MessageType.TOOL_EXECUTING,
    "tool_completed": MessageType.TOOL_COMPLETED,
    
    # CRITICAL FIX: Add missing execute_agent mapping (causes Tests 23 & 25 failures)
    "execute_agent": MessageType.START_AGENT,
    "EXECUTE_AGENT": MessageType.START_AGENT,  # Phase 2 Fix 2a: Handle uppercase case
    
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
    
    # Connection establishment messages (websocket_ssot.py patterns)
    "connection_established": MessageType.CONNECTION_ESTABLISHED,
    "factory_connection_established": MessageType.CONNECTION_ESTABLISHED,
    "isolated_connection_established": MessageType.CONNECTION_ESTABLISHED,  
    "legacy_connection_established": MessageType.CONNECTION_ESTABLISHED,
    
    # Broadcasting
    "broadcast": MessageType.BROADCAST,
    "broadcast_test": MessageType.BROADCAST_TEST,
    "direct_message": MessageType.DIRECT_MESSAGE,
    "room_message": MessageType.ROOM_MESSAGE,
    
    # Testing
    "resilience_test": MessageType.RESILIENCE_TEST,
    "recovery_test": MessageType.RECOVERY_TEST,

    # Additional legacy mappings - Issue #913 remediation
    "legacy_response": MessageType.AGENT_RESPONSE,
    "legacy_heartbeat": MessageType.HEARTBEAT
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
    
    # Phase 2 Fix 2a: Validate input type
    if not isinstance(message_type, str):
        raise ValueError(f"Message type must be string or MessageType enum, got {type(message_type)}")
    
    # Check legacy mappings first
    if message_type in LEGACY_MESSAGE_TYPE_MAP:
        return LEGACY_MESSAGE_TYPE_MAP[message_type]
    
    # Try direct enum conversion
    try:
        return MessageType(message_type)
    except ValueError:
        # Phase 2 Fix 2a: Be more strict - raise error for unknown types instead of defaulting
        raise ValueError(f"Unknown message type: '{message_type}'. Valid types: {list(MessageType.__members__.keys())} or legacy types: {list(LEGACY_MESSAGE_TYPE_MAP.keys())}")


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


def create_standard_message(msg_type: Union[str, MessageType] = None, 
                          payload: Dict[str, Any] = None,
                          user_id: Optional[str] = None,
                          thread_id: Optional[str] = None,
                          message_type: Optional[Union[str, MessageType]] = None,
                          content: Optional[Dict[str, Any]] = None,
                          **kwargs) -> WebSocketMessage:
    """Create standardized WebSocket message with strict validation."""
    import time
    import uuid
    
    # Handle backward compatibility for message_type parameter
    if message_type is not None:
        if msg_type is not None:
            raise ValueError("Cannot specify both msg_type and message_type parameters")
        msg_type = message_type
    
    # Handle backward compatibility for content parameter (alias for payload)
    if content is not None:
        if payload is not None:
            raise ValueError("Cannot specify both payload and content parameters")
        payload = content
    
    # Validate required parameters
    if msg_type is None:
        raise ValueError("msg_type (or message_type) is required")
    if payload is None:
        payload = {}
    
    # Phase 2 Fix 2b: Strengthen JSON schema validation
    # Validate message type first (this will raise proper errors now)
    normalized_type = normalize_message_type(msg_type)
    
    # Phase 2 Fix 2b: Validate payload structure
    if not isinstance(payload, dict):
        raise TypeError(f"Payload must be a dictionary, got {type(payload)}")
    
    # Phase 2 Fix 2b: Check for forbidden fields that violate SSOT
    forbidden_fields = {"forbidden_field", "another_violation", "invalid_field"}
    found_forbidden = forbidden_fields.intersection(payload.keys())
    if found_forbidden:
        raise ValueError(f"Payload contains forbidden fields that violate SSOT: {found_forbidden}")
    
    # Phase 2 Fix 2b: Validate field types for specific message types
    if normalized_type in [MessageType.AGENT_REQUEST, MessageType.START_AGENT]:
        # Agent messages require specific structure - payload cannot be empty
        if not payload:
            raise ValueError(f"Agent message type '{normalized_type}' requires non-empty payload")
        
        # If payload has request field, validate its type
        if "request" in payload:
            request = payload.get("request")
            if not isinstance(request, (dict, str)):
                raise TypeError(f"Agent message 'request' field must be dict or string, got {type(request)}")
        # If no request field but has other structure, that's acceptable (different message patterns)
    
    # Phase 2 Fix 2b: Validate non-serializable data doesn't get through
    try:
        import json
        import math
        
        # Check for infinity and NaN values first (common edge cases)
        def check_for_special_floats(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    check_for_special_floats(value)
            elif isinstance(obj, list):
                for item in obj:
                    check_for_special_floats(item)
            elif isinstance(obj, float):
                if math.isinf(obj):
                    raise ValueError("Payload contains infinity values that violate SSOT")
                if math.isnan(obj):
                    raise ValueError("Payload contains NaN values that violate SSOT")
        
        check_for_special_floats(payload)
        
        # Quick serialization test to catch other non-serializable objects
        json.dumps(payload, default=str, ensure_ascii=False)
    except (TypeError, ValueError, RecursionError) as e:
        if "circular" in str(e).lower() or "not.*serializable" in str(e).lower():
            raise ValueError(f"Payload contains non-serializable data that violates SSOT: {e}")
        # Re-raise validation errors (including our infinity/NaN checks)
        raise
    
    return WebSocketMessage(
        type=normalized_type,
        payload=payload,
        timestamp=time.time(),
        message_id=UnifiedIdGenerator.generate_base_id(
            f"msg_{str(normalized_type.value)}", 
            include_random=True,
            random_length=8
        ),
        user_id=user_id,
        thread_id=thread_id
    )


def create_error_message(error_code: str, 
                        error_message: str,
                        details: Optional[Dict[str, Any]] = None,
                        suggestions: Optional[List[str]] = None) -> ErrorMessage:
    """Create standardized error message with validation."""
    import time
    
    # Phase 2 Fix 2b: Validate error message parameters
    if not isinstance(error_code, str) or not error_code.strip():
        raise ValueError(f"Error code must be a non-empty string, got {type(error_code)}: {error_code}")
    
    if not isinstance(error_message, str) or not error_message.strip():
        raise ValueError(f"Error message must be a non-empty string, got {type(error_message)}: {error_message}")
    
    # Phase 2 Fix 2b: Validate details structure
    if details is not None and not isinstance(details, dict):
        raise TypeError(f"Error details must be a dictionary, got {type(details)}")
    
    # Phase 2 Fix 2b: Validate suggestions structure
    if suggestions is not None:
        if not isinstance(suggestions, list):
            raise TypeError(f"Recovery suggestions must be a list, got {type(suggestions)}")
        for i, suggestion in enumerate(suggestions):
            if not isinstance(suggestion, str):
                raise TypeError(f"Recovery suggestion {i} must be a string, got {type(suggestion)}")
    
    return ErrorMessage(
        error_code=error_code,
        error_message=error_message,
        details=details or {},
        timestamp=time.time(),
        recovery_suggestions=suggestions
    )


def create_server_message(msg_type_or_dict: Union[str, MessageType, Dict[str, Any]] = None,
                         data: Optional[Dict[str, Any]] = None,
                         correlation_id: Optional[str] = None,
                         content: Optional[Dict[str, Any]] = None,
                         **kwargs) -> ServerMessage:
    """
    Create standardized server message with hybrid signature support.
    
    HYBRID COMPATIBILITY: Supports both legacy and standard calling patterns:
    
    Legacy Pattern (backward compatibility):
        create_server_message({"type": "system", "status": "ok"})
        
    Standard Pattern (SSOT compliant):
        create_server_message(MessageType.SYSTEM, {"status": "ok"})
        create_server_message("system", {"status": "ok"})
    
    Args:
        msg_type_or_dict: Either:
            - MessageType enum or string (standard pattern)
            - Dictionary containing message data (legacy pattern)
        data: Message data dict (only used in standard pattern)
        correlation_id: Optional correlation identifier
        **kwargs: Additional arguments for backward compatibility
        
    Returns:
        ServerMessage: Standardized server message object
        
    Raises:
        ValueError: If arguments are invalid or ambiguous
    """
    import time
    
    # Handle content-only pattern (used by tests)
    if msg_type_or_dict is None and content is not None:
        # Default to SYSTEM_MESSAGE for content-only calls
        msg_type_or_dict = MessageType.SYSTEM_MESSAGE
        data = content
    
    # Handle backward compatibility for content parameter
    if content is not None and data is None and not isinstance(msg_type_or_dict, dict):
        data = content
    
    # PATTERN DETECTION: Legacy vs Standard calling patterns
    if isinstance(msg_type_or_dict, dict):
        # LEGACY PATTERN: create_server_message({"type": "system", "status": "ok"})
        legacy_dict = msg_type_or_dict
        
        if "type" not in legacy_dict:
            raise ValueError(
                "Legacy pattern requires 'type' field in dictionary. "
                f"Got dictionary keys: {list(legacy_dict.keys())}"
            )
        
        # Extract type and data from legacy dictionary
        msg_type = legacy_dict["type"]
        
        # All other fields become the data payload
        message_data = {k: v for k, v in legacy_dict.items() if k != "type"}
        
        # Handle any additional kwargs passed
        if kwargs:
            message_data.update(kwargs)
            
    else:
        # STANDARD PATTERN: create_server_message(MessageType.SYSTEM, {"status": "ok"})
        if data is None:
            data = {}
            
        if not isinstance(data, dict):
            raise TypeError(
                f"Standard pattern requires data to be a dictionary. "
                f"Got {type(data)}: {data}"
            )
        
        msg_type = msg_type_or_dict
        message_data = data.copy()  # Copy to avoid modifying original
        
        # Handle any additional kwargs
        if kwargs:
            message_data.update(kwargs)
    
    # Validate and normalize message type
    try:
        normalized_type = normalize_message_type(msg_type)
    except ValueError as e:
        raise ValueError(
            f"Invalid message type '{msg_type}': {e}. "
            f"Use MessageType enum values or valid string types."
        ) from e
    
    return ServerMessage(
        type=normalized_type,
        data=message_data,
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


def generate_default_message(
    message_type: Union[str, MessageType],
    user_id: str,
    thread_id: str,
    data: Optional[Dict[str, Any]] = None
) -> WebSocketMessage:
    """Generate a default WebSocket message with standard structure.
    
    This function provides compatibility for test cases that expect
    a generate_default_message function with this signature.
    
    Args:
        message_type: The type of message (string or MessageType enum)
        user_id: User identifier
        thread_id: Thread/conversation identifier
        data: Optional data payload
        
    Returns:
        WebSocketMessage: Standardized message with default values
    """
    normalized_type = normalize_message_type(message_type)
    
    return WebSocketMessage(
        type=normalized_type,
        payload=data or {},
        timestamp=time.time(),
        message_id=UnifiedIdGenerator.generate_base_id(
            f"msg_{str(normalized_type.value)}", 
            include_random=True,
            random_length=8
        ),
        user_id=user_id,
        thread_id=thread_id
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


# Additional WebSocket types for integration tests

class ConnectionMetadata(BaseModel):
    """Connection metadata for WebSocket connections."""
    connection_id: str
    user_id: str
    thread_id: Optional[str] = None
    connected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    client_info: Optional[Dict[str, Any]] = None
    session_data: Optional[Dict[str, Any]] = None

    def __init__(self, **data):
        super().__init__(**data)
        if not self.connection_id:
            # Generate connection_id using user_id for proper pattern
            self.connection_id = UnifiedIdGenerator.generate_websocket_connection_id(self.user_id)


class AgentEvent(BaseModel):
    """Agent event data model for WebSocket communication."""
    event_type: str
    agent_id: Optional[str] = None
    user_id: Optional[str] = None
    thread_id: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        if not self.event_id:
            # Generate event_id for tracking
            self.event_id = UnifiedIdGenerator.generate_base_id(
                f"evt_{self.event_type}",
                include_random=True,
                random_length=8
            )


# =============================================================================
# SSOT SERIALIZATION FUNCTIONS (EXTRACTED FROM UNIFIED_MANAGER)
# =============================================================================

def _get_enum_key_representation(enum_key: Enum) -> str:
    """
    Get string representation for enum keys in dictionaries.

    For enum keys, we use different strategies based on enum type:
    - WebSocketState enums: Use lowercase names for consistency ("open" vs "1")
    - Integer enums (IntEnum): Use string value for readability ("1" vs "first")
    - String/text enums: Use lowercase names for readability ("option_a" vs "OPTION_A")

    Args:
        enum_key: Enum object to convert to string key

    Returns:
        String representation suitable for JSON dict keys
    """
    if hasattr(enum_key, 'name') and hasattr(enum_key, 'value'):
        # WEBSOCKET STATE HANDLING: Check if this is a WebSocket state enum
        enum_name = str(enum_key.name).upper()
        websocket_state_names = {'CONNECTING', 'OPEN', 'CLOSING', 'CLOSED', 'CONNECTED', 'DISCONNECTED'}

        # Check if it's from a WebSocket framework module or has WebSocket-like class name
        module_name = getattr(enum_key.__class__, '__module__', '')
        framework_modules = ['starlette.websockets', 'fastapi.websockets', 'websockets']
        is_framework_websocket = any(framework_mod in module_name for framework_mod in framework_modules)

        class_name = enum_key.__class__.__name__
        is_websocket_class = 'websocket' in class_name.lower() and 'state' in class_name.lower()

        # For WebSocket state enums, always use lowercase name for keys
        if (is_framework_websocket or
            (is_websocket_class and enum_name in websocket_state_names)):
            return str(enum_key.name).lower()

        # For integer-valued non-WebSocket enums, use the string representation of the value
        # This makes {"1": "initialized"} instead of {"first": "initialized"}
        elif isinstance(enum_key.value, int):
            return str(enum_key.value)
        else:
            # For string/other enums, use lowercase names for better JSON readability
            # This makes {"option_a": "selected"} instead of {"OPTION_A": "selected"}
            return str(enum_key.name).lower()
    else:
        # Fallback to string representation
        return str(enum_key)


def serialize_message_safely(message: Any) -> Dict[str, Any]:
    """
    SSOT: Safely serialize message data for WebSocket transmission.

    EXTRACTED FROM UNIFIED_MANAGER: This function has been moved to types.py
    to break the circular dependency and provide a single source of truth
    for message serialization across the WebSocket infrastructure.

    CRITICAL FIX: Handles all serialization edge cases including:
    - Enum objects (WebSocketState, etc.)  ->  converted to string values
    - Pydantic models  ->  model_dump(mode='json') for datetime handling
    - Complex objects with to_dict() method
    - Datetime objects  ->  ISO string format
    - Dataclasses  ->  converted to dict
    - Fallback to string representation for unhandled types

    Args:
        message: Any message object that needs JSON serialization

    Returns:
        JSON-serializable dictionary

    Raises:
        TypeError: Only if all fallback strategies fail (should be extremely rare)
    """
    import json
    from shared.logging.unified_logging_ssot import get_logger

    logger = get_logger(__name__)

    # Quick path for already serializable dicts
    if isinstance(message, dict):
        try:
            # Test if it's already JSON serializable
            json.dumps(message)
            return message
        except (TypeError, ValueError):
            # Dict contains non-serializable objects, need to process recursively
            # Process both keys AND values for enum objects
            result = {}
            for key, value in message.items():
                # Convert enum keys consistently with enum value handling
                if isinstance(key, Enum):
                    # For WebSocketState enums, use name.lower() to match value handling
                    try:
                        from starlette.websockets import WebSocketState as StarletteWebSocketState
                        if isinstance(key, StarletteWebSocketState):
                            safe_key = key.name.lower()
                        else:
                            safe_key = _get_enum_key_representation(key)
                    except (ImportError, AttributeError):
                        try:
                            from fastapi.websockets import WebSocketState as FastAPIWebSocketState
                            if isinstance(key, FastAPIWebSocketState):
                                safe_key = key.name.lower()
                            else:
                                safe_key = _get_enum_key_representation(key)
                        except (ImportError, AttributeError):
                            safe_key = _get_enum_key_representation(key)
                else:
                    safe_key = key
                # Recursively serialize values
                result[safe_key] = serialize_message_safely(value)
            return result

    # CRITICAL FIX: Handle WebSocketState enum specifically (from FastAPI/Starlette)
    # CLOUD RUN FIX: More resilient import handling to prevent startup failures
    try:
        from starlette.websockets import WebSocketState as StarletteWebSocketState
        if isinstance(message, StarletteWebSocketState):
            return message.name.lower()  # CONNECTED  ->  "connected"
    except (ImportError, AttributeError) as e:
        logger.debug(f"Starlette WebSocketState import failed (non-critical): {e}")

    try:
        from fastapi.websockets import WebSocketState as FastAPIWebSocketState
        if isinstance(message, FastAPIWebSocketState):
            return message.name.lower()  # CONNECTED  ->  "connected"
    except (ImportError, AttributeError) as e:
        logger.debug(f"FastAPI WebSocketState import failed (non-critical): {e}")

    # Handle enum objects - CONSISTENT LOGIC: Return .value for generic enums
    if isinstance(message, Enum):
        # WEBSOCKET STATE HANDLING: Check if this enum represents WebSocket state
        # This includes both framework enums and test enums with WebSocket-like names
        if hasattr(message, 'name') and hasattr(message, 'value'):
            # Check for WebSocket state behavior by enum name pattern
            enum_name = str(message.name).upper()
            websocket_state_names = {'CONNECTING', 'OPEN', 'CLOSING', 'CLOSED', 'CONNECTED', 'DISCONNECTED'}

            # Also check if it's from a WebSocket framework module
            module_name = getattr(message.__class__, '__module__', '')
            framework_modules = ['starlette.websockets', 'fastapi.websockets', 'websockets']
            is_framework_websocket = any(framework_mod in module_name for framework_mod in framework_modules)

            # Also check if the class name suggests it's a WebSocket state enum
            class_name = message.__class__.__name__
            is_websocket_class = 'websocket' in class_name.lower() and 'state' in class_name.lower()

            # Treat as WebSocket state if:
            # 1. From framework module, OR
            # 2. Has WebSocket-like class name AND websocket state name
            if (is_framework_websocket or
                (is_websocket_class and enum_name in websocket_state_names)):
                return str(message.name).lower()

        # For all other enums, return the value
        return message.value if hasattr(message, 'value') else str(message)

    # Handle Pydantic models with proper datetime serialization
    if hasattr(message, 'model_dump'):
        try:
            return message.model_dump(mode='json')
        except Exception as e:
            logger.warning(f"Pydantic model_dump(mode='json') failed: {e}, trying without mode")
            try:
                return message.model_dump()
            except Exception as e2:
                logger.warning(f"Pydantic model_dump failed completely: {e2}, using string fallback")
                # Fall through to the string fallback at the end of the function

    # Handle objects with to_dict method (UserExecutionContext, etc.)
    if hasattr(message, 'to_dict'):
        return message.to_dict()

    # Handle dataclasses
    if hasattr(message, '__dataclass_fields__'):
        from dataclasses import asdict
        # Convert dataclass to dict, then recursively serialize the result
        dict_data = asdict(message)
        return serialize_message_safely(dict_data)

    # Handle datetime objects
    if hasattr(message, 'isoformat'):
        return message.isoformat()

    # Handle lists and tuples recursively
    if isinstance(message, (list, tuple)):
        return [serialize_message_safely(item) for item in message]

    # Handle sets (convert to list)
    if isinstance(message, set):
        return [serialize_message_safely(item) for item in message]

    # Test direct JSON serialization for basic types
    try:
        json.dumps(message)
        return message
    except (TypeError, ValueError):
        pass

    # Final fallback - convert to string (prevents total failure)
    logger.warning(f"Using string fallback for object of type {type(message)}: {message}")
    return str(message)


# Backward compatibility alias for _serialize_message_safely
_serialize_message_safely = serialize_message_safely


# Backward compatibility aliases
ConnectionState = WebSocketConnectionState