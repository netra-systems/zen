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
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator
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

# Database and external service identifiers
DatabaseSessionID = NewType('DatabaseSessionID', str)
"""Strongly typed database session identifier."""


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
    
    @validator('user_id', pre=True)
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
    
    @validator('user_id', pre=True)
    def validate_user_id(cls, v):
        if v is not None and isinstance(v, str):
            return UserID(v)
        return v
        
    @validator('session_id', pre=True)
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
    
    @validator('access_token', pre=True)
    def validate_access_token(cls, v):
        if isinstance(v, str):
            return TokenString(v)
        return v
        
    @validator('refresh_token', pre=True)
    def validate_refresh_token(cls, v):
        if v is not None and isinstance(v, str):
            return TokenString(v)
        return v
        
    @validator('user_id', pre=True)
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
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('user_id', pre=True)
    def validate_user_id(cls, v):
        if isinstance(v, str):
            return UserID(v)
        return v
        
    @validator('thread_id', pre=True)
    def validate_thread_id(cls, v):
        if isinstance(v, str):
            return ThreadID(v)
        return v
        
    @validator('request_id', pre=True)  
    def validate_request_id(cls, v):
        if isinstance(v, str):
            return RequestID(v)
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
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('execution_id', pre=True)
    def validate_execution_id(cls, v):
        if isinstance(v, str):
            return ExecutionID(v)
        return v
        
    @validator('agent_id', pre=True)
    def validate_agent_id(cls, v):
        if isinstance(v, str):
            return AgentID(v)
        return v
        
    @validator('user_id', pre=True)
    def validate_user_id(cls, v):
        if isinstance(v, str):
            return UserID(v)
        return v
        
    @validator('thread_id', pre=True)
    def validate_thread_id(cls, v):
        if isinstance(v, str):
            return ThreadID(v)
        return v
        
    @validator('run_id', pre=True)
    def validate_run_id(cls, v):
        if isinstance(v, str):
            return RunID(v)
        return v
        
    @validator('request_id', pre=True)
    def validate_request_id(cls, v):
        if isinstance(v, str):
            return RequestID(v)
        return v
        
    @validator('websocket_id', pre=True)
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
    """Convert string to UserID with validation."""
    if isinstance(value, UserID):
        return value
    if isinstance(value, str) and value.strip():
        return UserID(value.strip())
    raise ValueError(f"Invalid user_id: {value}")


def ensure_thread_id(value: Any) -> ThreadID:
    """Convert string to ThreadID with validation."""
    if isinstance(value, ThreadID):
        return value
    if isinstance(value, str) and value.strip():
        return ThreadID(value.strip())
    raise ValueError(f"Invalid thread_id: {value}")


def ensure_run_id(value: Any) -> RunID:
    """Convert string to RunID with validation."""
    if isinstance(value, RunID):
        return value
    if isinstance(value, str) and value.strip():
        return RunID(value.strip())
    raise ValueError(f"Invalid run_id: {value}")


def ensure_request_id(value: Any) -> RequestID:
    """Convert string to RequestID with validation."""
    if isinstance(value, RequestID):
        return value
    if isinstance(value, str) and value.strip():
        return RequestID(value.strip())
    raise ValueError(f"Invalid request_id: {value}")


def ensure_websocket_id(value: Any) -> Optional[WebSocketID]:
    """Convert string to WebSocketID with validation."""
    if value is None:
        return None
    if isinstance(value, WebSocketID):
        return value
    if isinstance(value, str) and value.strip():
        return WebSocketID(value.strip())
    raise ValueError(f"Invalid websocket_id: {value}")


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