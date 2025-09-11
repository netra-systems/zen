"""Core strongly-typed identifiers and data structures to prevent type drift.

This module provides NewType wrappers and structured types for critical system identifiers
that are currently suffering from string-based type drift across the platform.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: System Reliability and Type Safety
- Value Impact: Prevents type confusion bugs, improves IDE support, enforces validation
- Strategic Impact: Reduces debugging time and prevents production errors from type mismatches

Key Type Safety Principles:
1. Use NewType for semantically different identifiers (prevents mixing user_id with thread_id)
2. Use Pydantic models for complex structures that need validation
3. Use dataclasses for simple structures that don't need validation
4. Use Enums for constrained string values
5. Provide conversion utilities for backward compatibility
"""

from typing import NewType, Dict, Any, Optional, List
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field, field_validator, field_serializer
from dataclasses import dataclass


# =============================================================================
# Core Identity Types - Prevent ID mixing and type confusion
# =============================================================================

# User and authentication identifiers
UserID = NewType('UserID', str)
"""Strongly typed user identifier - prevents mixing with other ID types."""

SessionID = NewType('SessionID', str)  
"""Strongly typed session identifier for authentication sessions."""

TokenString = NewType('TokenString', str)
"""Strongly typed token string (JWT, OAuth, etc)."""

# Execution context identifiers
ThreadID = NewType('ThreadID', str)
"""Strongly typed conversation thread identifier."""

RunID = NewType('RunID', str)
"""Strongly typed execution run identifier."""

RequestID = NewType('RequestID', str)
"""Strongly typed request identifier for tracing."""

# WebSocket and connection identifiers
WebSocketID = NewType('WebSocketID', str)
"""Strongly typed WebSocket connection identifier."""

ConnectionID = NewType('ConnectionID', str)
"""Strongly typed general connection identifier."""

# Agent and execution identifiers
AgentID = NewType('AgentID', str)
"""Strongly typed agent instance identifier."""

ExecutionID = NewType('ExecutionID', str)
"""Strongly typed agent execution identifier."""

ContextID = NewType('ContextID', str)
"""Strongly typed context identifier."""

MessageID = NewType('MessageID', str)
"""Strongly typed message identifier."""

# Database and external service identifiers
DatabaseSessionID = NewType('DatabaseSessionID', str)
"""Strongly typed database session identifier."""

OrganizationID = NewType('OrganizationID', str)
"""Strongly typed organization identifier for multi-tenant support."""


# =============================================================================
# Authentication and Authorization Types
# =============================================================================

class AuthValidationResult(BaseModel):
    """Strongly typed authentication validation result."""
    valid: bool
    user_id: Optional[UserID] = None
    email: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    expires_at: Optional[datetime] = None
    auth_method: Optional[str] = None
    
    @property
    def is_valid(self) -> bool:
        """Compatibility property for legacy code that expects is_valid."""
        return self.valid
    
    @field_validator('user_id', mode='before')
    @classmethod
    def validate_user_id(cls, v):
        if v is not None and isinstance(v, str):
            return UserID(v)
        return v


