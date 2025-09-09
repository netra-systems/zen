"""Execution-specific strongly typed data structures.

This module provides comprehensive type safety for agent execution, WebSocket events,
and user context management to prevent the critical type drift issues identified
in the current system.

Key Areas Addressed:
1. Agent execution context with proper isolation
2. WebSocket event routing and message handling  
3. User execution context validation and lifecycle
4. Tool execution and result handling
5. Error propagation and state management
"""

from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field, field_validator, ConfigDict
from dataclasses import dataclass, field

from shared.types.core_types import (
    UserID, ThreadID, RunID, RequestID, WebSocketID, AgentID, ExecutionID,
    ensure_user_id, ensure_thread_id, ensure_run_id, ensure_request_id,
    ensure_websocket_id
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# =============================================================================
# User Execution Context - Strongly Typed Version
# =============================================================================

class ContextValidationError(Exception):
    """Raised when execution context validation fails."""
    pass


class IsolationViolationError(Exception):
    """Raised when context isolation is violated."""
    pass


@dataclass(frozen=True)
class StronglyTypedUserExecutionContext:
    """Strongly typed user execution context to replace string-based version.
    
    This provides the same interface as UserExecutionContext but with proper
    type safety to prevent the critical type drift issues.
    
    All identifiers use NewType wrappers to prevent accidental mixing of
    different ID types (e.g., passing user_id where thread_id is expected).
    """
    
    # Core identifiers - strongly typed
    user_id: UserID
    thread_id: ThreadID
    run_id: RunID
    request_id: RequestID
    
    # Session and connection management
    db_session: Optional['AsyncSession'] = field(default=None, repr=False, compare=False)
    websocket_client_id: Optional[WebSocketID] = None
    
    # Audit and lifecycle tracking
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    agent_context: Dict[str, Any] = field(default_factory=dict)
    audit_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Hierarchical context support
    operation_depth: int = 0
    parent_request_id: Optional[RequestID] = None
    
    def __post_init__(self):
        """Validate context after creation."""
        self._validate_identifiers()
        self._validate_context_data()
    
    def _validate_identifiers(self):
        """Validate that all identifiers are proper types."""
        if not isinstance(self.user_id, str) or not self.user_id.strip():
            raise ContextValidationError(f"Invalid user_id: {self.user_id}")
        if not isinstance(self.thread_id, str) or not self.thread_id.strip():
            raise ContextValidationError(f"Invalid thread_id: {self.thread_id}")
        if not isinstance(self.run_id, str) or not self.run_id.strip():
            raise ContextValidationError(f"Invalid run_id: {self.run_id}")
        if not isinstance(self.request_id, str) or not self.request_id.strip():
            raise ContextValidationError(f"Invalid request_id: {self.request_id}")
            
        # Check for forbidden placeholder values
        forbidden_values = [
            "test_user", "mock_user", "placeholder", "default", "example",
            "test_thread", "mock_thread", "test_run", "mock_run", 
            "test_request", "mock_request", "", "none", "null"
        ]
        
        for field_name, value in [
            ("user_id", str(self.user_id)),
            ("thread_id", str(self.thread_id)), 
            ("run_id", str(self.run_id)),
            ("request_id", str(self.request_id))
        ]:
            if value.lower() in forbidden_values:
                raise ContextValidationError(
                    f"Forbidden placeholder value in {field_name}: {value}"
                )
    
    def _validate_context_data(self):
        """Validate context dictionaries for security."""
        if not isinstance(self.agent_context, dict):
            raise ContextValidationError("agent_context must be a dictionary")
        if not isinstance(self.audit_metadata, dict):
            raise ContextValidationError("audit_metadata must be a dictionary")
        
        # Check operation depth bounds
        if self.operation_depth < 0 or self.operation_depth > 10:
            raise ContextValidationError(
                f"Invalid operation_depth: {self.operation_depth} (must be 0-10)"
            )
    
    @property 
    def metadata(self) -> Dict[str, Any]:
        """Backward compatibility: unified metadata view."""
        return {**self.agent_context, **self.audit_metadata}
    
    @property
    def websocket_connection_id(self) -> Optional[WebSocketID]:
        """Backward compatibility alias."""
        return self.websocket_client_id
    
    @property
    def websocket_id(self) -> Optional[WebSocketID]:
        """Backward compatibility alias for websocket_id."""
        return self.websocket_client_id
    
    def create_child_context(self, new_request_id: Optional[RequestID] = None) -> 'StronglyTypedUserExecutionContext':
        """Create child context for sub-operations."""
        import uuid
        
        child_request_id = new_request_id or RequestID(str(uuid.uuid4()))
        
        return StronglyTypedUserExecutionContext(
            user_id=self.user_id,
            thread_id=self.thread_id,
            run_id=self.run_id,
            request_id=child_request_id,
            db_session=self.db_session,  # Shared session 
            websocket_client_id=self.websocket_client_id,
            created_at=datetime.now(timezone.utc),
            agent_context=self.agent_context.copy(),
            audit_metadata=self.audit_metadata.copy(),
            operation_depth=self.operation_depth + 1,
            parent_request_id=self.request_id
        )


# =============================================================================
# Agent Execution State and Lifecycle
# =============================================================================

class AgentExecutionState(Enum):
    """Agent execution lifecycle states."""
    INITIALIZING = "initializing"
    VALIDATING = "validating"
    EXECUTING = "executing"
    TOOL_CALLING = "tool_calling"
    THINKING = "thinking"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ToolExecutionState(Enum):
    """Tool execution states."""
    STARTING = "starting"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class AgentExecutionMetrics:
    """Metrics for agent execution performance."""
    execution_id: ExecutionID
    agent_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    state: AgentExecutionState = AgentExecutionState.INITIALIZING
    
    # Performance metrics
    total_tool_calls: int = 0
    successful_tool_calls: int = 0
    failed_tool_calls: int = 0
    websocket_events_sent: int = 0
    
    # Resource usage
    memory_peak_mb: Optional[float] = None
    cpu_time_seconds: Optional[float] = None
    
    # Error tracking
    error_count: int = 0
    last_error: Optional[str] = None
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate execution duration."""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def success_rate(self) -> float:
        """Calculate tool call success rate."""
        if self.total_tool_calls == 0:
            return 1.0
        return self.successful_tool_calls / self.total_tool_calls


# =============================================================================
# WebSocket Event System - Strongly Typed
# =============================================================================

class WebSocketEventPriority(Enum):
    """WebSocket event priority levels."""
    LOW = "low"
    NORMAL = "normal" 
    HIGH = "high"
    CRITICAL = "critical"


class StronglyTypedWebSocketEvent(BaseModel):
    """Strongly typed WebSocket event to prevent type drift."""
    
    # Event identification
    event_id: str = Field(default_factory=lambda: f"evt_{datetime.now().timestamp()}")
    event_type: str
    priority: WebSocketEventPriority = WebSocketEventPriority.NORMAL
    
    # Context routing - strongly typed
    user_id: UserID
    thread_id: ThreadID
    request_id: RequestID
    websocket_id: Optional[WebSocketID] = None
    
    # Event payload and metadata
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    retry_count: int = 0
    max_retries: int = 3
    
    @field_validator('user_id', mode='before')
    @classmethod
    def validate_user_id(cls, v):
        return ensure_user_id(v)
        
    @field_validator('thread_id', mode='before')
    @classmethod
    def validate_thread_id(cls, v):
        return ensure_thread_id(v)
        
    @field_validator('request_id', mode='before')
    @classmethod
    def validate_request_id(cls, v):
        return ensure_request_id(v)
        
    @field_validator('websocket_id', mode='before')
    @classmethod
    def validate_websocket_id(cls, v):
        return ensure_websocket_id(v)
    
    def to_legacy_dict(self) -> Dict[str, Any]:
        """Convert to legacy string-based dictionary format."""
        return {
            "event_type": self.event_type,
            "user_id": str(self.user_id),
            "thread_id": str(self.thread_id),
            "request_id": str(self.request_id),
            "websocket_id": str(self.websocket_id) if self.websocket_id else None,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.value
        }


# =============================================================================
# Tool Execution Context and Results
# =============================================================================

class ToolExecutionRequest(BaseModel):
    """Strongly typed tool execution request."""
    
    tool_name: str
    execution_id: ExecutionID
    user_context: StronglyTypedUserExecutionContext
    parameters: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: Optional[int] = None
    retry_on_failure: bool = True
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    @field_validator('execution_id', mode='before')
    @classmethod
    def validate_execution_id(cls, v):
        if isinstance(v, str):
            return ExecutionID(v)
        return v


class ToolExecutionResult(BaseModel):
    """Strongly typed tool execution result."""
    
    tool_name: str
    execution_id: ExecutionID
    state: ToolExecutionState
    start_time: datetime
    end_time: Optional[datetime] = None
    
    # Results and outputs
    result: Optional[Any] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    return_code: Optional[int] = None
    
    # Error information
    error: Optional[str] = None
    error_type: Optional[str] = None
    traceback: Optional[str] = None
    
    # Metadata
    retry_count: int = 0
    resource_usage: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('execution_id', mode='before')
    @classmethod
    def validate_execution_id(cls, v):
        if isinstance(v, str):
            return ExecutionID(v)
        return v
    
    @property
    def is_success(self) -> bool:
        """Check if tool execution was successful."""
        return self.state == ToolExecutionState.COMPLETED and self.error is None
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate tool execution duration."""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


# =============================================================================
# Factory and Registry Types
# =============================================================================

@dataclass 
class AgentCreationRequest:
    """Strongly typed agent creation request."""
    agent_name: str
    agent_id: AgentID
    user_context: StronglyTypedUserExecutionContext
    configuration: Dict[str, Any] = field(default_factory=dict)
    websocket_enabled: bool = True
    tool_timeout_seconds: int = 30
    
    def __post_init__(self):
        """Validate agent creation request."""
        if not self.agent_name or not self.agent_name.strip():
            raise ValueError("agent_name cannot be empty")
        if not isinstance(self.agent_id, str) or not self.agent_id.strip():
            raise ValueError("agent_id must be a non-empty string")


@dataclass
class AgentCreationResult:
    """Strongly typed agent creation result."""
    agent_id: AgentID
    agent_instance: Any  # BaseAgent type - avoiding circular import
    creation_time: datetime
    websocket_connected: bool
    metrics: AgentExecutionMetrics
    
    success: bool = True
    error: Optional[str] = None


# =============================================================================
# Migration and Compatibility Utilities
# =============================================================================

def upgrade_legacy_context(legacy_context: Any) -> StronglyTypedUserExecutionContext:
    """Upgrade legacy UserExecutionContext to strongly typed version."""
    
    # Handle both dict and object forms
    if isinstance(legacy_context, dict):
        data = legacy_context
    else:
        data = {
            'user_id': getattr(legacy_context, 'user_id', ''),
            'thread_id': getattr(legacy_context, 'thread_id', ''),
            'run_id': getattr(legacy_context, 'run_id', ''),
            'request_id': getattr(legacy_context, 'request_id', ''),
            'websocket_client_id': getattr(legacy_context, 'websocket_client_id', None),
            'db_session': getattr(legacy_context, 'db_session', None),
            'agent_context': getattr(legacy_context, 'agent_context', {}),
            'audit_metadata': getattr(legacy_context, 'audit_metadata', {}),
            'operation_depth': getattr(legacy_context, 'operation_depth', 0),
            'parent_request_id': getattr(legacy_context, 'parent_request_id', None),
        }
    
    return StronglyTypedUserExecutionContext(
        user_id=ensure_user_id(data.get('user_id')),
        thread_id=ensure_thread_id(data.get('thread_id')),
        run_id=ensure_run_id(data.get('run_id')), 
        request_id=ensure_request_id(data.get('request_id')),
        websocket_client_id=ensure_websocket_id(data.get('websocket_client_id')),
        db_session=data.get('db_session'),
        agent_context=data.get('agent_context', {}),
        audit_metadata=data.get('audit_metadata', {}),
        operation_depth=data.get('operation_depth', 0),
        parent_request_id=RequestID(data['parent_request_id']) if data.get('parent_request_id') else None
    )


def downgrade_to_legacy_context(typed_context: StronglyTypedUserExecutionContext) -> Dict[str, Any]:
    """Downgrade strongly typed context to legacy format for compatibility."""
    return {
        'user_id': str(typed_context.user_id),
        'thread_id': str(typed_context.thread_id),
        'run_id': str(typed_context.run_id),
        'request_id': str(typed_context.request_id),
        'websocket_client_id': str(typed_context.websocket_client_id) if typed_context.websocket_client_id else None,
        'db_session': typed_context.db_session,
        'agent_context': typed_context.agent_context,
        'audit_metadata': typed_context.audit_metadata,
        'operation_depth': typed_context.operation_depth,
        'parent_request_id': str(typed_context.parent_request_id) if typed_context.parent_request_id else None,
        'created_at': typed_context.created_at,
    }