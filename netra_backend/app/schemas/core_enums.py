"""
Core Domain Enums: Single Source of Truth for All Enumeration Types

This module contains all enumeration types used across the Netra platform,
ensuring consistency and preventing duplication.

CRITICAL ARCHITECTURAL COMPLIANCE:
- All enum definitions MUST be imported from this module
- NO duplicate enum definitions allowed anywhere else in codebase
- This file maintains strong typing and single sources of truth
- Maximum file size: 300 lines (currently under limit)

Usage:
    from netra_backend.app.schemas.core_enums import MessageType, AgentStatus, WebSocketMessageType
"""

from enum import Enum
from typing import Literal


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
    
    # Agent lifecycle management (for agent manager)
    AGENT_REGISTERED = "agent_registered"
    AGENT_UNREGISTERED = "agent_unregistered"
    AGENT_FAILED = "agent_failed"
    AGENT_CANCELLED = "agent_cancelled"
    AGENT_STATUS_CHANGED = "agent_status_changed"
    AGENT_METRICS_UPDATED = "agent_metrics_updated"
    AGENT_MANAGER_SHUTDOWN = "agent_manager_shutdown"
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
    THREAD_SWITCHED = "thread_switched"
    STEP_CREATED = "step_created"
    PARTIAL_RESULT = "partial_result"
    FINAL_REPORT = "final_report"
    ERROR = "error"
    CONNECTION_ESTABLISHED = "connection_established"
    STREAM_CHUNK = "stream_chunk"
    STREAM_COMPLETE = "stream_complete"
    MESSAGE_RECEIVED = "message_received"
    
    # Synthetic data generation messages
    GENERATION_STARTED = "generation_started"
    GENERATION_PROGRESS = "generation_progress"
    GENERATION_COMPLETE = "generation_complete"
    GENERATION_ERROR = "generation_error"
    GENERATION_CANCELLED = "generation_cancelled"
    BATCH_COMPLETE = "batch_complete"
    
    # MCP integration messages
    MCP_TOOL_DISCOVERY = "mcp_tool_discovery"
    MCP_TOOL_EXECUTION = "mcp_tool_execution" 
    MCP_TOOL_RESULT = "mcp_tool_result"
    MCP_SERVER_CONNECTED = "mcp_server_connected"
    MCP_SERVER_DISCONNECTED = "mcp_server_disconnected"
    
    # Example message handling for DEV MODE
    EXAMPLE_MESSAGE = "example_message"
    EXAMPLE_MESSAGE_RESPONSE = "example_message_response"


class WebSocketConnectionState(str, Enum):
    """WebSocket connection states."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"


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
    "agent_registered",
    "agent_unregistered",
    "agent_failed",
    "agent_cancelled",
    "agent_status_changed",
    "agent_metrics_updated",
    "agent_manager_shutdown",
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
    "stream_complete",
    "generation_started",
    "generation_progress",
    "generation_complete",
    "generation_error",
    "generation_cancelled",
    "batch_complete"
]


class ErrorCategory(str, Enum):
    """Unified error category classification - consolidates all error types."""
    # System and infrastructure errors
    SYSTEM = "system"
    APPLICATION = "application"
    SECURITY = "security"
    BUSINESS = "business"
    INFRASTRUCTURE = "infrastructure"
    INTEGRATION = "integration"
    USER = "user"
    
    # Operational errors
    VALIDATION = "validation"
    NETWORK = "network"
    DATABASE = "database"
    PROCESSING = "processing"
    WEBSOCKET = "websocket"
    TIMEOUT = "timeout"
    CONFIGURATION = "configuration"
    RESOURCE = "resource"
    UNKNOWN = "unknown"


class CircuitBreakerState(str, Enum):
    """Unified circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class MCPTransport(str, Enum):
    """MCP transport types."""
    STDIO = "stdio"
    HTTP = "http"
    WEBSOCKET = "websocket"


class MCPServerStatus(str, Enum):
    """MCP server status types."""
    REGISTERED = "registered"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"


class MCPAuthType(str, Enum):
    """MCP authentication types."""
    NONE = "none"
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    ENVIRONMENT = "environment"


class MCPToolExecutionStatus(str, Enum):
    """MCP tool execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class TaskPriority(str, Enum):
    """Task priority levels for agent execution."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class ExecutionStatus(str, Enum):
    """Agent execution status enumeration - moved from base.interface to break circular imports."""
    PENDING = "pending"
    INITIALIZING = "initializing"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    FALLBACK = "fallback"
    DEGRADED = "degraded"


# Export all enums
__all__ = [
    "MessageType",
    "AgentStatus", 
    "WebSocketMessageType",
    "WebSocketConnectionState",
    "CorpusAuditAction",
    "CorpusAuditStatus",
    "ErrorCategory",
    "CircuitBreakerState",
    "MCPTransport",
    "MCPServerStatus",
    "MCPAuthType",
    "MCPToolExecutionStatus",
    "TaskPriority",
    "ExecutionStatus",
    "MessageTypeLiteral"
]