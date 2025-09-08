"""UserExecutionContext Service: Comprehensive Request Isolation and Context Management

This module provides the definitive UserExecutionContext implementation for proper
request isolation and session management across the entire Netra platform.

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) 
- Business Goal: Ensure complete request isolation and prevent data leakage
- Value Impact: Guarantees user data security, request traceability, and proper session management
- Revenue Impact: Prevents security breaches and enables audit trails for compliance

Key Features:
- Complete request isolation with immutable design
- Database session management and proper cleanup
- WebSocket connection routing for real-time updates
- Audit trail support for compliance and debugging
- Child context creation for sub-agent operations
- FastAPI integration with factory methods
- Comprehensive validation to prevent placeholder values

Architecture:
This implementation serves as the Single Source of Truth (SSOT) for user execution 
context across all services while maintaining complete isolation between concurrent
user requests.
"""

import uuid
import copy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union, TYPE_CHECKING
import logging
from contextlib import asynccontextmanager

from netra_backend.app.core.unified_id_manager import UnifiedIDManager
from netra_backend.app.logging_config import central_logger
from shared.isolated_environment import IsolatedEnvironment

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from fastapi import Request

logger = central_logger.get_logger(__name__)


class InvalidContextError(Exception):
    """Raised when UserExecutionContext contains invalid data."""
    pass


class ContextIsolationError(Exception):
    """Raised when context isolation is violated."""
    pass