class SessionValidationResult(BaseModel):
    """Strongly typed session validation result."""
    valid: bool
    user_id: Optional[UserID] = None
    session_id: Optional[SessionID] = None
    permissions: List[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None
    
    @field_validator('user_id', mode='before')
    @classmethod
    def validate_user_id(cls, v):
        if v is not None and isinstance(v, str):
            return UserID(v)
        return v
        
    @field_validator('session_id', mode='before')
    @classmethod
    def validate_session_id(cls, v):
        if v is not None and isinstance(v, str):
            return SessionID(v)
        return v


class TokenResponse(BaseModel):
    """Strongly typed token response."""
    access_token: TokenString
    refresh_token: Optional[TokenString] = None
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    user_id: Optional[UserID] = None
    
    @field_validator('access_token', mode='before')
    @classmethod
    def validate_access_token(cls, v):
        if isinstance(v, str):
            return TokenString(v)
        return v
        
    @field_validator('refresh_token', mode='before')
    @classmethod
    def validate_refresh_token(cls, v):
        if v is not None and isinstance(v, str):
            return TokenString(v)
        return v
        
    @field_validator('user_id', mode='before')
    @classmethod
    def validate_user_id(cls, v):
        if v is not None and isinstance(v, str):
            return UserID(v)
        return v


# =============================================================================
# WebSocket and Connection Types
# =============================================================================

class ConnectionState(Enum):
    """WebSocket connection states."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"
    CLOSING = "closing"


@dataclass
class WebSocketConnectionInfo:
    """Strongly typed WebSocket connection information."""
    websocket_id: WebSocketID
    user_id: UserID
    connection_state: ConnectionState
    connected_at: datetime
    last_ping: Optional[datetime] = None
    message_count: int = 0


class WebSocketEventType(Enum):
    """WebSocket event types."""
    AGENT_STARTED = "agent_started"
    AGENT_THINKING = "agent_thinking"  
    AGENT_COMPLETED = "agent_completed"
    TOOL_EXECUTING = "tool_executing"
    TOOL_COMPLETED = "tool_completed"
    ERROR_OCCURRED = "error_occurred"
    STATUS_UPDATE = "status_update"


class WebSocketMessage(BaseModel):
    """Strongly typed WebSocket message structure."""
    event_type: WebSocketEventType
    user_id: UserID
    thread_id: ThreadID
    request_id: RequestID
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @field_validator('user_id', mode='before')
    @classmethod
    def validate_user_id(cls, v):
        if isinstance(v, str):
            return UserID(v)
        return v
        
    @field_validator('thread_id', mode='before')
    @classmethod
    def validate_thread_id(cls, v):
        if isinstance(v, str):
            return ThreadID(v)
        return v
        
    @field_validator('request_id', mode='before')
    @classmethod
    def validate_request_id(cls, v):
        if isinstance(v, str):
            return RequestID(v)
        return v
    
    @field_serializer('event_type')
    def serialize_event_type(self, value: WebSocketEventType) -> str:
        """Serialize WebSocketEventType enum to string value for frontend compatibility."""
        return value.value


class WebSocketAuthContext(BaseModel):
    """Strongly typed WebSocket authentication context."""
    user_id: UserID
    websocket_client_id: WebSocketID
    permissions: List[str]
    auth_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    session_data: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('user_id', mode='before')
    @classmethod
    def validate_user_id(cls, v):
        if isinstance(v, str):
            return UserID(v)
        return v
        
    @field_validator('websocket_client_id', mode='before') 
    @classmethod
    def validate_websocket_client_id(cls, v):
        if isinstance(v, str):
            return WebSocketID(v)
        return v


# =============================================================================
# Agent Execution Context Types
# =============================================================================

class ExecutionContextState(Enum):
    """Agent execution context states."""
    CREATED = "created"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExecutionMetrics:
    """Strongly typed execution metrics."""
    execution_id: ExecutionID
    start_time: datetime
    end_time: Optional[datetime] = None
    tool_calls: int = 0
    websocket_events: int = 0
    errors: int = 0
    state: ExecutionContextState = ExecutionContextState.CREATED


class AgentExecutionContext(BaseModel):
    """Strongly typed agent execution context."""
    execution_id: ExecutionID
    agent_id: AgentID
    user_id: UserID
    thread_id: ThreadID
    run_id: RunID
    request_id: RequestID
    websocket_id: Optional[WebSocketID] = None
    state: ExecutionContextState = ExecutionContextState.CREATED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Additional fields for supervisor compatibility
    retry_count: int = 0
    max_retries: int = 3
    timeout: Optional[int] = None
    correlation_id: Optional[str] = None
    pipeline_step_num: Optional[int] = None
    
    @field_validator('execution_id', mode='before')
    @classmethod
    def validate_execution_id(cls, v):
        if isinstance(v, str):
            return ExecutionID(v)
        return v
        
    @field_validator('agent_id', mode='before')
    @classmethod
    def validate_agent_id(cls, v):
        if isinstance(v, str):
            return AgentID(v)
        return v
        
    @field_validator('user_id', mode='before')
    @classmethod
    def validate_user_id(cls, v):
        if isinstance(v, str):
            return UserID(v)
        return v
        
    @field_validator('thread_id', mode='before')
    @classmethod
    def validate_thread_id(cls, v):
        if isinstance(v, str):
            return ThreadID(v)
        return v
        
    @field_validator('run_id', mode='before')
    @classmethod
    def validate_run_id(cls, v):
        if isinstance(v, str):
            return RunID(v)
        return v
        
    @field_validator('request_id', mode='before')
    @classmethod
    def validate_request_id(cls, v):
        if isinstance(v, str):
            return RequestID(v)
        return v
        
    @field_validator('websocket_id', mode='before')
    @classmethod
    def validate_websocket_id(cls, v):
        if v is not None and isinstance(v, str):
            return WebSocketID(v)
        return v


# =============================================================================
# Database and Storage Types  
# =============================================================================

@dataclass
class DatabaseConnectionInfo:
    """Strongly typed database connection information."""
    session_id: DatabaseSessionID
    user_id: UserID
    created_at: datetime
    last_activity: datetime
    connection_pool: str
    isolation_level: str = "READ_COMMITTED"


# =============================================================================
# Type Conversion Utilities for Backward Compatibility
# =============================================================================

def ensure_user_id(value: Any) -> UserID:
    """Convert string to UserID with validation using enhanced dual format support."""
    # Import here to avoid circular imports
    from netra_backend.app.core.unified_id_manager import is_valid_id_format_compatible, IDType
    
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Invalid user_id: {value}")
    
    cleaned_value = value.strip()
    
    # Use enhanced validation that supports both UUID and structured formats
    if is_valid_id_format_compatible(cleaned_value, IDType.USER):
        return UserID(cleaned_value)
    
    raise ValueError(f"Invalid user_id format: {value}")


def ensure_thread_id(value: Any) -> ThreadID:
    """Convert string to ThreadID with validation using enhanced dual format support."""
    # Import here to avoid circular imports
    from netra_backend.app.core.unified_id_manager import is_valid_id_format_compatible, IDType
    
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Invalid thread_id: {value}")
    
    cleaned_value = value.strip()
    
    # Use enhanced validation that supports both UUID and structured formats
    if is_valid_id_format_compatible(cleaned_value, IDType.THREAD):
        return ThreadID(cleaned_value)
    
    raise ValueError(f"Invalid thread_id format: {value}")


def ensure_run_id(value: Any) -> RunID:
    """Convert string to RunID with validation using enhanced dual format support."""
    # Import here to avoid circular imports
    from netra_backend.app.core.unified_id_manager import is_valid_id_format_compatible
    
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Invalid run_id: {value}")
    
    cleaned_value = value.strip()
    
    # Run IDs have special validation since they can contain thread IDs
    # Use the general format validation for now
    if is_valid_id_format_compatible(cleaned_value):
        return RunID(cleaned_value)
    
    raise ValueError(f"Invalid run_id format: {value}")


def ensure_request_id(value: Any) -> RequestID:
    """Convert string to RequestID with validation using enhanced dual format support."""
    # Import here to avoid circular imports
    from netra_backend.app.core.unified_id_manager import is_valid_id_format_compatible, IDType
    
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Invalid request_id: {value}")
    
    cleaned_value = value.strip()
    
    # Use enhanced validation that supports both UUID and structured formats
    if is_valid_id_format_compatible(cleaned_value, IDType.REQUEST):
        return RequestID(cleaned_value)
    
    raise ValueError(f"Invalid request_id format: {value}")


def ensure_websocket_id(value: Any) -> Optional[WebSocketID]:
    """Convert string to WebSocketID with validation using enhanced dual format support."""
    if value is None:
        return None
    
    # Import here to avoid circular imports
    from netra_backend.app.core.unified_id_manager import is_valid_id_format_compatible, IDType
    
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Invalid websocket_id: {value}")
    
    cleaned_value = value.strip()
    
    # Use enhanced validation that supports both UUID and structured formats
    if is_valid_id_format_compatible(cleaned_value, IDType.WEBSOCKET):
        return WebSocketID(cleaned_value)
    
    raise ValueError(f"Invalid websocket_id format: {value}")


def ensure_session_id(value: Any) -> SessionID:
    """Convert string to SessionID with validation using enhanced dual format support."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Invalid session_id: {value}")
    
    cleaned_value = value.strip()
    
    # Session IDs are typically UUIDs - validate UUID format
    try:
        import uuid
        # This will raise ValueError if not a valid UUID
        uuid.UUID(cleaned_value)
        return SessionID(cleaned_value)
    except ValueError:
        raise ValueError(f"Invalid session_id format (must be UUID): {value}")


