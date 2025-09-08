"""UserExecutionContext for request isolation and state management.

This module provides the core UserExecutionContext class that carries all per-request
state through the execution chain to prevent global state issues and user data leakage.

The context follows immutable design patterns with fail-fast validation to ensure
data integrity and proper request isolation.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class InvalidContextError(Exception):
    """Raised when UserExecutionContext contains invalid data."""
    pass


@dataclass(frozen=True)
class UserExecutionContext:
    """Immutable context carrying all per-request state through execution chain.
    
    This class is designed to prevent global state issues and user data leakage
    by providing a single source of truth for all request-specific data that
    flows through the entire execution pipeline.
    
    Key Design Principles:
    - Immutable once created (frozen=True)
    - No global state references
    - Pass-through pattern (flows through all layers)
    - Fail-fast on invalid data (no placeholder values)
    
    Attributes:
        user_id: Unique identifier for the user making the request
        thread_id: Unique identifier for the conversation thread
        run_id: Unique identifier for this specific execution run
        request_id: Unique identifier for this specific request
        db_session: Optional database session for this request
        websocket_client_id: Optional WebSocket client identifier for event routing
        created_at: Timestamp when context was created
        metadata: Extensible dictionary for additional context data
    """
    
    user_id: str
    thread_id: str
    run_id: str
    db_session: Optional[AsyncSession] = field(default=None, repr=False)
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: Optional[str] = field(default=None)
    websocket_client_id: Optional[str] = field(default=None)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate context data after initialization."""
        self._validate_required_ids()
        self._validate_no_placeholder_values()
        self._validate_metadata()
        
        # Ensure metadata isolation by copying if it's not the default empty dict
        # Use object.__setattr__ because this is a frozen dataclass
        if self.metadata is not None and id(self.metadata) != id({}):
            object.__setattr__(self, 'metadata', self.metadata.copy())
            
        logger.debug(f"Created UserExecutionContext: user_id={self.user_id}, "
                    f"thread_id={self.thread_id}, run_id={self.run_id}, "
                    f"request_id={self.request_id}")
    
    def create_child_context(self, child_suffix: str) -> 'UserExecutionContext':
        """Create a child context for agent-specific execution.
        
        Args:
            child_suffix: Suffix to append to the run_id to create child context
            
        Returns:
            New UserExecutionContext with child-specific run_id
        """
        return UserExecutionContext(
            user_id=self.user_id,
            thread_id=self.thread_id,
            run_id=f"{self.run_id}_{child_suffix}",
            request_id=f"{self.request_id}_{child_suffix}",
            session_id=self.session_id,
            websocket_client_id=self.websocket_client_id,
            created_at=datetime.now(timezone.utc),
            metadata=self.metadata.copy() if self.metadata else {}
        )
    
    def _validate_required_ids(self) -> None:
        """Validate that all required IDs are present and non-empty."""
        required_fields = ['user_id', 'thread_id', 'run_id', 'request_id']
        
        for field_name in required_fields:
            value = getattr(self, field_name)
            if not value or not isinstance(value, str) or not value.strip():
                raise InvalidContextError(
                    f"Required field '{field_name}' must be a non-empty string, "
                    f"got: {value!r}"
                )
    
    def _validate_no_placeholder_values(self) -> None:
        """Validate that no IDs contain dangerous placeholder or default values."""
        # Only forbid exact matches that clearly indicate uninitialized state
        dangerous_exact_values = {
            'registry', 'placeholder', 'default', 'temp', 
            'none', 'null', 'undefined', '0', '1', 'xxx', 'yyy',
            'example'
        }
        
        # Patterns that indicate uninitialized or template values (prefix matches only)
        dangerous_patterns = [
            'placeholder_',
            'registry_',
            'default_',
            'temp_'
        ]
        
        id_fields = ['user_id', 'thread_id', 'run_id', 'request_id']
        
        for field_name in id_fields:
            value = getattr(self, field_name)
            value_lower = value.lower()
            
            # Check exact dangerous values
            if value_lower in dangerous_exact_values:
                raise InvalidContextError(
                    f"Field '{field_name}' contains forbidden placeholder value: "
                    f"{value!r}"
                )
            
            # Check dangerous patterns (prefix matches only, for short values)
            for pattern in dangerous_patterns:
                if value_lower.startswith(pattern) and len(value) < 20:
                    raise InvalidContextError(
                        f"Field '{field_name}' appears to contain placeholder pattern: "
                        f"{value!r}"
                    )
    
    
    def _validate_metadata(self) -> None:
        """Validate metadata structure."""
        if not isinstance(self.metadata, dict):
            raise InvalidContextError(
                f"metadata must be a dictionary, got: {type(self.metadata)}"
            )
        
        # Check for reserved keys that might cause conflicts
        reserved_keys = {'user_id', 'thread_id', 'run_id', 'request_id', 'created_at'}
        conflicting_keys = set(self.metadata.keys()) & reserved_keys
        if conflicting_keys:
            raise InvalidContextError(
                f"metadata contains reserved keys: {conflicting_keys}"
            )
    
    @classmethod
    def from_request(
        cls,
        user_id: str,
        thread_id: str,
        run_id: str,
        request_id: Optional[str] = None,
        db_session: Optional[AsyncSession] = None,
        websocket_client_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'UserExecutionContext':
        """Factory method to create context from request parameters.
        
        Args:
            user_id: User identifier from request
            thread_id: Thread identifier from request
            run_id: Run identifier from request
            request_id: Optional request identifier (auto-generated if None)
            db_session: Optional database session
            websocket_client_id: Optional WebSocket client ID
            metadata: Optional metadata dictionary
            
        Returns:
            New UserExecutionContext instance
            
        Raises:
            InvalidContextError: If any required parameters are invalid
        """
        return cls(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            request_id=request_id or str(uuid.uuid4()),
            db_session=db_session,
            websocket_client_id=websocket_client_id,
            metadata=metadata or {}
        )
    
    def create_child_context(
        self,
        operation_name: str,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> 'UserExecutionContext':
        """Create a child context for sub-operations.
        
        Child contexts inherit all parent data but get a new request_id and
        enhanced metadata to track the operation hierarchy.
        
        Args:
            operation_name: Name of the sub-operation
            additional_metadata: Additional metadata for the child context
            
        Returns:
            New UserExecutionContext for the child operation
            
        Raises:
            InvalidContextError: If operation_name is invalid
        """
        if not operation_name or not isinstance(operation_name, str):
            raise InvalidContextError("operation_name must be a non-empty string")
        
        # Build enhanced metadata
        child_metadata = self.metadata.copy()
        child_metadata.update({
            'parent_request_id': self.request_id,
            'operation_name': operation_name,
            'operation_depth': child_metadata.get('operation_depth', 0) + 1
        })
        
        if additional_metadata:
            child_metadata.update(additional_metadata)
        
        return UserExecutionContext(
            user_id=self.user_id,
            thread_id=self.thread_id,
            run_id=self.run_id,
            request_id=str(uuid.uuid4()),
            db_session=self.db_session,
            websocket_client_id=self.websocket_client_id,
            metadata=child_metadata
        )
    
    def with_db_session(self, db_session: AsyncSession) -> 'UserExecutionContext':
        """Create a new context with a database session.
        
        Since the context is immutable, this creates a new instance with
        the provided session while preserving all other data.
        
        Args:
            db_session: Database session to attach
            
        Returns:
            New UserExecutionContext with the database session
        """
        return UserExecutionContext(
            user_id=self.user_id,
            thread_id=self.thread_id,
            run_id=self.run_id,
            request_id=self.request_id,
            db_session=db_session,
            websocket_client_id=self.websocket_client_id,
            created_at=self.created_at,
            metadata=self.metadata.copy()
        )
    
    def with_websocket_connection(self, connection_id: str) -> 'UserExecutionContext':
        """Create a new context with a WebSocket connection ID.
        
        Args:
            connection_id: WebSocket connection identifier
            
        Returns:
            New UserExecutionContext with the WebSocket connection ID
        """
        return UserExecutionContext(
            user_id=self.user_id,
            thread_id=self.thread_id,
            run_id=self.run_id,
            request_id=self.request_id,
            db_session=self.db_session,
            websocket_client_id=connection_id,
            created_at=self.created_at,
            metadata=self.metadata.copy()
        )
    
    def verify_isolation(self) -> bool:
        """Verify that this context has proper isolation (no shared references).
        
        This method checks that the context doesn't contain any mutable objects
        that could be shared between requests, which would break isolation.
        
        Returns:
            True if context is properly isolated
            
        Raises:
            InvalidContextError: If shared references are detected
        """
        # Check that metadata is a separate dict instance
        if hasattr(self.metadata, '__dict__') and id(self.metadata) in _SHARED_OBJECTS:
            raise InvalidContextError("metadata contains shared object references")
        
        # Verify all string IDs are separate instances (basic check)
        id_values = [self.user_id, self.thread_id, self.run_id, self.request_id]
        unique_ids = set(id_values)
        if len(unique_ids) < len(id_values):
            logger.warning("Context contains duplicate ID values - this may indicate improper usage")
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for serialization/logging.
        
        Note: Excludes db_session as it's not serializable.
        
        Returns:
            Dictionary representation of the context
        """
        return {
            'user_id': self.user_id,
            'thread_id': self.thread_id,
            'run_id': self.run_id,
            'request_id': self.request_id,
            'websocket_client_id': self.websocket_client_id,
            'created_at': self.created_at.isoformat(),
            'metadata': self.metadata.copy(),
            'has_db_session': self.db_session is not None
        }
    
    def get_correlation_id(self) -> str:
        """Get a correlation ID for logging and tracing.
        
        Returns:
            Formatted correlation ID combining key identifiers
        """
        return f"{self.user_id[:8]}:{self.thread_id[:8]}:{self.run_id[:8]}:{self.request_id[:8]}"


# Module-level set to track shared objects for isolation verification
_SHARED_OBJECTS = set()


def register_shared_object(obj: Any) -> None:
    """Register an object as shared to help detect isolation violations."""
    _SHARED_OBJECTS.add(id(obj))


def clear_shared_objects() -> None:
    """Clear the shared objects registry (primarily for testing)."""
    global _SHARED_OBJECTS
    _SHARED_OBJECTS.clear()


def validate_user_context(context: Any) -> UserExecutionContext:
    """Validate that an object is a proper UserExecutionContext.
    
    This function provides runtime validation that can be used at API boundaries
    or in functions that expect a UserExecutionContext.
    
    Args:
        context: Object to validate
        
    Returns:
        The validated UserExecutionContext
        
    Raises:
        TypeError: If context is not a UserExecutionContext
        InvalidContextError: If context is invalid
    """
    if not isinstance(context, UserExecutionContext):
        raise TypeError(
            f"Expected UserExecutionContext, got: {type(context)}"
        )
    
    # Additional runtime validation could be added here
    # The __post_init__ validation already runs during creation
    
    return context
