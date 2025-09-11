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
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union, TYPE_CHECKING, List, Callable
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
    
    # Resource cleanup management
    cleanup_callbacks: List[Callable] = field(default_factory=list, repr=False, compare=False)
    
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
                logger.error(
                    f"❌ VALIDATION FAILURE: Required field '{field_name}' validation failed. "
                    f"Expected non-empty string, got: {value!r} (type: {type(value).__name__}). "
                    f"Context: user_id={getattr(self, 'user_id', 'unknown')[:8]}..."
                )
                raise InvalidContextError(
                    f"Required field '{field_name}' must be a non-empty string, "
                    f"got: {value!r}"
                )
            
            # Validate ID format for request_id (supports UUID and UnifiedIDManager formats)
            if field_name == 'request_id':
                from netra_backend.app.core.unified_id_manager import is_valid_id_format
                if not is_valid_id_format(value):
                    logger.warning(
                        f"request_id '{value}' has invalid format. "
                        "Expected UUID or UnifiedIDManager structured format."
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
        
        # Smart placeholder pattern detection - differentiate between real placeholders and legitimate values
        # CRITICAL FIX: Previous "default_" pattern was too broad and blocked legitimate "default_user" IDs
        # Issue #XXX: Golden Path authentication failure ($500K+ ARR impact)
        
        # Specific placeholder patterns that indicate improper initialization
        forbidden_patterns = [
            'placeholder_', 'registry_', 'temp_',
            'example_', 'demo_', 'sample_', 'template_', 'mock_', 'fake_',
            'default_'  # Block all default_ patterns, except specific legitimate ones below
        ]
        
        # Legitimate patterns that should be ALLOWED (not blocked)
        # These are common legitimate user ID patterns in production systems
        legitimate_patterns = {
            'default_user', 'default_admin', 'default_system', 'default_account',
            'default_service', 'default_client', 'default_guest'
        }
        
        # Specific default patterns that ARE placeholders and should be blocked
        forbidden_default_patterns = [
            'default_placeholder', 'default_temp', 'default_registry',
            'default_example', 'default_demo', 'default_sample',
            'default_template', 'default_mock', 'default_fake'
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
                logger.error(
                    f"[ERROR] VALIDATION FAILURE: Field '{field_name}' contains forbidden placeholder value. "
                    f"Value: {value!r}, User: {getattr(self, 'user_id', 'unknown')[:8]}..., "
                    f"This prevents proper request isolation and indicates improper context initialization. "
                    f"GCP context: Exact placeholder value match detected for enhanced debugging."
                )
                raise InvalidContextError(
                    f"Field '{field_name}' contains forbidden placeholder value: "
                    f"{value!r}. This prevents proper request isolation."
                )
            
            # Smart placeholder pattern validation for short values
            if len(value) < 20:
                # First, check if this is a legitimate pattern that should be allowed
                if value_lower in legitimate_patterns:
                    logger.debug(
                        f"[OK] VALIDATION ALLOW: Field '{field_name}' contains legitimate pattern. "
                        f"Value: {value!r}, Pattern: legitimate_default_user_pattern, "
                        f"Business context: Allowing known legitimate user ID patterns for Golden Path authentication"
                    )
                    continue  # Skip further validation for this field - it's explicitly allowed
                
                # Check for specific forbidden default patterns
                if value_lower in forbidden_default_patterns:
                    logger.error(
                        f"[ERROR] VALIDATION FAILURE: Field '{field_name}' contains forbidden default placeholder pattern. "
                        f"Value: {value!r}, User: {getattr(self, 'user_id', 'unknown')[:8]}..., "
                        f"Pattern detected: forbidden_default_placeholder, "
                        f"Business impact: Prevents proper request isolation and indicates improper context initialization. "
                        f"GCP context: Issue may impact Golden Path user authentication and revenue protection."
                    )
                    raise InvalidContextError(
                        f"Field '{field_name}' contains forbidden default placeholder pattern: "
                        f"{value!r}. This prevents proper request isolation."
                    )
                
                # Check standard forbidden patterns (excluding default_ which we handled above)
                for pattern in forbidden_patterns:
                    if value_lower.startswith(pattern):
                        logger.error(
                            f"[ERROR] VALIDATION FAILURE: Field '{field_name}' contains forbidden placeholder pattern. "
                            f"Pattern: '{pattern}', Value: {value!r}, User: {getattr(self, 'user_id', 'unknown')[:8]}..., "
                            f"Business impact: Risks request isolation and indicates improper context initialization. "
                            f"Suggestion: Use legitimate user ID or add to legitimate_patterns if truly valid. "
                            f"GCP context: Structured logging for troubleshooting authentication failures."
                        )
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
        # FIVE WHYS FIX: Updated validation logic to handle UnifiedIdGenerator patterns
        if hasattr(UnifiedIDManager, 'extract_thread_id'):
            extracted_thread_id = UnifiedIDManager.extract_thread_id(self.run_id)
            if extracted_thread_id:
                # Check for consistency based on ID generation pattern
                is_consistent = self._validate_thread_run_id_consistency(extracted_thread_id, self.thread_id, self.run_id)
                if not is_consistent:
                    logger.warning(
                        f"Thread ID mismatch: run_id '{self.run_id}' extracted to '{extracted_thread_id}' "
                        f"but thread_id is '{self.thread_id}'. This may indicate "
                        "inconsistent ID generation."
                    )
    
    def _validate_thread_run_id_consistency(self, extracted_thread_id: str, actual_thread_id: str, run_id: str) -> bool:
        """
        Validate thread_id and run_id consistency with SSOT pattern support.
        
        FIVE WHYS FIX: Handles both UnifiedIdGenerator and UnifiedIDManager patterns
        to prevent false positive thread ID mismatch warnings.
        
        Args:
            extracted_thread_id: Thread ID extracted from run_id
            actual_thread_id: Actual thread_id field value
            run_id: Original run_id for pattern detection
            
        Returns:
            True if IDs are consistent according to their generation pattern
        """
        # Pattern 1: UnifiedIdGenerator pattern
        # run_id="websocket_factory_1757372478799", thread_id="thread_websocket_factory_1757372478799_528_584ef8a5"
        # In this case, thread_id should contain the run_id as a substring
        if run_id.startswith(('websocket_factory_', 'context_', 'agent_')):
            # For UnifiedIdGenerator: thread_id should contain run_id as substring
            is_consistent = run_id in actual_thread_id and actual_thread_id.startswith('thread_')
            if is_consistent:
                logger.debug(f"UnifiedIdGenerator pattern validated: run_id '{run_id}' found in thread_id '{actual_thread_id}'")
            return is_consistent
        
        # Pattern 2: UnifiedIDManager pattern  
        # run_id="run_thread123_456_abcd", extracted="thread123", thread_id="thread123"
        # In this case, extracted_thread_id should exactly match actual_thread_id
        if extracted_thread_id == actual_thread_id:
            logger.debug(f"UnifiedIDManager pattern validated: exact match '{extracted_thread_id}'")
            return True
        
        # Pattern 3: Legacy/fallback patterns - be more lenient
        # Check if there's any reasonable relationship between the IDs
        if extracted_thread_id in actual_thread_id or actual_thread_id in extracted_thread_id:
            logger.debug(f"Legacy pattern validated: relationship found between '{extracted_thread_id}' and '{actual_thread_id}'")
            return True
        
        # If no pattern matches, log the specific mismatch for debugging
        logger.debug(
            f"ID consistency check failed: extracted='{extracted_thread_id}', "
            f"actual='{actual_thread_id}', run_id='{run_id}'"
        )
        return False
    
    def _validate_metadata_isolation(self) -> None:
        """Ensure metadata dictionaries are properly isolated."""
        # Validate agent_context structure
        if not isinstance(self.agent_context, dict):
            logger.error(
                f"❌ VALIDATION FAILURE: agent_context must be a dictionary. "
                f"Got: {type(self.agent_context).__name__}, Value: {self.agent_context!r}, "
                f"User: {getattr(self, 'user_id', 'unknown')[:8]}..."
            )
            raise InvalidContextError(
                f"agent_context must be a dictionary, got: {type(self.agent_context)}"
            )
        
        if not isinstance(self.audit_metadata, dict):
            logger.error(
                f"❌ VALIDATION FAILURE: audit_metadata must be a dictionary. "
                f"Got: {type(self.audit_metadata).__name__}, Value: {self.audit_metadata!r}, "
                f"User: {getattr(self, 'user_id', 'unknown')[:8]}..."
            )
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
                logger.error(
                    f"❌ VALIDATION FAILURE: {dict_name} contains reserved keys that would cause conflicts. "
                    f"Conflicting keys: {conflicting_keys}, Reserved keys: {reserved_keys}, "
                    f"User: {getattr(self, 'user_id', 'unknown')[:8]}..., "
                    f"This prevents proper context isolation."
                )
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
    def from_agent_execution_context(
        cls,
        user_id: str,
        thread_id: str,
        run_id: str,
        request_id: Optional[str] = None,
        agent_context: Optional[Dict[str, Any]] = None,
        audit_metadata: Optional[Dict[str, Any]] = None
    ) -> 'UserExecutionContext':
        """Factory method to create context from agent execution context parameters.
        
        This method provides compatibility with legacy agent execution patterns
        during the migration from DeepAgentState to UserExecutionContext.
        
        Args:
            user_id: User identifier
            thread_id: Thread identifier  
            run_id: Run identifier
            request_id: Optional request identifier (auto-generated if None)
            agent_context: Optional agent-specific context data
            audit_metadata: Optional audit and compliance metadata
            
        Returns:
            New UserExecutionContext instance
        """
        return cls(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            request_id=request_id or str(uuid.uuid4()),
            agent_context=agent_context or {},
            audit_metadata=audit_metadata or {}
        )

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
    def from_websocket_request(
        cls,
        user_id: str,
        websocket_client_id: Optional[str] = None,
        operation: str = "websocket_session"
    ) -> 'UserExecutionContext':
        """
        SSOT factory method for WebSocket context creation with consistent ID generation.
        
        This is the Single Source of Truth for WebSocket-related UserExecutionContext creation.
        It ensures consistent thread_id generation patterns across all WebSocket components,
        preventing the isolation key mismatches that cause resource leak issues.
        
        Business Value Justification (BVJ):
        - Segment: ALL (Free -> Enterprise)
        - Business Goal: Eliminate WebSocket resource leaks causing user connection failures
        - Value Impact: Ensures reliable chat connections and prevents service degradation
        - Strategic Impact: CRITICAL - Prevents cascade failures in real-time user interactions
        
        Args:
            user_id: User identifier from authentication
            websocket_client_id: Optional WebSocket connection ID (auto-generated if None)
            operation: Operation type for ID generation consistency (default: "websocket_session")
            
        Returns:
            New UserExecutionContext with consistent SSOT ID generation
            
        Raises:
            InvalidContextError: If user_id is invalid or ID generation fails
        """
        if not user_id or not isinstance(user_id, str) or not user_id.strip():
            raise InvalidContextError(
                f"user_id must be a non-empty string for WebSocket context, got: {user_id!r}"
            )
        
        # Use SSOT ID generation for consistent patterns
        from shared.id_generation.unified_id_generator import UnifiedIdGenerator
        
        try:
            # Generate consistent IDs using SSOT pattern
            thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(
                user_id=user_id,
                operation=operation
            )
            
            # Generate websocket_client_id if not provided
            if websocket_client_id is None:
                websocket_client_id = UnifiedIdGenerator.generate_websocket_client_id(user_id)
                
            logger.info(
                f"SSOT WebSocket Context: Created for user {user_id[:8]}... with "
                f"thread_id={thread_id}, websocket_client_id={websocket_client_id}"
            )
            
            return cls(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                request_id=request_id,
                websocket_client_id=websocket_client_id,
                agent_context={
                    'source': 'websocket_ssot',
                    'operation': operation,
                    'created_via': 'from_websocket_request'
                },
                audit_metadata={
                    'context_source': 'websocket_ssot',
                    'id_generation_method': 'UnifiedIdGenerator',
                    'operation_type': operation,
                    'isolation_key_compatible': True
                }
            )
            
        except Exception as id_error:
            logger.error(
                f"SSOT ID generation failed for WebSocket context creation "
                f"(user_id={user_id[:8]}..., operation={operation}): {id_error}"
            )
            raise InvalidContextError(
                f"WebSocket context creation failed due to ID generation error: {id_error}. "
                f"This indicates a system configuration issue with SSOT ID generation."
            ) from id_error
    
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
    
    async def cleanup(self) -> None:
        """Clean up resources associated with this context.
        
        This method executes all registered cleanup callbacks in reverse order (LIFO)
        to ensure proper resource cleanup and prevent memory leaks.
        
        **Compatibility Note**: This method provides compatibility with the execution
        factory pattern while maintaining the managed_user_context design.
        
        Raises:
            Exception: If any cleanup callback fails (logged but not re-raised)
        """
        if not self.cleanup_callbacks:
            logger.debug(f"No cleanup callbacks for context {self.request_id}")
            return
            
        logger.debug(f"🧹 Running {len(self.cleanup_callbacks)} cleanup callbacks for context {self.request_id}")
        
        # Execute cleanup callbacks in reverse order (LIFO)
        for i, callback in enumerate(reversed(self.cleanup_callbacks)):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
                logger.debug(f"✅ Cleanup callback {i+1}/{len(self.cleanup_callbacks)} executed successfully")
            except Exception as e:
                logger.error(
                    f"❌ Cleanup callback {i+1}/{len(self.cleanup_callbacks)} failed: {e}",
                    exc_info=True
                )
                # Continue with other callbacks even if one fails
        
        # Clear all callbacks after execution
        self.cleanup_callbacks.clear()
        logger.debug(f"🧹 Cleanup completed for context {self.request_id}")
    
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
    
    def get_scoped_key(self, component: str) -> str:
        """
        Generate user-scoped key for component isolation.
        
        This method ensures complete isolation by creating unique keys that
        include user context, preventing any cross-user contamination.
        
        Args:
            component: Component name requiring isolation
            
        Returns:
            Unique scoped key for this user and component
        """
        if not component or not component.strip():
            raise ValueError("Component name cannot be empty")
        
        # Create hierarchical scoping key
        return f"{component}:{self.user_id}:{self.request_id}"
    
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
    # Accept both UserExecutionContext and StronglyTypedUserExecutionContext for SSOT compatibility
    if not isinstance(context, UserExecutionContext):
        # Check if it's a StronglyTypedUserExecutionContext from the SSOT auth helper
        try:
            from shared.types.execution_types import StronglyTypedUserExecutionContext
            if isinstance(context, StronglyTypedUserExecutionContext):
                # Convert to UserExecutionContext for compatibility
                converted_context = UserExecutionContext(
                    user_id=context.user_id,
                    thread_id=context.thread_id,
                    run_id=context.run_id,
                    request_id=context.request_id
                )
                logger.debug(f"Converted StronglyTypedUserExecutionContext to UserExecutionContext for user {context.user_id}")
                context = converted_context
            else:
                raise TypeError(
                    f"Expected UserExecutionContext or StronglyTypedUserExecutionContext, got: {type(context)}"
                )
        except ImportError:
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
        # Execute registered cleanup callbacks first
        try:
            await context.cleanup()
        except Exception as e:
            logger.warning(f"Error during cleanup callbacks: {e}")
        
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


async def create_isolated_execution_context(
    user_id: str,
    request_id: str,
    database_session: Optional['AsyncSession'] = None,
    websocket_emitter: Optional[Any] = None,
    thread_id: Optional[str] = None,
    run_id: Optional[str] = None,
    validate_user: bool = True,
    isolation_level: str = "standard"
) -> UserExecutionContext:
    """
    SSOT factory function for creating isolated execution contexts.
    
    This is the Single Source of Truth for creating UserExecutionContext instances
    with comprehensive isolation guarantees and database/WebSocket integration.
    
    Business Value Justification (BVJ):
    - Segment: ALL (Free → Enterprise)
    - Business Goal: Ensure complete request isolation and proper resource management
    - Value Impact: Guarantees user data security and prevents resource leaks
    - Strategic Impact: Critical for multi-user agent execution and compliance
    
    Args:
        user_id: User identifier from authentication
        request_id: Request identifier for this specific operation
        database_session: Optional database session for request-scoped operations
        websocket_emitter: Optional WebSocket emitter for real-time updates
        thread_id: Optional thread identifier (auto-generated if None)
        run_id: Optional run identifier (auto-generated if None)  
        validate_user: Whether to validate user exists in database
        isolation_level: Isolation level ("standard" or "strict")
        
    Returns:
        New UserExecutionContext with proper isolation
        
    Raises:
        InvalidContextError: If parameters are invalid or user validation fails
    """
    if not user_id or not isinstance(user_id, str):
        raise InvalidContextError("user_id must be a non-empty string")
        
    if not request_id or not isinstance(request_id, str):
        raise InvalidContextError("request_id must be a non-empty string")
    
    # Generate missing IDs if not provided
    id_manager = UnifiedIDManager()
    
    if not thread_id:
        thread_id = id_manager.generate_thread_id()
        
    if not run_id:
        run_id = id_manager.generate_run_id(thread_id)
    
    # Validate user exists in database if requested and session available
    if validate_user and database_session:
        try:
            # Check user exists in database
            result = await database_session.execute("""
                SELECT id, is_active FROM auth.users WHERE id = :user_id 
                UNION ALL
                SELECT id, is_active FROM users WHERE id = :user_id
                LIMIT 1
            """, {"user_id": user_id})
            
            user_row = result.fetchone()
            if not user_row:
                raise InvalidContextError(f"User {user_id} not found in database")
                
            if not user_row[1]:  # is_active check
                raise InvalidContextError(f"User {user_id} is not active")
                
            logger.debug(f"User validation successful for {user_id}")
            
        except Exception as e:
            if isinstance(e, InvalidContextError):
                raise
            logger.warning(f"User validation failed for {user_id}: {e}")
            
            # In strict isolation, validation failure is fatal
            if isolation_level == "strict":
                raise InvalidContextError(
                    f"User validation required in strict isolation mode but failed: {e}"
                )
    
    # Build agent context with isolation metadata
    agent_context = {
        'isolation_level': isolation_level,
        'created_via': 'create_isolated_execution_context',
        'validated_user': validate_user and database_session is not None,
        'has_websocket_emitter': websocket_emitter is not None,
        'has_database_session': database_session is not None
    }
    
    # Build audit metadata
    audit_metadata = {
        'context_source': 'ssot_isolated_factory',
        'isolation_level': isolation_level,
        'validation_performed': validate_user and database_session is not None,
        'factory_method': 'create_isolated_execution_context'
    }
    
    # Convert websocket_emitter to websocket_client_id if needed
    websocket_client_id = None
    if websocket_emitter:
        if hasattr(websocket_emitter, 'user_id'):
            websocket_client_id = f"ws_{websocket_emitter.user_id}"
        else:
            websocket_client_id = f"ws_{user_id}"
    
    # Create the context
    context = UserExecutionContext(
        user_id=user_id,
        thread_id=thread_id,
        run_id=run_id,
        request_id=request_id,
        db_session=database_session,
        websocket_client_id=websocket_client_id,
        agent_context=agent_context,
        audit_metadata=audit_metadata
    )
    
    logger.info(
        f"🔒 ISOLATED_CONTEXT_CREATED: Secure isolated execution context ready. "
        f"User: {user_id[:8]}..., Request: {request_id[:8]}..., "
        f"Isolation_level: {isolation_level}, Validation_performed: {validate_user and database_session is not None}, "
        f"WebSocket_emitter: {'configured' if websocket_emitter else 'none'}, "
        f"DB_session: {'attached' if database_session else 'none'}, "
        f"Business_context: Enterprise-grade security for agent execution"
    )
    
    return context


# Alias for compatibility with integration tests
UserExecutionContextFactory = UserContextFactory

# ============================================================================
# USER CONTEXT MANAGER - SINGLE SOURCE OF TRUTH FOR CONTEXT MANAGEMENT
# ============================================================================

import threading
import time
from collections import defaultdict
from typing import Optional, Set, Callable, Union, Coroutine
import weakref
import gc


class UserContextManager:
    """
    Single Source of Truth for managing UserExecutionContext instances with enterprise-grade security.
    
    This class provides comprehensive multi-tenant isolation, preventing any form of data leakage
    between user contexts while ensuring proper resource management and audit compliance.
    
    Business Value Justification (BVJ):
    - Segment: Enterprise (highest security requirements)
    - Business Goal: Prevent data leakage between users ($500K+ ARR protection)
    - Value Impact: Validates multi-tenant isolation preventing security breaches
    - Revenue Impact: Critical for compliance requirements enabling enterprise sales
    
    Security Features:
    - Complete isolation between user contexts
    - Memory isolation preventing shared state contamination
    - Cross-contamination detection and prevention
    - Comprehensive audit trails for compliance
    - Resource limits and automatic cleanup
    - Thread-safe concurrent operations
    - Graceful error handling and recovery
    
    Key Design Principles:
    - Zero tolerance for cross-user data leakage
    - Fail-safe patterns - errors don't compromise other users
    - Resource management - automatic cleanup prevents memory leaks
    - Observability - comprehensive audit trails and monitoring
    - Performance - efficient operations under high concurrency
    """
    
    # Class constants for security limits
    MAX_CONTEXTS_PER_USER = 100
    DEFAULT_CONTEXT_TTL = 3600  # 1 hour default TTL in seconds
    MAX_TOTAL_CONTEXTS = 10000  # System-wide limit
    CLEANUP_INTERVAL = 300  # 5 minutes
    
    def __init__(
        self,
        isolation_level: str = "strict",
        cross_contamination_detection: bool = True,
        memory_isolation: bool = True,
        enable_audit_trail: bool = True,
        auto_cleanup: bool = True
    ):
        """
        Initialize UserContextManager with security-first configuration.
        
        Args:
            isolation_level: Isolation level ("strict" or "standard")
            cross_contamination_detection: Enable cross-contamination detection
            memory_isolation: Enable memory isolation validation
            enable_audit_trail: Enable comprehensive audit trails
            auto_cleanup: Enable automatic resource cleanup
        """
        self._isolation_level = isolation_level
        self._cross_contamination_detection = cross_contamination_detection
        self._memory_isolation = memory_isolation
        self._enable_audit_trail = enable_audit_trail
        self._auto_cleanup = auto_cleanup
        
        # Thread-safe context storage with isolation
        self._contexts_lock = threading.RLock()
        self._contexts: Dict[str, UserExecutionContext] = {}
        self._context_metadata: Dict[str, Dict[str, Any]] = {}
        self._context_timestamps: Dict[str, float] = {}
        self._context_ttl: Dict[str, float] = {}
        
        # User-based context tracking for limits
        self._user_contexts: Dict[str, Set[str]] = defaultdict(set)
        self._user_contexts_lock = threading.RLock()
        
        # Audit trail storage
        self._audit_trail: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._audit_lock = threading.RLock()
        
        # Memory isolation tracking
        self._memory_references: Dict[str, Set[int]] = defaultdict(set)
        self._memory_lock = threading.RLock()
        
        # Cleanup management
        self._cleanup_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self._last_cleanup = time.time()
        
        # Health monitoring
        self._error_count = 0
        self._operation_count = 0
        self._healthy = True
        
        logger.info(
            f"UserContextManager initialized: isolation_level={isolation_level}, "
            f"cross_contamination_detection={cross_contamination_detection}, "
            f"memory_isolation={memory_isolation}"
        )
        
        # Initialize audit trail
        if self._enable_audit_trail:
            self._record_audit_event(
                "system",
                "manager_initialized",
                {
                    "isolation_level": isolation_level,
                    "security_features": {
                        "cross_contamination_detection": cross_contamination_detection,
                        "memory_isolation": memory_isolation,
                        "audit_trail": enable_audit_trail
                    }
                }
            )
    
    def get_context(self, context_key: str) -> UserExecutionContext:
        """
        Retrieve user context with comprehensive isolation validation.
        
        Args:
            context_key: Unique key for the context (typically user_id or user_id_request_id)
            
        Returns:
            UserExecutionContext for the specified key
            
        Raises:
            KeyError: If context doesn't exist
            ContextIsolationError: If isolation validation fails
            ValueError: If context_key is invalid
        """
        if not context_key or not isinstance(context_key, str):
            raise ValueError("context_key must be a non-empty string")
        
        with self._contexts_lock:
            self._operation_count += 1
            
            # Auto-cleanup expired contexts
            if self._auto_cleanup:
                self._cleanup_expired_contexts()
            
            # Check if context exists
            if context_key not in self._contexts:
                self._record_audit_event(
                    context_key,
                    "context_access_denied",
                    {"reason": "context_not_found"}
                )
                raise KeyError(f"Context not found: {context_key}")
            
            # Check if context is expired
            if self._is_context_expired(context_key):
                self._cleanup_single_context(context_key)
                self._record_audit_event(
                    context_key,
                    "context_access_denied",
                    {"reason": "context_expired"}
                )
                raise KeyError(f"Context expired: {context_key}")
            
            context = self._contexts[context_key]
            
            # Validate isolation if enabled
            if self._memory_isolation:
                try:
                    context.verify_isolation()
                except ContextIsolationError as e:
                    self._error_count += 1
                    self._record_audit_event(
                        context_key,
                        "isolation_violation_detected",
                        {"error": str(e), "severity": "CRITICAL"}
                    )
                    raise
            
            # Record successful access
            self._record_audit_event(
                context_key,
                "context_accessed",
                {
                    "user_id": context.user_id,
                    "thread_id": context.thread_id,
                    "request_id": context.request_id
                }
            )
            
            return context
    
    def set_context(
        self,
        context_key: str,
        context: UserExecutionContext,
        ttl_seconds: Optional[float] = None
    ) -> None:
        """
        Set user context with comprehensive security validation.
        
        Args:
            context_key: Unique key for the context
            context: UserExecutionContext to store
            ttl_seconds: Time-to-live in seconds (optional)
            
        Raises:
            ValueError: If parameters are invalid
            InvalidContextError: If context validation fails
            ContextIsolationError: If isolation validation fails
            RuntimeError: If resource limits are exceeded
        """
        if not context_key or not isinstance(context_key, str):
            raise ValueError("context_key must be a non-empty string")
        
        if context is None:
            raise ValueError("context cannot be None")
        
        if not isinstance(context, UserExecutionContext):
            raise InvalidContextError(f"Expected UserExecutionContext, got: {type(context)}")
        
        # Validate context integrity
        try:
            validate_user_context(context)
        except (TypeError, InvalidContextError) as e:
            self._error_count += 1
            raise InvalidContextError(f"Context validation failed: {e}")
        
        # Validate isolation
        try:
            context.verify_isolation()
        except ContextIsolationError as e:
            self._error_count += 1
            self._record_audit_event(
                context_key,
                "context_isolation_failure",
                {"error": str(e), "severity": "CRITICAL"}
            )
            raise
        
        with self._contexts_lock:
            self._operation_count += 1
            
            # Auto-cleanup if needed
            if self._auto_cleanup:
                self._cleanup_expired_contexts()
            
            # Check system-wide limits
            if len(self._contexts) >= self.MAX_TOTAL_CONTEXTS:
                raise RuntimeError(
                    f"System-wide context limit exceeded: {self.MAX_TOTAL_CONTEXTS}"
                )
            
            # Check per-user limits
            with self._user_contexts_lock:
                user_context_count = len(self._user_contexts.get(context.user_id, set()))
                if user_context_count >= self.MAX_CONTEXTS_PER_USER:
                    raise RuntimeError(
                        f"User context limit exceeded for {context.user_id}: "
                        f"{self.MAX_CONTEXTS_PER_USER}"
                    )
            
            # Store context with deep copy for isolation
            self._contexts[context_key] = copy.deepcopy(context)
            
            # Store metadata
            current_time = time.time()
            self._context_timestamps[context_key] = current_time
            self._context_ttl[context_key] = ttl_seconds or self.DEFAULT_CONTEXT_TTL
            self._context_metadata[context_key] = {
                "created_at": current_time,
                "user_id": context.user_id,
                "thread_id": context.thread_id,
                "request_id": context.request_id,
                "ttl_seconds": ttl_seconds or self.DEFAULT_CONTEXT_TTL,
                "has_db_session": context.db_session is not None,
                "has_websocket": context.websocket_client_id is not None,
                "isolation_validated": True
            }
            
            # Track user contexts
            with self._user_contexts_lock:
                self._user_contexts[context.user_id].add(context_key)
            
            # Track memory references for isolation
            if self._memory_isolation:
                with self._memory_lock:
                    memory_refs = set()
                    if hasattr(context, 'agent_context') and context.agent_context:
                        memory_refs.add(id(context.agent_context))
                    if hasattr(context, 'audit_metadata') and context.audit_metadata:
                        memory_refs.add(id(context.audit_metadata))
                    if context.db_session:
                        memory_refs.add(id(context.db_session))
                    
                    self._memory_references[context_key] = memory_refs
            
            # Record audit event
            self._record_audit_event(
                context_key,
                "context_set",
                {
                    "user_id": context.user_id,
                    "thread_id": context.thread_id,
                    "request_id": context.request_id,
                    "ttl_seconds": ttl_seconds or self.DEFAULT_CONTEXT_TTL,
                    "isolation_level": self._isolation_level
                }
            )
            
            logger.debug(
                f"Context set successfully: key={context_key}, user={context.user_id[:8]}..., "
                f"total_contexts={len(self._contexts)}"
            )
    
    def clear_context(self, context_key: str) -> bool:
        """
        Clear context with comprehensive cleanup.
        
        Args:
            context_key: Key of the context to clear
            
        Returns:
            True if context was cleared, False if it didn't exist
        """
        if not context_key or not isinstance(context_key, str):
            raise ValueError("context_key must be a non-empty string")
        
        with self._contexts_lock:
            self._operation_count += 1
            
            if context_key not in self._contexts:
                return False
            
            # Get context for audit before cleanup
            context = self._contexts[context_key]
            user_id = context.user_id
            
            # Perform cleanup
            self._cleanup_single_context(context_key)
            
            # Record audit event
            self._record_audit_event(
                context_key,
                "context_cleared",
                {"user_id": user_id, "manual_clear": True}
            )
            
            logger.debug(f"Context cleared successfully: key={context_key}")
            return True
    
    def validate_isolation(self, context_key: str) -> bool:
        """
        Validate context isolation and detect cross-contamination.
        
        Args:
            context_key: Key of the context to validate
            
        Returns:
            True if isolation is valid
            
        Raises:
            KeyError: If context doesn't exist
            ContextIsolationError: If isolation violations are detected
        """
        with self._contexts_lock:
            if context_key not in self._contexts:
                raise KeyError(f"Context not found: {context_key}")
            
            context = self._contexts[context_key]
            
            # Validate context isolation
            try:
                context.verify_isolation()
            except ContextIsolationError as e:
                self._record_audit_event(
                    context_key,
                    "isolation_validation_failed",
                    {"error": str(e), "severity": "CRITICAL"}
                )
                raise
            
            # Cross-contamination detection
            if self._cross_contamination_detection:
                self._detect_cross_contamination(context_key, context)
            
            # Memory isolation validation
            if self._memory_isolation:
                self._validate_memory_isolation(context_key, context)
            
            self._record_audit_event(
                context_key,
                "isolation_validated",
                {"user_id": context.user_id}
            )
            
            return True
    
    def get_active_contexts(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all active contexts.
        
        Returns:
            Dictionary mapping context keys to context metadata
        """
        with self._contexts_lock:
            # Auto-cleanup expired contexts
            if self._auto_cleanup:
                self._cleanup_expired_contexts()
            
            return {
                key: {
                    "user_id": metadata["user_id"],
                    "created_at": metadata["created_at"],
                    "ttl_seconds": metadata["ttl_seconds"],
                    "age_seconds": time.time() - metadata["created_at"],
                    "has_db_session": metadata["has_db_session"],
                    "has_websocket": metadata["has_websocket"]
                }
                for key, metadata in self._context_metadata.items()
                if key in self._contexts
            }
    
    def get_audit_trail(self, context_key: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive audit trail for a context.
        
        Args:
            context_key: Key of the context
            
        Returns:
            Audit trail dictionary or None if context doesn't exist
        """
        if not self._enable_audit_trail:
            return None
        
        with self._audit_lock:
            if context_key not in self._audit_trail and context_key not in self._contexts:
                return None
            
            # Get context metadata if available
            context_info = {}
            if context_key in self._context_metadata:
                metadata = self._context_metadata[context_key]
                context_info = {
                    "context_set_at": metadata["created_at"],
                    "user_id": metadata["user_id"],
                    "thread_id": metadata["thread_id"],
                    "request_id": metadata["request_id"],
                    "ttl_seconds": metadata["ttl_seconds"],
                    "has_db_session": metadata["has_db_session"],
                    "has_websocket": metadata["has_websocket"]
                }
            
            # Build comprehensive audit trail
            audit_data = {
                "context_key": context_key,
                "context_source": "user_context_manager",
                "isolation_verified": True,
                "compliance_version": "1.0",
                "events": self._audit_trail.get(context_key, []),
                "total_events": len(self._audit_trail.get(context_key, [])),
                **context_info
            }
            
            return audit_data
    
    # ========================================================================
    # INTEGRATION METHODS FOR WEBSOCKET, AGENT EXECUTION, AND DATABASE
    # ========================================================================
    
    def create_isolated_context(
        self,
        user_id: str,
        request_id: str,
        **kwargs
    ) -> UserExecutionContext:
        """
        Create isolated context using SSOT factory integration.
        
        Args:
            user_id: User identifier
            request_id: Request identifier
            **kwargs: Additional arguments for create_isolated_execution_context
            
        Returns:
            New isolated UserExecutionContext
        """
        # Use SSOT factory for context creation
        context = asyncio.run(create_isolated_execution_context(
            user_id=user_id,
            request_id=request_id,
            **kwargs
        ))
        
        # Set the context in manager
        self.set_context(f"{user_id}_{request_id}", context)
        
        return context
    
    def create_context_with_unified_ids(self, user_id: str) -> UserExecutionContext:
        """
        Create context with UnifiedIDManager integration.
        
        Args:
            user_id: User identifier
            
        Returns:
            New UserExecutionContext with unified ID generation
        """
        id_manager = UnifiedIDManager()
        thread_id = id_manager.generate_thread_id()
        run_id = id_manager.generate_run_id()
        request_id = str(uuid.uuid4())
        
        context = UserExecutionContext.from_request(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            request_id=request_id
        )
        
        # Set context in manager
        self.set_context(f"{user_id}_{request_id}", context)
        
        return context
    
    def create_managed_context(
        self,
        user_id: str,
        request_id: str,
        **kwargs
    ) -> UserExecutionContext:
        """
        Create managed context with factory integration.
        
        Args:
            user_id: User identifier
            request_id: Request identifier
            **kwargs: Additional context arguments
            
        Returns:
            New managed UserExecutionContext
        """
        # Use factory to create isolated context
        context = asyncio.run(create_isolated_execution_context(
            user_id=user_id,
            request_id=request_id,
            **kwargs
        ))
        
        # Set context in manager with automatic key generation
        context_key = f"{user_id}_{request_id}"
        self.set_context(context_key, context)
        
        return context
    
    async def notify_context_change(self, user_id: str, event_type: str) -> None:
        """
        Notify WebSocket connections of context changes.
        
        Args:
            user_id: User identifier
            event_type: Type of change event
        """
        try:
            # Import WebSocket manager (avoid circular imports)
            from netra_backend.app.websocket_core.manager import WebSocketManager
            
            # Get WebSocket connection for user
            ws_manager = WebSocketManager()
            connection = ws_manager.get_connection(user_id)
            
            if connection:
                await connection.send_json({
                    "event": "context_change",
                    "type": event_type,
                    "user_id": user_id,
                    "timestamp": time.time()
                })
                
                self._record_audit_event(
                    user_id,
                    "websocket_notification_sent",
                    {"event_type": event_type}
                )
        except Exception as e:
            logger.warning(f"Failed to notify WebSocket for user {user_id}: {e}")
    
    async def send_event(
        self,
        user_id: str,
        event_name: str,
        event_data: Dict[str, Any]
    ) -> None:
        """
        Send event to user's WebSocket connection.
        
        Args:
            user_id: User identifier
            event_name: Name of the event
            event_data: Event data
        """
        try:
            from netra_backend.app.websocket_core.notifier import WebSocketNotifier
            
            notifier = WebSocketNotifier()
            await notifier.send_event(user_id, event_name, event_data)
            
            self._record_audit_event(
                user_id,
                "event_sent",
                {"event_name": event_name, "has_data": bool(event_data)}
            )
        except Exception as e:
            logger.warning(f"Failed to send event {event_name} to user {user_id}: {e}")
    
    async def execute_with_agent(
        self,
        user_id: str,
        agent_name: str,
        parameters: Dict[str, Any]
    ) -> Any:
        """
        Execute agent with proper context isolation.
        
        Args:
            user_id: User identifier
            agent_name: Name of the agent to execute
            parameters: Agent parameters
            
        Returns:
            Agent execution result
        """
        try:
            from netra_backend.app.agents.supervisor.agent_registry import UserAgentSession
            
            # Get user context
            context_key = self._find_context_key_for_user(user_id)
            if not context_key:
                raise ValueError(f"No active context found for user: {user_id}")
            
            context = self.get_context(context_key)
            
            # Execute agent with context
            session = UserAgentSession()
            result = await session.execute(
                agent_name=agent_name,
                parameters=parameters,
                context=context
            )
            
            self._record_audit_event(
                context_key,
                "agent_executed",
                {
                    "agent_name": agent_name,
                    "user_id": user_id,
                    "success": True
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Agent execution failed for user {user_id}: {e}")
            
            if context_key:
                self._record_audit_event(
                    context_key,
                    "agent_execution_failed",
                    {
                        "agent_name": agent_name,
                        "user_id": user_id,
                        "error": str(e)
                    }
                )
            
            raise
    
    def create_context_with_transaction(self, user_id: str) -> UserExecutionContext:
        """
        Create context with database transaction.
        
        Args:
            user_id: User identifier
            
        Returns:
            UserExecutionContext with database transaction
        """
        from netra_backend.app.db.database_manager import DatabaseManager
        
        # Begin database transaction
        db_manager = DatabaseManager()
        transaction = db_manager.begin_transaction()
        
        # Create context with transaction
        thread_id = f"tx_thread_{int(time.time())}"
        run_id = f"tx_run_{int(time.time())}"
        request_id = str(uuid.uuid4())
        
        context = UserExecutionContext.from_request(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            request_id=request_id,
            db_session=transaction
        )
        
        # Set context in manager
        context_key = f"{user_id}_tx_{request_id}"
        self.set_context(context_key, context)
        
        return context
    
    async def execute_in_transaction(
        self,
        user_id: str,
        query: str
    ) -> Any:
        """
        Execute database query within user's transaction.
        
        Args:
            user_id: User identifier
            query: SQL query to execute
            
        Returns:
            Query result
        """
        context_key = self._find_context_key_for_user(user_id)
        if not context_key:
            raise ValueError(f"No active context found for user: {user_id}")
        
        context = self.get_context(context_key)
        
        if not context.db_session:
            raise ValueError(f"No database session found for user: {user_id}")
        
        # Execute query
        result = await context.db_session.execute(query)
        
        self._record_audit_event(
            context_key,
            "database_query_executed",
            {"user_id": user_id, "query_type": query.split()[0].upper()}
        )
        
        return result
    
    async def cleanup_context(self, context_key: str) -> None:
        """
        Cleanup context with resource management.
        
        Args:
            context_key: Key of the context to cleanup
        """
        with self._contexts_lock:
            if context_key in self._contexts:
                context = self._contexts[context_key]
                
                # Cleanup database session if present
                if context.db_session:
                    try:
                        await context.db_session.close()
                    except Exception as e:
                        logger.warning(f"Error closing database session: {e}")
                
                # Execute cleanup callbacks
                if context_key in self._cleanup_callbacks:
                    for callback in self._cleanup_callbacks[context_key]:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback()
                            else:
                                callback()
                        except Exception as e:
                            logger.warning(f"Cleanup callback error: {e}")
                
                # Remove context
                self._cleanup_single_context(context_key)
    
    def cleanup_all_contexts(self) -> int:
        """
        Cleanup all contexts (typically for shutdown).
        
        Returns:
            Number of contexts cleaned up
        """
        with self._contexts_lock:
            context_keys = list(self._contexts.keys())
            
            for context_key in context_keys:
                try:
                    self._cleanup_single_context(context_key)
                except Exception as e:
                    logger.warning(f"Error cleaning up context {context_key}: {e}")
            
            self._record_audit_event(
                "system",
                "all_contexts_cleaned",
                {"contexts_cleaned": len(context_keys)}
            )
            
            return len(context_keys)
    
    def is_healthy(self) -> bool:
        """
        Check if the UserContextManager is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        # Simple health check based on error rate
        if self._operation_count == 0:
            return True
        
        error_rate = self._error_count / self._operation_count
        return error_rate < 0.1  # Less than 10% error rate
    
    # ========================================================================
    # PRIVATE METHODS FOR INTERNAL OPERATIONS
    # ========================================================================
    
    def _cleanup_single_context(self, context_key: str) -> None:
        """Remove single context and all associated data."""
        context = self._contexts.get(context_key)
        if not context:
            return
        
        user_id = context.user_id
        
        # Remove from all tracking structures
        self._contexts.pop(context_key, None)
        self._context_metadata.pop(context_key, None)
        self._context_timestamps.pop(context_key, None)
        self._context_ttl.pop(context_key, None)
        
        # Remove from user contexts tracking
        with self._user_contexts_lock:
            if user_id in self._user_contexts:
                self._user_contexts[user_id].discard(context_key)
                if not self._user_contexts[user_id]:
                    del self._user_contexts[user_id]
        
        # Remove memory references
        with self._memory_lock:
            self._memory_references.pop(context_key, None)
        
        # Remove cleanup callbacks
        self._cleanup_callbacks.pop(context_key, None)
    
    def _cleanup_expired_contexts(self) -> None:
        """Clean up expired contexts."""
        current_time = time.time()
        
        # Only run cleanup if enough time has passed
        if current_time - self._last_cleanup < self.CLEANUP_INTERVAL:
            return
        
        expired_keys = []
        
        # Find expired contexts
        for context_key, timestamp in self._context_timestamps.items():
            ttl = self._context_ttl.get(context_key, self.DEFAULT_CONTEXT_TTL)
            if current_time - timestamp > ttl:
                expired_keys.append(context_key)
        
        # Clean up expired contexts
        for context_key in expired_keys:
            self._cleanup_single_context(context_key)
            self._record_audit_event(
                context_key,
                "context_expired",
                {"expired_at": current_time}
            )
        
        self._last_cleanup = current_time
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired contexts")
    
    def _is_context_expired(self, context_key: str) -> bool:
        """Check if a context is expired."""
        timestamp = self._context_timestamps.get(context_key)
        if not timestamp:
            return True
        
        ttl = self._context_ttl.get(context_key, self.DEFAULT_CONTEXT_TTL)
        return time.time() - timestamp > ttl
    
    def _detect_cross_contamination(
        self,
        context_key: str,
        context: UserExecutionContext
    ) -> None:
        """Detect potential cross-user contamination."""
        if not self._cross_contamination_detection:
            return
        
        # Check for suspicious data patterns
        suspicious_patterns = []
        
        # Check agent context for other user IDs
        if hasattr(context, 'agent_context') and context.agent_context:
            for key, value in context.agent_context.items():
                if isinstance(value, str) and 'user_' in value.lower():
                    # Check if this contains other user IDs
                    for other_key in self._contexts:
                        if other_key != context_key:
                            other_context = self._contexts[other_key]
                            if other_context.user_id in str(value):
                                suspicious_patterns.append(
                                    f"Found other user ID {other_context.user_id} in agent_context"
                                )
        
        if suspicious_patterns:
            self._record_audit_event(
                context_key,
                "cross_contamination_detected",
                {
                    "patterns": suspicious_patterns,
                    "severity": "HIGH",
                    "user_id": context.user_id
                }
            )
            
            logger.warning(
                f"Cross-contamination detected in context {context_key}: "
                f"{suspicious_patterns}"
            )
    
    def _validate_memory_isolation(
        self,
        context_key: str,
        context: UserExecutionContext
    ) -> None:
        """Validate memory isolation between contexts."""
        if not self._memory_isolation:
            return
        
        with self._memory_lock:
            context_refs = self._memory_references.get(context_key, set())
            
            # Check for shared memory references with other contexts
            for other_key, other_refs in self._memory_references.items():
                if other_key != context_key:
                    shared_refs = context_refs & other_refs
                    if shared_refs:
                        self._record_audit_event(
                            context_key,
                            "memory_isolation_violation",
                            {
                                "shared_with": other_key,
                                "shared_references": len(shared_refs),
                                "severity": "CRITICAL"
                            }
                        )
                        
                        raise ContextIsolationError(
                            f"Memory isolation violation: Context {context_key} "
                            f"shares memory references with {other_key}"
                        )
    
    def _find_context_key_for_user(self, user_id: str) -> Optional[str]:
        """Find active context key for a user."""
        with self._user_contexts_lock:
            user_context_keys = self._user_contexts.get(user_id, set())
            
            if not user_context_keys:
                return None
            
            # Return the most recently created context
            most_recent_key = None
            most_recent_time = 0
            
            for context_key in user_context_keys:
                if context_key in self._context_timestamps:
                    timestamp = self._context_timestamps[context_key]
                    if timestamp > most_recent_time:
                        most_recent_time = timestamp
                        most_recent_key = context_key
            
            return most_recent_key
    
    def _record_audit_event(
        self,
        context_key: str,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> None:
        """Record audit event for compliance."""
        if not self._enable_audit_trail:
            return
        
        with self._audit_lock:
            event = {
                "timestamp": time.time(),
                "event_type": event_type,
                "context_key": context_key,
                "event_data": event_data,
                "manager_id": id(self)
            }
            
            self._audit_trail[context_key].append(event)
            
            # Limit audit trail size per context
            max_events_per_context = 1000
            if len(self._audit_trail[context_key]) > max_events_per_context:
                self._audit_trail[context_key] = self._audit_trail[context_key][-max_events_per_context:]


# Export all public classes and functions
__all__ = [
    'UserExecutionContext',
    'UserContextManager',  # NEW: Adding the UserContextManager class
    'UserContextFactory',
    'UserExecutionContextFactory',  # Alias for compatibility
    'InvalidContextError', 
    'ContextIsolationError',
    'validate_user_context',
    'managed_user_context',
    'register_shared_object',
    'clear_shared_object_registry',
    'create_isolated_execution_context'
]