@dataclass(frozen=True)
class UserExecutionContext:
    """Comprehensive immutable context for complete request isolation.
    
    This class is the definitive implementation for user execution context,
    designed to prevent any form of data leakage between concurrent requests
    while providing complete audit trail support.
    
    **BACKWARD COMPATIBILITY LAYER:**
    This implementation includes full backward compatibility with the supervisor
    implementation patterns, supporting both interface styles:
    
    Services Style (Enhanced):
    - separate `agent_context` and `audit_metadata` dictionaries
    - `websocket_client_id` for WebSocket routing
    - comprehensive security validation (20 forbidden patterns)
    - enhanced operation depth tracking and hierarchical contexts
    
    Supervisor Style (Compatibility):
    - unified `metadata` property (merges agent_context + audit_metadata)
    - `websocket_connection_id` property alias for `websocket_client_id`
    - `from_request_supervisor` factory method with single metadata parameter
    - default operation_depth=0 and parent_request_id=None for compatibility
    
    Key Design Principles:
    - Immutable after creation (frozen=True) - prevents accidental modification
    - No global state references - everything passed explicitly
    - Complete validation - fails fast on invalid or placeholder values
    - Database session isolation - each context has its own session
    - WebSocket routing - direct connection to user's real-time channel
    - Audit trail support - comprehensive tracking for compliance
    - Child context creation - proper hierarchical operation tracking
    
    Attributes:
        user_id: Unique identifier for the user making the request
        thread_id: Unique identifier for the conversation thread
        run_id: Unique identifier for this specific execution run
        request_id: Unique identifier for this specific request (auto-generated)
        db_session: Optional database session for request-scoped operations
        websocket_client_id: Optional WebSocket connection ID for real-time updates
        created_at: Timestamp when context was created (UTC)
        agent_context: Dictionary for agent-specific data and state
        audit_metadata: Dictionary for audit trail and compliance tracking
        operation_depth: Depth level for nested operations (0 for root requests)
        parent_request_id: Request ID of parent context (for sub-operations)
    """
    
    # Required core identifiers
    user_id: str
    thread_id: str  
    run_id: str
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Session and connection management
    db_session: Optional['AsyncSession'] = field(default=None, repr=False, compare=False)
    websocket_client_id: Optional[str] = field(default=None)
    
    # Timestamp and metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    agent_context: Dict[str, Any] = field(default_factory=dict)
    audit_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Hierarchical operation tracking
    operation_depth: int = field(default=0)
    parent_request_id: Optional[str] = field(default=None)
    
    def __post_init__(self):
        """Comprehensive validation after initialization."""
        self._validate_required_fields()
        self._validate_no_placeholder_values()
        self._validate_id_consistency()
        self._validate_metadata_isolation()
        self._initialize_audit_trail()
        
        logger.debug(
            f"Created UserExecutionContext: user_id={self.user_id[:8]}..., "
            f"thread_id={self.thread_id}, run_id={self.run_id}, "
            f"request_id={self.request_id}, depth={self.operation_depth}"
        )
    
    def _validate_required_fields(self) -> None:
        """Validate that all required IDs are present and properly formatted."""
        required_fields = {
            'user_id': self.user_id,
            'thread_id': self.thread_id,
            'run_id': self.run_id,
            'request_id': self.request_id
        }
        
        for field_name, value in required_fields.items():
            if not value or not isinstance(value, str) or not value.strip():
                raise InvalidContextError(
                    f"Required field '{field_name}' must be a non-empty string, "
                    f"got: {value!r}"
                )
            
            # Validate UUID format for request_id (only if not auto-generated)
            if field_name == 'request_id':
                try:
                    uuid.UUID(value)
                except ValueError:
                    # Allow non-UUID values for testing, but log a warning
                    logger.warning(
                        f"request_id '{value}' is not a valid UUID. "
                        "Consider using proper UUID format for production."
                    )
    
    def _validate_no_placeholder_values(self) -> None:
        """Validate that no IDs contain dangerous placeholder or template values."""
        # Get environment instance for test detection
        env = IsolatedEnvironment()
        is_test_environment = env.is_test()
        
        # Forbidden exact values (case-insensitive)
        forbidden_exact_values = {
            'registry', 'placeholder', 'default', 'temp', 'none', 'null', 
            'undefined', '0', '1', 'xxx', 'yyy', 'example', 'test', 'demo',
            'sample', 'template', 'mock', 'fake', 'dummy'
        }
        
        # Forbidden prefix patterns for short values (< 20 chars)
        forbidden_patterns = [
            'placeholder_', 'registry_', 'default_', 'temp_',
            'example_', 'demo_', 'sample_', 'template_', 'mock_', 'fake_'
        ]
        
        # Only add 'test_' pattern restriction for non-test environments
        if not is_test_environment:
            forbidden_patterns.append('test_')
        else:
            logger.debug(
                f"Test environment detected - allowing test_ patterns for context creation. "
                f"user_id: {self.user_id[:12]}..., environment: {env.get_environment_name()}"
            )
        
        id_fields = ['user_id', 'thread_id', 'run_id', 'request_id']
        
        for field_name in id_fields:
            value = getattr(self, field_name)
            value_lower = value.lower()
            
            # Check forbidden exact values
            if value_lower in forbidden_exact_values:
                raise InvalidContextError(
                    f"Field '{field_name}' contains forbidden placeholder value: "
                    f"{value!r}. This prevents proper request isolation."
                )
            
            # Check forbidden patterns for short values
            if len(value) < 20:
                for pattern in forbidden_patterns:
                    if value_lower.startswith(pattern):
                        raise InvalidContextError(
                            f"Field '{field_name}' appears to contain placeholder pattern: "
                            f"{value!r}. This indicates improper context initialization."
                        )
    
    def _validate_id_consistency(self) -> None:
        """Validate ID consistency and format compliance."""
        # Validate run_id format using UnifiedIDManager
        if hasattr(UnifiedIDManager, 'validate_run_id'):
            if not UnifiedIDManager.validate_run_id(self.run_id):
                logger.warning(
                    f"run_id '{self.run_id}' does not follow expected format. "
                    "Consider using UnifiedIDManager.generate_run_id() for consistency."
                )
        
        # Validate thread_id consistency with run_id if extractable
        if hasattr(UnifiedIDManager, 'extract_thread_id'):
            extracted_thread_id = UnifiedIDManager.extract_thread_id(self.run_id)
            if extracted_thread_id and extracted_thread_id != self.thread_id:
                logger.warning(
                    f"Thread ID mismatch: run_id contains '{extracted_thread_id}' "
                    f"but thread_id is '{self.thread_id}'. This may indicate "
                    "inconsistent ID generation."
                )
    
    def _validate_metadata_isolation(self) -> None:
        """Ensure metadata dictionaries are properly isolated."""
        # Validate agent_context structure
        if not isinstance(self.agent_context, dict):
            raise InvalidContextError(
                f"agent_context must be a dictionary, got: {type(self.agent_context)}"
            )
        
        if not isinstance(self.audit_metadata, dict):
            raise InvalidContextError(
                f"audit_metadata must be a dictionary, got: {type(self.audit_metadata)}"
            )
        
        # Check for reserved keys that might cause conflicts
        reserved_keys = {
            'user_id', 'thread_id', 'run_id', 'request_id', 'created_at',
            'db_session', 'websocket_client_id'
        }
        
        for metadata_dict, dict_name in [
            (self.agent_context, 'agent_context'),
            (self.audit_metadata, 'audit_metadata')
        ]:
            conflicting_keys = set(metadata_dict.keys()) & reserved_keys
            if conflicting_keys:
                raise InvalidContextError(
                    f"{dict_name} contains reserved keys: {conflicting_keys}"
                )
        
        # Ensure metadata isolation by creating deep copies
        object.__setattr__(self, 'agent_context', copy.deepcopy(self.agent_context))
        object.__setattr__(self, 'audit_metadata', copy.deepcopy(self.audit_metadata))
    
    def _initialize_audit_trail(self) -> None:
        """Initialize audit trail metadata."""
        audit_data = self.audit_metadata.copy()
        audit_data.update({
            'context_created_at': self.created_at.isoformat(),
            'context_version': '1.0',
            'isolation_verified': True,
            'operation_depth': self.operation_depth
        })
        
        if self.parent_request_id:
            audit_data['parent_request_id'] = self.parent_request_id
        
        object.__setattr__(self, 'audit_metadata', audit_data)
    
    @classmethod
    def from_request(
        cls,
        user_id: str,
        thread_id: str,
        run_id: str,
        request_id: Optional[str] = None,
        db_session: Optional['AsyncSession'] = None,
        websocket_client_id: Optional[str] = None,
        agent_context: Optional[Dict[str, Any]] = None,
        audit_metadata: Optional[Dict[str, Any]] = None
    ) -> 'UserExecutionContext':
        """Factory method to create context from request parameters.
        
        This is the primary factory method for creating UserExecutionContext
        instances from incoming requests, particularly FastAPI requests.
        
        Args:
            user_id: User identifier from authentication
            thread_id: Thread identifier from request
            run_id: Run identifier from request
            request_id: Optional request identifier (auto-generated if None)
            db_session: Optional database session for the request
            websocket_client_id: Optional WebSocket connection ID
            agent_context: Optional agent-specific context data
            audit_metadata: Optional audit and compliance metadata
            
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
            agent_context=agent_context or {},
            audit_metadata=audit_metadata or {}
        )
    
    @classmethod 
    def from_fastapi_request(
        cls,
        request: 'Request',
        user_id: str,
        thread_id: str,
        run_id: str,
        db_session: Optional['AsyncSession'] = None,
        websocket_client_id: Optional[str] = None
    ) -> 'UserExecutionContext':
        """Factory method to create context from FastAPI Request object.
        
        Extracts relevant information from FastAPI request including
        headers for tracing and audit purposes.
        
        Args:
            request: FastAPI Request object
            user_id: User identifier from authentication
            thread_id: Thread identifier
            run_id: Run identifier
            db_session: Optional database session
            websocket_client_id: Optional WebSocket connection ID
            
        Returns:
            New UserExecutionContext instance
            
        Raises:
            InvalidContextError: If required data is missing or invalid
        """
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Extract audit information from request
        audit_metadata = {
            'client_ip': getattr(request.client, 'host', 'unknown') if request.client else 'unknown',
            'user_agent': request.headers.get('user-agent', 'unknown'),
            'method': request.method,
            'url': str(request.url),
            'content_type': request.headers.get('content-type', 'unknown')
        }
        
        # Add tracing headers if present
        trace_headers = ['x-request-id', 'x-correlation-id', 'x-trace-id']
        for header in trace_headers:
            if header in request.headers:
                audit_metadata[header.replace('-', '_')] = request.headers[header]
        
        return cls(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            request_id=request_id,
            db_session=db_session,
            websocket_client_id=websocket_client_id,
            audit_metadata=audit_metadata
        )
    
    def create_child_context(
        self,
        operation_name: str,
        additional_agent_context: Optional[Dict[str, Any]] = None,
        additional_audit_metadata: Optional[Dict[str, Any]] = None
    ) -> 'UserExecutionContext':
        """Create a child context for sub-operations with proper hierarchy tracking.
        
        Child contexts inherit all parent data but receive a new request_id and
        enhanced metadata to track the operation hierarchy. This ensures proper
        isolation while maintaining audit trail continuity.
        
        Args:
            operation_name: Name of the sub-operation (e.g., 'data_analysis', 'report_generation')
            additional_agent_context: Additional agent-specific context data
            additional_audit_metadata: Additional audit metadata
            
        Returns:
            New UserExecutionContext for the child operation
            
        Raises:
            InvalidContextError: If operation_name is invalid or depth limit exceeded
        """
        if not operation_name or not isinstance(operation_name, str) or not operation_name.strip():
            raise InvalidContextError("operation_name must be a non-empty string")
        
        # Prevent excessive nesting depth (protection against infinite recursion)
        max_depth = 10
        if self.operation_depth >= max_depth:
            raise InvalidContextError(
                f"Maximum operation depth ({max_depth}) exceeded. "
                f"Current depth: {self.operation_depth}"
            )
        
        # Build enhanced agent context with deep copy for isolation
        child_agent_context = copy.deepcopy(self.agent_context)
        child_agent_context.update({
            'parent_operation': self.agent_context.get('operation_name', 'root'),
            'operation_name': operation_name,
            'operation_depth': self.operation_depth + 1
        })
        
        if additional_agent_context:
            child_agent_context.update(additional_agent_context)
        
        # Build enhanced audit metadata with deep copy for isolation
        child_audit_metadata = copy.deepcopy(self.audit_metadata)
        child_audit_metadata.update({
            'parent_request_id': self.request_id,
            'operation_name': operation_name,
            'operation_depth': self.operation_depth + 1,
            'child_created_at': datetime.now(timezone.utc).isoformat()
        })
        
        if additional_audit_metadata:
            child_audit_metadata.update(additional_audit_metadata)
        
        return UserExecutionContext(
            user_id=self.user_id,
            thread_id=self.thread_id,
            run_id=self.run_id,
            request_id=str(uuid.uuid4()),
            db_session=self.db_session,
            websocket_client_id=self.websocket_client_id,
            created_at=datetime.now(timezone.utc),
            agent_context=child_agent_context,
            audit_metadata=child_audit_metadata,
            operation_depth=self.operation_depth + 1,
            parent_request_id=self.request_id
        )
    
    def with_db_session(self, db_session: 'AsyncSession') -> 'UserExecutionContext':
        """Create a new context with a database session attached.
        
        Since the context is immutable, this creates a new instance with
        the provided session while preserving all other data.
        
        Args:
            db_session: Database session to attach
            
        Returns:
            New UserExecutionContext with the database session
            
        Raises:
            InvalidContextError: If db_session is None or invalid
        """
        if db_session is None:
            raise InvalidContextError("db_session cannot be None")
        
        return UserExecutionContext(
            user_id=self.user_id,
            thread_id=self.thread_id,
            run_id=self.run_id,
            request_id=self.request_id,
            db_session=db_session,
            websocket_client_id=self.websocket_client_id,
            created_at=self.created_at,
            agent_context=copy.deepcopy(self.agent_context),
            audit_metadata=copy.deepcopy(self.audit_metadata),
            operation_depth=self.operation_depth,
            parent_request_id=self.parent_request_id
        )
    
    def with_websocket_connection(self, connection_id: str) -> 'UserExecutionContext':
        """Create a new context with a WebSocket connection ID.
        
        Args:
            connection_id: WebSocket connection identifier
            
        Returns:
            New UserExecutionContext with the WebSocket connection ID
            
        Raises:
            InvalidContextError: If connection_id is invalid
        """
        if not connection_id or not isinstance(connection_id, str):
            raise InvalidContextError("connection_id must be a non-empty string")
        
        return UserExecutionContext(
            user_id=self.user_id,
            thread_id=self.thread_id,
            run_id=self.run_id,
            request_id=self.request_id,
            db_session=self.db_session,
            websocket_client_id=connection_id,
            created_at=self.created_at,
            agent_context=copy.deepcopy(self.agent_context),
            audit_metadata=copy.deepcopy(self.audit_metadata),
            operation_depth=self.operation_depth,
            parent_request_id=self.parent_request_id
        )
    
    def with_websocket_connection_supervisor(self, connection_id: str) -> 'UserExecutionContext':
        """Supervisor-compatible method for WebSocket connection attachment.
        
        This is an alias for `with_websocket_connection` to maintain compatibility
        with supervisor implementation naming patterns.
        
        Args:
            connection_id: WebSocket connection identifier
            
        Returns:
            New UserExecutionContext with the WebSocket connection ID
            
        Raises:
            InvalidContextError: If connection_id is invalid
        """
        return self.with_websocket_connection(connection_id)
    
    def verify_isolation(self) -> bool:
        """Verify that this context has proper isolation from other requests.
        
        This method performs comprehensive checks to ensure the context doesn't
        contain any shared references that could lead to data leakage between
        concurrent requests.
        
        Returns:
            True if context is properly isolated
            
        Raises:
            ContextIsolationError: If isolation violations are detected
        """
        # Check metadata isolation
        if hasattr(self.agent_context, '__dict__'):
            if id(self.agent_context) in _SHARED_OBJECT_REGISTRY:
                raise ContextIsolationError(
                    "agent_context contains shared object references"
                )
        
        if hasattr(self.audit_metadata, '__dict__'):
            if id(self.audit_metadata) in _SHARED_OBJECT_REGISTRY:
                raise ContextIsolationError(
                    "audit_metadata contains shared object references"
                )
        
        # Verify all string IDs are unique within this context
        id_values = [self.user_id, self.thread_id, self.run_id, self.request_id]
        unique_ids = set(id_values)
        if len(unique_ids) < len(id_values):
            logger.warning(
                f"Context contains duplicate ID values: {id_values}. "
                "This may indicate improper context usage."
            )
        
        # Verify database session is not shared if present
        if self.db_session is not None:
            session_id = id(self.db_session)
            if session_id in _SHARED_OBJECT_REGISTRY:
                raise ContextIsolationError(
                    "Database session is shared between contexts"
                )
        
        logger.debug(f"Context isolation verified for request_id={self.request_id}")
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for serialization and logging.
        
        Note: Excludes db_session as it's not serializable and may contains
        sensitive connection information.
        
        **Backward Compatibility:** Includes both services and supervisor field names
        for maximum compatibility.
        
        Returns:
            Dictionary representation of the context (safe for serialization)
        """
        return {
            # Core fields (both implementations)
            'user_id': self.user_id,
            'thread_id': self.thread_id,
            'run_id': self.run_id,
            'request_id': self.request_id,
            'created_at': self.created_at.isoformat(),
            'operation_depth': self.operation_depth,
            'parent_request_id': self.parent_request_id,
            'has_db_session': self.db_session is not None,
            
            # Services implementation fields
            'websocket_client_id': self.websocket_client_id,
            'agent_context': copy.deepcopy(self.agent_context),
            'audit_metadata': copy.deepcopy(self.audit_metadata),
            
            # Supervisor compatibility fields
            'websocket_connection_id': self.websocket_connection_id,  # Alias
            'metadata': self.metadata,  # Unified metadata
            
            # Additional compatibility info
            'implementation': 'services_with_supervisor_compatibility',
            'compatibility_layer_active': True
        }
    
    def get_correlation_id(self) -> str:
        """Get a correlation ID for logging and distributed tracing.
        
        Returns:
            Formatted correlation ID combining key identifiers
        """
        return f"{self.user_id[:8]}:{self.thread_id[:8]}:{self.run_id[:8]}:{self.request_id[:8]}"
    
    def get_audit_trail(self) -> Dict[str, Any]:
        """Get comprehensive audit trail for compliance and debugging.
        
        Returns:
            Complete audit trail with request lifecycle information
        """
        return {
            'correlation_id': self.get_correlation_id(),
            'user_id': self.user_id,
            'thread_id': self.thread_id,
            'run_id': self.run_id,
            'request_id': self.request_id,
            'created_at': self.created_at.isoformat(),
            'operation_depth': self.operation_depth,
            'parent_request_id': self.parent_request_id,
            'has_db_session': self.db_session is not None,
            'has_websocket': self.websocket_client_id is not None,
            'audit_metadata': copy.deepcopy(self.audit_metadata),
            'context_age_seconds': (datetime.now(timezone.utc) - self.created_at).total_seconds()
        }
    
    # ============================================================================
    # BACKWARD COMPATIBILITY LAYER FOR SUPERVISOR IMPLEMENTATION PATTERNS
    # ============================================================================
    
    @property
    def websocket_connection_id(self) -> Optional[str]:
        """Backward compatibility property mapping to websocket_client_id.
        
        The supervisor implementation used `websocket_connection_id`, while
        the services implementation uses `websocket_client_id`. This property
        provides seamless compatibility.
        
        Returns:
            WebSocket connection ID (same as websocket_client_id)
        """
        return self.websocket_client_id
    
    @property 
    def metadata(self) -> Dict[str, Any]:
        """Backward compatibility property merging agent_context and audit_metadata.
        
        The supervisor implementation used a single `metadata` dictionary, while
        the services implementation uses separate `agent_context` and `audit_metadata`.
        This property merges both for backward compatibility.
        
        **Merge Priority:** audit_metadata values override agent_context values
        for any conflicting keys (audit data takes precedence).
        
        Returns:
            Merged dictionary containing all context and audit metadata
        """
        merged = copy.deepcopy(self.agent_context)
        merged.update(self.audit_metadata)  # Audit metadata takes precedence
        return merged
    
    @classmethod
    def from_request_supervisor(
        cls,
        user_id: str,
        thread_id: str,
        run_id: str,
        request_id: Optional[str] = None,
        db_session: Optional['AsyncSession'] = None,
        websocket_connection_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'UserExecutionContext':
        """Supervisor-compatible factory method with single metadata parameter.
        
        This factory method provides full backward compatibility with the supervisor
        implementation's interface, accepting a single metadata dictionary that gets
        intelligently split into agent_context and audit_metadata.
        
        **Metadata Split Logic:**
        - Keys containing 'audit', 'compliance', 'trace', 'log' → audit_metadata
        - Keys containing 'agent', 'operation', 'workflow' → agent_context  
        - Special supervisor fields (operation_depth, parent_request_id) → audit_metadata
        - All other keys → agent_context (default)
        
        Args:
            user_id: User identifier from authentication
            thread_id: Thread identifier from request
            run_id: Run identifier from request
            request_id: Optional request identifier (auto-generated if None)
            db_session: Optional database session for the request
            websocket_connection_id: Optional WebSocket connection ID (supervisor field name)
            metadata: Optional unified metadata dictionary (supervisor style)
            
        Returns:
            New UserExecutionContext instance with metadata properly split
            
        Raises:
            InvalidContextError: If any required parameters are invalid
        """
        # Handle metadata splitting for backward compatibility
        agent_context = {}
        audit_metadata = {}
        
        if metadata:
            # Define audit-related keys that should go to audit_metadata
            audit_keywords = {
                'audit', 'compliance', 'trace', 'log', 'parent_request_id',
                'operation_depth', 'created_at', 'context_', 'client_ip',
                'user_agent', 'method', 'url', 'content_type'
            }
            
            # Define agent-related keys that should go to agent_context
            agent_keywords = {
                'agent', 'operation_name', 'workflow', 'execution', 'state',
                'parent_operation'
            }
            
            for key, value in metadata.items():
                key_lower = key.lower()
                
                # Check if key should go to audit_metadata
                if any(keyword in key_lower for keyword in audit_keywords):
                    audit_metadata[key] = value
                # Check if key should go to agent_context
                elif any(keyword in key_lower for keyword in agent_keywords):
                    agent_context[key] = value
                else:
                    # Default to agent_context for unknown keys
                    agent_context[key] = value
        
        # Set default values for supervisor compatibility
        if 'operation_depth' not in audit_metadata:
            audit_metadata['operation_depth'] = 0
        if 'parent_request_id' not in audit_metadata:
            audit_metadata['parent_request_id'] = None
            
        # Extract operation_depth and parent_request_id for constructor
        operation_depth = audit_metadata.get('operation_depth', 0)
        parent_request_id = audit_metadata.get('parent_request_id')
        
        # Remove from audit_metadata to avoid duplication (they're constructor params)
        audit_metadata_cleaned = {k: v for k, v in audit_metadata.items() 
                                  if k not in ('operation_depth', 'parent_request_id')}
        
        return cls(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            request_id=request_id or str(uuid.uuid4()),
            db_session=db_session,
            websocket_client_id=websocket_connection_id,  # Map supervisor field name
            agent_context=agent_context,
            audit_metadata=audit_metadata_cleaned,
            operation_depth=operation_depth,
            parent_request_id=parent_request_id
        )
    
    def create_child_context_supervisor(
        self,
        operation_name: str,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> 'UserExecutionContext':
        """Supervisor-compatible child context creation method.
        
        This method provides backward compatibility with the supervisor implementation's
        child context creation interface, accepting a single additional_metadata parameter
        that gets merged with the parent's unified metadata.
        
        Args:
            operation_name: Name of the sub-operation (e.g., 'data_analysis', 'report_generation')
            additional_metadata: Additional unified metadata for the child context (supervisor style)
            
        Returns:
            New UserExecutionContext for the child operation
            
        Raises:
            InvalidContextError: If operation_name is invalid or depth limit exceeded
        """
        if not operation_name or not isinstance(operation_name, str) or not operation_name.strip():
            raise InvalidContextError("operation_name must be a non-empty string")
        
        # Prevent excessive nesting depth
        max_depth = 10
        if self.operation_depth >= max_depth:
            raise InvalidContextError(
                f"Maximum operation depth ({max_depth}) exceeded. "
                f"Current depth: {self.operation_depth}"
            )
        
        # Start with parent's unified metadata (supervisor style)
        child_metadata = self.metadata.copy()
        child_metadata.update({
            'parent_request_id': self.request_id,
            'operation_name': operation_name,
            'operation_depth': self.operation_depth + 1
        })
        
        if additional_metadata:
            child_metadata.update(additional_metadata)
        
        # Use the supervisor factory method to handle metadata splitting
        return self.from_request_supervisor(
            user_id=self.user_id,
            thread_id=self.thread_id,
            run_id=self.run_id,
            request_id=str(uuid.uuid4()),
            db_session=self.db_session,
            websocket_connection_id=self.websocket_client_id,
            metadata=child_metadata
        )
    
    def to_execution_context(self) -> 'ExecutionContext':
        """Convert to legacy ExecutionContext for backwards compatibility.
        
        This method provides a bridge to the existing ExecutionContext system
        while we migrate to the new UserExecutionContext pattern.
        
        Returns:
            ExecutionContext instance compatible with existing agent infrastructure
        """
        from netra_backend.app.agents.base.interface import ExecutionContext
        from netra_backend.app.agents.state import DeepAgentState
        
        # Create minimal state for compatibility
        state = DeepAgentState()
        if hasattr(state, 'chat_thread_id'):
            state.chat_thread_id = self.thread_id
        
        # Build metadata for ExecutionContext
        execution_metadata = {}
        execution_metadata.update(self.agent_context)
        execution_metadata.update({
            'user_execution_context_id': self.request_id,
            'operation_depth': self.operation_depth,
            'websocket_client_id': self.websocket_client_id
        })
        
        return ExecutionContext(
            run_id=self.run_id,
            agent_name=self.agent_context.get('agent_name', 'unknown'),
            state=state,
            user_id=self.user_id,
            thread_id=self.thread_id,
            correlation_id=self.get_correlation_id(),
            metadata=execution_metadata,
            start_time=self.created_at
        )


# Module-level registry for tracking shared objects to detect isolation violations
_SHARED_OBJECT_REGISTRY = set()


def register_shared_object(obj: Any) -> None:
    """Register an object as potentially shared for isolation validation.
    
    This function helps detect when objects are improperly shared between
    different UserExecutionContext instances, which could lead to data leakage.
    
    Args:
        obj: Object to register as potentially shared
    """
    _SHARED_OBJECT_REGISTRY.add(id(obj))


def clear_shared_object_registry() -> None:
    """Clear the shared object registry (primarily for testing)."""
    global _SHARED_OBJECT_REGISTRY
    _SHARED_OBJECT_REGISTRY.clear()


def validate_user_context(context: Any) -> UserExecutionContext:
    """Runtime validation that an object is a proper UserExecutionContext.
    
    This function provides runtime validation that can be used at API boundaries
    or in functions that expect a UserExecutionContext.
    
    Args:
        context: Object to validate
        
    Returns:
        The validated UserExecutionContext
        
    Raises:
        TypeError: If context is not a UserExecutionContext
        InvalidContextError: If context validation fails
    """
    if not isinstance(context, UserExecutionContext):
        raise TypeError(
            f"Expected UserExecutionContext, got: {type(context)}"
        )
    
    # Verify isolation on each validation
    context.verify_isolation()
    
    return context


@asynccontextmanager
async def managed_user_context(
    context: UserExecutionContext,
    cleanup_db_session: bool = True
):
    """Async context manager for UserExecutionContext with automatic cleanup.
    
    This context manager ensures proper cleanup of resources associated with
    the UserExecutionContext, particularly database sessions.
    
    Args:
        context: UserExecutionContext to manage
        cleanup_db_session: Whether to close db_session on exit
        
    Yields:
        The managed UserExecutionContext
        
    Example:
        async with managed_user_context(context) as ctx:
            # Use ctx for operations
            result = await some_agent.execute(ctx)
        # Resources are automatically cleaned up
    """
    try:
        logger.debug(f"Managing context: {context.get_correlation_id()}")
        yield context
    except Exception as e:
        logger.error(
            f"Exception in managed context {context.get_correlation_id()}: {e}",
            exc_info=True
        )
        raise
    finally:
        # Cleanup database session if requested
        if cleanup_db_session and context.db_session:
            try:
                await context.db_session.close()
                logger.debug(f"Closed database session for context {context.request_id}")
            except Exception as e:
                logger.warning(f"Error closing database session: {e}")


# ============================================================================
# FACTORY CLASS FOR INTEGRATION TEST COMPATIBILITY
# ============================================================================

class UserContextFactory:
    """Factory class for creating UserExecutionContext instances.
    
    This factory provides a convenient interface for integration tests
    and other components that need to create UserExecutionContext instances
    with consistent patterns.
    """
    
    @staticmethod
    def create_context(
        user_id: str,
        thread_id: str,
        run_id: str,
        request_id: Optional[str] = None,
        websocket_client_id: Optional[str] = None
    ) -> UserExecutionContext:
        """Create a basic UserExecutionContext for testing."""
        return UserExecutionContext.from_request(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            request_id=request_id,
            websocket_client_id=websocket_client_id
        )
    
    @staticmethod
    def create_with_session(
        user_id: str,
        thread_id: str,
        run_id: str,
        db_session: 'AsyncSession',
        request_id: Optional[str] = None,
        websocket_client_id: Optional[str] = None
    ) -> UserExecutionContext:
        """Create a UserExecutionContext with database session."""
        context = UserExecutionContext.from_request(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            request_id=request_id,
            websocket_client_id=websocket_client_id
        )
        return context.with_db_session(db_session)


# Export all public classes and functions
__all__ = [
    'UserExecutionContext',
    'UserContextFactory',
    'InvalidContextError', 
    'ContextIsolationError',
    'validate_user_context',
    'managed_user_context',
    'register_shared_object',
    'clear_shared_object_registry'
]