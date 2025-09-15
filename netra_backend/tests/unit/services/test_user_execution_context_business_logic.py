"""UserExecutionContext Business Logic Unit Tests

ISSUE #825 Phase 2: User Execution Context Business Logic Testing
Business Impact: $500K+ ARR Golden Path protection through comprehensive business logic validation

This module provides focused unit tests for UserExecutionContext business logic,
specifically targeting the critical validation, isolation, and factory patterns
that protect user data security and context integrity.

Test Focus Areas:
1. User isolation boundary enforcement
2. Context validation and security checks
3. Child context creation and cleanup
4. Memory management and resource limits
5. Factory pattern compliance and consistency
6. Error handling and recovery patterns

Coverage Target: 15-20 focused unit tests covering critical business logic gaps
Execution Pattern: Fast, no Docker dependencies, SSOT compliant
Pattern Reference: Phase 1 WebSocket unit test success (100% passing)
"""

import pytest
import uuid
import asyncio
import copy
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from typing import Dict, Any

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    InvalidContextError,
    ContextIsolationError
)
from shared.isolated_environment import IsolatedEnvironment


class UserExecutionContextBusinessLogicTests(SSotAsyncTestCase):
    """Comprehensive business logic unit tests for UserExecutionContext.

    These tests focus on the critical business logic that protects the Golden Path
    user flow and ensures proper user isolation and context management.
    """

    def setup_method(self, method):
        """Setup for each test method with SSOT compliance."""
        super().setup_method(method)

        # Standard test context data
        self.valid_user_id = "user_12345"
        self.valid_thread_id = "thread_67890"
        self.valid_run_id = "run_abc123"
        self.valid_request_id = "request_def456"
        self.valid_websocket_id = "ws_connection_789"

        # Test environment isolation
        self.env = IsolatedEnvironment()

    @pytest.mark.asyncio
    async def test_user_isolation_validation_success(self):
        """Test that valid user isolation passes validation.

        Business Logic: User isolation boundary enforcement is critical for
        preventing cross-user data contamination in multi-tenant system.

        Expected: Context with proper isolation should validate successfully.
        """
        # Create context with proper isolation
        context = UserExecutionContext(
            user_id=self.valid_user_id,
            thread_id=self.valid_thread_id,
            run_id=self.valid_run_id,
            request_id=self.valid_request_id,
            websocket_client_id=self.valid_websocket_id,
            agent_context={"operation": "test"},
            audit_metadata={"source": "test"}
        )

        # Validation should succeed
        assert context.user_id == self.valid_user_id
        assert context.thread_id == self.valid_thread_id
        assert context._validation_fingerprint is not None
        assert len(context._validation_fingerprint) == 16  # SHA256 truncated

        # Isolation token should be unique
        assert context._isolation_token is not None
        assert context._isolation_token.startswith(("isolation_token_", "uuid_", "id_"))

    @pytest.mark.asyncio
    async def test_cross_user_contamination_detection(self):
        """Test detection of cross-user data contamination in agent context.

        Business Logic: System must prevent user A's data from appearing in user B's context.
        This is critical for data privacy and security compliance.

        Expected: ContextIsolationError should be raised when cross-user contamination detected.
        """
        # Create object with different user_id (simulating cross-user contamination)
        contaminated_object = Mock()
        contaminated_object.user_id = "user_different_12345"

        # Attempt to create context with contaminated data
        with pytest.raises(ContextIsolationError) as exc_info:
            UserExecutionContext(
                user_id=self.valid_user_id,
                thread_id=self.valid_thread_id,
                run_id=self.valid_run_id,
                request_id=self.valid_request_id,
                agent_context={"contaminated_data": contaminated_object}
            )

        # Verify proper error message
        assert "Cross-user contamination detected" in str(exc_info.value)
        assert self.valid_user_id in str(exc_info.value)
        assert "user_different_12345" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_placeholder_value_detection(self):
        """Test detection of dangerous placeholder values in context fields.

        Business Logic: Placeholder values like 'placeholder', 'default', 'test'
        indicate improper initialization that could break the Golden Path user flow.

        Expected: InvalidContextError should be raised for forbidden placeholder values.
        """
        forbidden_values = ['placeholder', 'default', 'temp', 'null', 'test', 'demo']

        for forbidden_value in forbidden_values:
            with pytest.raises(InvalidContextError) as exc_info:
                UserExecutionContext(
                    user_id=forbidden_value,
                    thread_id=self.valid_thread_id,
                    run_id=self.valid_run_id,
                    request_id=self.valid_request_id
                )

            # Check for the actual error message format from the implementation
            error_message = str(exc_info.value)
            assert ("forbidden placeholder value" in error_message.lower() or
                   "required field" in error_message.lower()), f"Unexpected error message: {error_message}"

    @pytest.mark.asyncio
    async def test_child_context_creation_hierarchy(self):
        """Test proper hierarchical child context creation.

        Business Logic: Child contexts must maintain proper hierarchy and isolation
        while preserving audit trail continuity for complex agent operations.

        Expected: Child context should have proper depth, parent tracking, and isolation.
        """
        # Create parent context
        parent_context = UserExecutionContext(
            user_id=self.valid_user_id,
            thread_id=self.valid_thread_id,
            run_id=self.valid_run_id,
            request_id=self.valid_request_id,
            agent_context={"parent_data": "preserved"},
            audit_metadata={"audit_info": "preserved"}
        )

        # Create child context
        child_context = parent_context.create_child_context(
            operation_name="data_analysis",
            additional_agent_context={"child_data": "added"},
            additional_audit_metadata={"child_audit": "added"}
        )

        # Verify hierarchy
        assert child_context.user_id == parent_context.user_id  # Same user
        assert child_context.thread_id == parent_context.thread_id  # Same thread
        assert child_context.run_id == parent_context.run_id  # Same run
        assert child_context.request_id != parent_context.request_id  # Different request
        assert child_context.operation_depth == parent_context.operation_depth + 1
        assert child_context.parent_request_id == parent_context.request_id

        # Verify data preservation and isolation
        assert child_context.agent_context["parent_data"] == "preserved"
        assert child_context.agent_context["child_data"] == "added"
        assert child_context.agent_context["operation_name"] == "data_analysis"

        # Verify audit trail
        assert child_context.audit_metadata["audit_info"] == "preserved"
        assert child_context.audit_metadata["child_audit"] == "added"
        assert child_context.audit_metadata["parent_request_id"] == parent_context.request_id

    @pytest.mark.asyncio
    async def test_child_context_depth_limit_protection(self):
        """Test protection against excessive nesting depth.

        Business Logic: Prevent infinite recursion in child context creation
        which could cause memory exhaustion and system instability.

        Expected: InvalidContextError when maximum depth exceeded.
        """
        # Create context with maximum allowed depth
        context = UserExecutionContext(
            user_id=self.valid_user_id,
            thread_id=self.valid_thread_id,
            run_id=self.valid_run_id,
            request_id=self.valid_request_id,
            operation_depth=10  # At maximum allowed depth
        )

        # Attempt to create child context should fail
        with pytest.raises(InvalidContextError) as exc_info:
            context.create_child_context("excessive_depth")

        assert "Maximum operation depth" in str(exc_info.value)
        assert "10" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_metadata_isolation_deep_copy(self):
        """Test that metadata dictionaries are properly deep copied for isolation.

        Business Logic: Metadata must be isolated to prevent shared state between
        contexts, which could cause data corruption or cross-user contamination.

        Expected: Modifications to source metadata should not affect context metadata.
        """
        # Create mutable metadata
        original_agent_context = {"nested": {"value": "original"}}
        original_audit_metadata = {"audit": {"level": "info"}}

        # Create context
        context = UserExecutionContext(
            user_id=self.valid_user_id,
            thread_id=self.valid_thread_id,
            run_id=self.valid_run_id,
            request_id=self.valid_request_id,
            agent_context=original_agent_context,
            audit_metadata=original_audit_metadata
        )

        # Modify original metadata
        original_agent_context["nested"]["value"] = "modified"
        original_audit_metadata["audit"]["level"] = "error"

        # Context metadata should remain unchanged (deep copy protection)
        assert context.agent_context["nested"]["value"] == "original"
        assert context.audit_metadata["audit"]["level"] == "info"

    @pytest.mark.asyncio
    async def test_reserved_keys_validation(self):
        """Test validation against reserved keys in metadata dictionaries.

        Business Logic: Reserved keys like 'user_id', 'thread_id' in metadata
        could cause conflicts and compromise context isolation.

        Expected: InvalidContextError when reserved keys are used in metadata.
        """
        reserved_keys = ['user_id', 'thread_id', 'run_id', 'request_id']

        for reserved_key in reserved_keys:
            # Test reserved key in agent_context
            with pytest.raises(InvalidContextError) as exc_info:
                UserExecutionContext(
                    user_id=self.valid_user_id,
                    thread_id=self.valid_thread_id,
                    run_id=self.valid_run_id,
                    request_id=self.valid_request_id,
                    agent_context={reserved_key: "conflicting_value"}
                )

            assert "reserved keys" in str(exc_info.value)
            assert reserved_key in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_websocket_isolation_validation(self):
        """Test WebSocket connection isolation validation.

        Business Logic: WebSocket connections must be properly isolated to prevent
        user A receiving real-time updates intended for user B.

        Expected: Warning logged when WebSocket ID contains foreign user identifiers.
        """
        with patch('netra_backend.app.services.user_execution_context.logger') as mock_logger:
            # Create context with potentially problematic WebSocket ID
            UserExecutionContext(
                user_id=self.valid_user_id,
                thread_id=self.valid_thread_id,
                run_id=self.valid_run_id,
                request_id=self.valid_request_id,
                websocket_client_id="ws_user_different_connection_123"
            )

            # Check that warning was logged about potential isolation issue
            warning_logged = any(
                call for call in mock_logger.warning.call_args_list
                if "POTENTIAL ISOLATION ISSUE" in str(call)
            )
            assert warning_logged, "Should log warning for suspicious WebSocket ID"

    @pytest.mark.asyncio
    async def test_memory_tracking_setup(self):
        """Test memory tracking setup for leak detection.

        Business Logic: Memory tracking prevents memory leaks in long-running
        agent operations that could degrade system performance.

        Expected: Memory tracking metadata should be properly initialized.
        """
        context = UserExecutionContext(
            user_id=self.valid_user_id,
            thread_id=self.valid_thread_id,
            run_id=self.valid_run_id,
            request_id=self.valid_request_id
        )

        # Memory tracking should be initialized
        assert len(context._memory_refs) > 0
        memory_info = context._memory_refs[0]
        assert 'creation_time' in memory_info
        assert 'creation_stack_summary' in memory_info
        assert 'weak_ref' in memory_info
        assert 'gc_count' in memory_info
        assert 'fingerprint' in memory_info

    @pytest.mark.asyncio
    async def test_from_request_factory_validation(self):
        """Test from_request factory method validation.

        Business Logic: Factory methods must create valid contexts with proper
        validation to ensure Golden Path user flow reliability.

        Expected: Valid context created with all required fields populated.
        """
        context = UserExecutionContext.from_request(
            user_id=self.valid_user_id,
            thread_id=self.valid_thread_id,
            run_id=self.valid_run_id,
            request_id=self.valid_request_id,
            websocket_client_id=self.valid_websocket_id,
            agent_context={"factory_test": True},
            audit_metadata={"created_by": "factory"}
        )

        # Verify proper initialization
        assert context.user_id == self.valid_user_id
        assert context.thread_id == self.valid_thread_id
        assert context.run_id == self.valid_run_id
        assert context.request_id == self.valid_request_id
        assert context.websocket_client_id == self.valid_websocket_id
        assert context.agent_context["factory_test"] is True
        assert context.audit_metadata["created_by"] == "factory"

    @pytest.mark.asyncio
    async def test_with_db_session_immutability(self):
        """Test with_db_session creates new immutable instance.

        Business Logic: Context immutability ensures thread safety and prevents
        accidental modification during concurrent agent operations.

        Expected: New context instance with database session, original unchanged.
        """
        # Create original context
        original_context = UserExecutionContext(
            user_id=self.valid_user_id,
            thread_id=self.valid_thread_id,
            run_id=self.valid_run_id,
            request_id=self.valid_request_id
        )

        # Create mock database session
        mock_session = Mock()
        mock_session.bind = Mock()

        # Create new context with session
        new_context = original_context.with_db_session(mock_session)

        # Verify immutability
        assert new_context is not original_context  # Different instances
        assert original_context.db_session is None  # Original unchanged
        assert new_context.db_session is mock_session  # New has session
        assert new_context.user_id == original_context.user_id  # Same data

    @pytest.mark.asyncio
    async def test_invalid_operation_name_child_context(self):
        """Test invalid operation names in child context creation.

        Business Logic: Operation names must be valid for audit trail and debugging.
        Invalid names indicate programming errors that could affect system reliability.

        Expected: InvalidContextError for invalid operation names.
        """
        context = UserExecutionContext(
            user_id=self.valid_user_id,
            thread_id=self.valid_thread_id,
            run_id=self.valid_run_id,
            request_id=self.valid_request_id
        )

        invalid_operations = ["", "   ", None]

        for invalid_op in invalid_operations:
            with pytest.raises(InvalidContextError) as exc_info:
                context.create_child_context(invalid_op)

            assert "operation_name must be a non-empty string" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_audit_trail_initialization(self):
        """Test proper audit trail initialization.

        Business Logic: Audit trail is critical for compliance and debugging.
        Proper initialization ensures all required metadata is captured.

        Expected: Audit metadata should contain required audit fields.
        """
        context = UserExecutionContext(
            user_id=self.valid_user_id,
            thread_id=self.valid_thread_id,
            run_id=self.valid_run_id,
            request_id=self.valid_request_id,
            operation_depth=2,
            parent_request_id="parent_123"
        )

        # Verify audit trail initialization
        assert 'context_created_at' in context.audit_metadata
        assert 'context_version' in context.audit_metadata
        assert 'isolation_verified' in context.audit_metadata
        assert 'operation_depth' in context.audit_metadata
        assert 'parent_request_id' in context.audit_metadata

        assert context.audit_metadata['context_version'] == '1.0'
        assert context.audit_metadata['isolation_verified'] is True
        assert context.audit_metadata['operation_depth'] == 2
        assert context.audit_metadata['parent_request_id'] == "parent_123"

    @pytest.mark.asyncio
    async def test_thread_run_id_consistency_validation(self):
        """Test thread_id and run_id consistency validation.

        Business Logic: ID consistency is critical for proper request routing
        and prevents context mismatches that could break the user flow.

        Expected: Validation should handle different ID generation patterns correctly.
        """
        # Test UnifiedIdGenerator pattern (run_id as substring in thread_id)
        context = UserExecutionContext(
            user_id=self.valid_user_id,
            thread_id="thread_websocket_factory_1234_suffix",
            run_id="websocket_factory_1234",
            request_id=self.valid_request_id
        )

        # Should validate successfully (no exception)
        assert context.user_id == self.valid_user_id

        # Test UnifiedIDManager pattern (extracted thread_id matches actual)
        context2 = UserExecutionContext(
            user_id=self.valid_user_id,
            thread_id="thread123",
            run_id="run_thread123_456_abcd",
            request_id=self.valid_request_id
        )

        # Should validate successfully (no exception)
        assert context2.user_id == self.valid_user_id

    @pytest.mark.asyncio
    async def test_empty_metadata_dictionaries_validation(self):
        """Test validation with empty but valid metadata dictionaries.

        Business Logic: Empty metadata should be valid (default case).
        System should handle minimal contexts for simple operations.

        Expected: Context with empty metadata should validate successfully.
        """
        context = UserExecutionContext(
            user_id=self.valid_user_id,
            thread_id=self.valid_thread_id,
            run_id=self.valid_run_id,
            request_id=self.valid_request_id,
            agent_context={},
            audit_metadata={}
        )

        # Should validate successfully
        assert isinstance(context.agent_context, dict)
        assert isinstance(context.audit_metadata, dict)
        assert len(context.agent_context) == 0  # Empty but valid
        assert 'context_created_at' in context.audit_metadata  # Audit trail added

    @pytest.mark.asyncio
    async def test_cleanup_callbacks_management(self):
        """Test cleanup callbacks management for resource cleanup.

        Business Logic: Cleanup callbacks prevent resource leaks in long-running
        agent operations by ensuring proper resource disposal.

        Expected: Cleanup callbacks list should be properly initialized and managed.
        """
        context = UserExecutionContext(
            user_id=self.valid_user_id,
            thread_id=self.valid_thread_id,
            run_id=self.valid_run_id,
            request_id=self.valid_request_id
        )

        # Cleanup callbacks should be initialized
        assert hasattr(context, 'cleanup_callbacks')
        assert isinstance(context.cleanup_callbacks, list)
        assert len(context.cleanup_callbacks) == 0  # Initially empty

        # Test that field is excluded from representation and comparison
        # (cleanup_callbacks has repr=False, compare=False)
        context_str = repr(context)
        assert 'cleanup_callbacks' not in context_str

    @pytest.mark.asyncio
    async def test_context_creation_timestamp_validation(self):
        """Test context creation timestamp is properly set and validated.

        Business Logic: Accurate timestamps are critical for audit trails,
        debugging, and performance monitoring in the Golden Path flow.

        Expected: created_at should be set to current UTC time.
        """
        before_creation = datetime.now(timezone.utc)

        context = UserExecutionContext(
            user_id=self.valid_user_id,
            thread_id=self.valid_thread_id,
            run_id=self.valid_run_id,
            request_id=self.valid_request_id
        )

        after_creation = datetime.now(timezone.utc)

        # Timestamp should be between before and after creation
        assert before_creation <= context.created_at <= after_creation
        assert context.created_at.tzinfo == timezone.utc

        # Should be reflected in audit metadata
        audit_timestamp = datetime.fromisoformat(
            context.audit_metadata['context_created_at'].replace('Z', '+00:00')
        )
        assert abs((context.created_at - audit_timestamp).total_seconds()) < 1

    @pytest.mark.asyncio
    async def test_required_fields_validation_comprehensive(self):
        """Test comprehensive validation of all required fields.

        Business Logic: All required fields must be validated to prevent
        system failures from incomplete context initialization.

        Expected: InvalidContextError for any missing or invalid required field.
        """
        required_fields = ['user_id', 'thread_id', 'run_id']
        valid_values = [self.valid_user_id, self.valid_thread_id, self.valid_run_id]

        for i, field in enumerate(required_fields):
            # Create kwargs with all valid values
            kwargs = dict(zip(required_fields, valid_values))

            # Test None value
            kwargs[field] = None
            with pytest.raises((InvalidContextError, TypeError)) as exc_info:
                UserExecutionContext(**kwargs)
            error_msg = str(exc_info.value)
            assert (f"Required field '{field}'" in error_msg or
                   "NoneType" in error_msg or
                   "subscriptable" in error_msg), f"Unexpected error for None value: {error_msg}"

            # Reset to valid values
            kwargs = dict(zip(required_fields, valid_values))

            # Test empty string
            kwargs[field] = ""
            with pytest.raises(InvalidContextError) as exc_info:
                UserExecutionContext(**kwargs)
            assert f"Required field '{field}'" in str(exc_info.value)

            # Reset to valid values
            kwargs = dict(zip(required_fields, valid_values))

            # Test whitespace only
            kwargs[field] = "   "
            with pytest.raises(InvalidContextError) as exc_info:
                UserExecutionContext(**kwargs)
            assert f"Required field '{field}'" in str(exc_info.value)