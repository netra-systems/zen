"""Shared type definitions - Single Source of Truth for common types.

This module provides canonical type definitions to prevent SSOT violations
across the codebase. All services should import from here rather than
defining duplicate types.

CRITICAL TYPE SAFETY UPDATE:
- Core strongly-typed identifiers to prevent type drift
- Execution context types for proper request isolation  
- Authentication types with validation
- WebSocket event types with routing safety
"""

from .performance_metrics import PerformanceMetrics
from .user_types import UserBase, UserInfo, UserCreate, UserUpdate, ExtendedUser

# Core strongly-typed identifiers (prevents ID mixing bugs)
from .core_types import (
    UserID, ThreadID, RunID, RequestID, WebSocketID, AgentID, ExecutionID,
    SessionID, TokenString, ConnectionID, DatabaseSessionID, ContextID, MessageID, OrganizationID,
    # Validation utilities
    ensure_user_id, ensure_thread_id, ensure_run_id, ensure_request_id, ensure_websocket_id,
    # Authentication types
    AuthValidationResult, SessionValidationResult, TokenResponse,
    # WebSocket types
    ConnectionState, WebSocketConnectionInfo, WebSocketEventType, WebSocketMessage, WebSocketAuthContext,
    # Database types
    DatabaseConnectionInfo,
    # Compatibility utilities
    to_string_dict, from_string_dict
)

# Execution context and agent types  
from .execution_types import (
    # Context types
    StronglyTypedUserExecutionContext, ContextValidationError, IsolationViolationError,
    # Agent execution types
    AgentExecutionState, AgentExecutionMetrics, 
    # Tool execution types
    ToolExecutionState, ToolExecutionRequest, ToolExecutionResult,
    # WebSocket events
    WebSocketEventPriority, StronglyTypedWebSocketEvent,
    # Factory types
    AgentCreationRequest, AgentCreationResult,
    # Migration utilities
    upgrade_legacy_context, downgrade_to_legacy_context
)

# Agent request/response/validation types - SSOT for agent execution flows
from .agent_types import (
    # Core agent execution types
    AgentExecutionRequest, AgentExecutionResult, AgentValidationResult,
    # Enhanced typed result for better validation
    TypedAgentResult
)

# Service types - imported from netra_backend for compatibility
try:
    from netra_backend.app.schemas.startup_types import ServiceType
except ImportError:
    # Define ServiceType enum locally if netra_backend not available
    from enum import Enum
    class ServiceType(str, Enum):
        """Service types for startup tracking."""
        BACKEND = "backend"
        FRONTEND = "frontend"

__all__ = [
    # Legacy types
    "PerformanceMetrics", 
    "UserBase", "UserInfo", "UserCreate", "UserUpdate", "ExtendedUser",
    
    # Core typed identifiers - CRITICAL for type safety
    "UserID", "ThreadID", "RunID", "RequestID", "WebSocketID", "AgentID", "ExecutionID",
    "SessionID", "TokenString", "ConnectionID", "DatabaseSessionID", "ContextID", "MessageID", "OrganizationID",
    
    # Validation utilities
    "ensure_user_id", "ensure_thread_id", "ensure_run_id", "ensure_request_id", "ensure_websocket_id",
    
    # Authentication types
    "AuthValidationResult", "SessionValidationResult", "TokenResponse",
    
    # WebSocket types
    "ConnectionState", "WebSocketConnectionInfo", "WebSocketEventType", "WebSocketMessage", "WebSocketAuthContext",
    "WebSocketEventPriority", "StronglyTypedWebSocketEvent",
    
    # Database types
    "DatabaseConnectionInfo",
    
    # Execution context types - CRITICAL for request isolation
    "StronglyTypedUserExecutionContext", "ContextValidationError", "IsolationViolationError",
    
    # Agent execution types
    "AgentExecutionState", "AgentExecutionMetrics",
    
    # Agent request/response/validation types - CRITICAL for agent execution flows
    "AgentExecutionRequest", "AgentExecutionResult", "AgentValidationResult", "TypedAgentResult",
    
    # Tool execution types  
    "ToolExecutionState", "ToolExecutionRequest", "ToolExecutionResult",
    
    # Factory types
    "AgentCreationRequest", "AgentCreationResult",
    
    # Migration and compatibility utilities
    "upgrade_legacy_context", "downgrade_to_legacy_context",
    "to_string_dict", "from_string_dict",
    
    # Service types
    "ServiceType"
]