def ensure_connection_id(value: Any) -> ConnectionID:
    """Convert string to ConnectionID with validation using enhanced dual format support."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Invalid connection_id: {value}")
    
    # Import here to avoid circular imports
    from netra_backend.app.core.unified_id_manager import is_valid_id_format_compatible, IDType
    
    cleaned_value = value.strip()
    
    # Use enhanced validation that supports both UUID and structured formats
    # ConnectionID uses WEBSOCKET validation since they're closely related
    if is_valid_id_format_compatible(cleaned_value, IDType.WEBSOCKET):
        return ConnectionID(cleaned_value)
    
    raise ValueError(f"Invalid connection_id format: {value}")


# =============================================================================
# Enhanced Dual Format Utilities for Migration
# =============================================================================

def normalize_to_structured_id(id_value: str, id_type_enum) -> str:
    """
    Normalize any ID format to structured format during migration.
    
    Args:
        id_value: ID in any valid format
        id_type_enum: IDType enum value from UnifiedIDManager
        
    Returns:
        ID in structured format
    """
    # Import here to avoid circular imports
    from netra_backend.app.core.unified_id_manager import (
        validate_and_normalize_id, 
        is_valid_id_format_compatible
    )
    
    if not is_valid_id_format_compatible(id_value, id_type_enum):
        raise ValueError(f"Invalid ID format for normalization: {id_value}")
    
    is_valid, normalized = validate_and_normalize_id(id_value, id_type_enum)
    if not is_valid or normalized is None:
        raise ValueError(f"Could not normalize ID: {id_value}")
    
    return normalized


def create_strongly_typed_execution_context(
    execution_id: str,
    agent_id: str, 
    user_id: str,
    thread_id: str,
    run_id: str,
    request_id: str,
    websocket_id: Optional[str] = None,
    normalize_ids: bool = False,
    retry_count: int = 0,
    max_retries: int = 3,
    timeout: Optional[int] = None,
    correlation_id: Optional[str] = None,
    pipeline_step_num: Optional[int] = None
) -> 'AgentExecutionContext':
    """
    Create strongly typed execution context with dual format support.
    
    Args:
        execution_id: Execution identifier
        agent_id: Agent identifier  
        user_id: User identifier
        thread_id: Thread identifier
        run_id: Run identifier
        request_id: Request identifier
        websocket_id: Optional WebSocket identifier
        normalize_ids: Whether to normalize UUIDs to structured format
        
    Returns:
        AgentExecutionContext with validated IDs
    """
    if normalize_ids:
        # Import here to avoid circular imports
        from netra_backend.app.core.unified_id_manager import IDType
        
        # Normalize all IDs to structured format
        execution_id = normalize_to_structured_id(execution_id, IDType.EXECUTION)
        agent_id = normalize_to_structured_id(agent_id, IDType.AGENT) 
        user_id = normalize_to_structured_id(user_id, IDType.USER)
        thread_id = normalize_to_structured_id(thread_id, IDType.THREAD)
        request_id = normalize_to_structured_id(request_id, IDType.REQUEST)
        if websocket_id:
            websocket_id = normalize_to_structured_id(websocket_id, IDType.WEBSOCKET)
    
    # Create the context with type validation
    return AgentExecutionContext(
        execution_id=execution_id,
        agent_id=agent_id,
        user_id=user_id,
        thread_id=thread_id,
        run_id=run_id,
        request_id=request_id,
        websocket_id=websocket_id,
        retry_count=retry_count,
        max_retries=max_retries,
        timeout=timeout,
        correlation_id=correlation_id,
        pipeline_step_num=pipeline_step_num
    )


# =============================================================================
# Legacy String Compatibility Layer
# =============================================================================

def to_string_dict(typed_data: Dict[Any, Any]) -> Dict[str, str]:
    """Convert typed identifiers back to strings for legacy compatibility."""
    return {str(k): str(v) for k, v in typed_data.items()}


def from_string_dict(string_data: Dict[str, str], expected_types: Dict[str, type]) -> Dict[str, Any]:
    """Convert string dictionary to typed identifiers."""
    result = {}
    for key, value in string_data.items():
        if key in expected_types:
            type_constructor = expected_types[key]
            if type_constructor in [UserID, ThreadID, RunID, RequestID, WebSocketID]:
                result[key] = type_constructor(value)
            else:
                result[key] = value
        else:
            result[key] = value
    return result


# =============================================================================
# Supervisor Compatibility Layer for Migration
# =============================================================================

def create_execution_context_from_supervisor_style(
    run_id: str,
    thread_id: str,
    user_id: str,
    agent_name: str,
    request_id: Optional[str] = None,
    retry_count: int = 0,
    max_retries: int = 3,
    timeout: Optional[int] = None,
    correlation_id: Optional[str] = None,
    pipeline_step_num: Optional[int] = None,
    **metadata
) -> 'AgentExecutionContext':
    """
    Create SSOT AgentExecutionContext from supervisor-style parameters.
    
    This function bridges the gap between the legacy supervisor dataclass format
    and the strongly typed SSOT Pydantic model.
    """
    # Generate required IDs
    import uuid
    from netra_backend.app.core.unified_id_manager import IDType
    
    execution_id = str(uuid.uuid4())
    
    # Convert agent_name to agent_id (since SSOT uses agent_id)
    agent_id = agent_name
    
    # Ensure request_id exists
    if request_id is None:
        request_id = str(uuid.uuid4())
    
    return create_strongly_typed_execution_context(
        execution_id=execution_id,
        agent_id=agent_id,
        user_id=user_id,
        thread_id=thread_id,
        run_id=run_id,
        request_id=request_id,
        retry_count=retry_count,
        max_retries=max_retries,
        timeout=timeout,
        correlation_id=correlation_id,
        pipeline_step_num=pipeline_step_num,
        normalize_ids=True
    )