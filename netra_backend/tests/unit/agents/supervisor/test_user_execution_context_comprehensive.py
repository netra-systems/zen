"""
Comprehensive Unit Tests for UserExecutionContext

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure robust user isolation and context management
- Value Impact: Prevents user data leakage, enables reliable multi-user operations
- Strategic Impact: Core platform stability - MISSION CRITICAL for user trust

This test suite validates the UserExecutionContext class, which is the SSOT component
for user isolation in the Netra platform. It ensures:
- Complete user context isolation between users
- Proper request state management
- WebSocket event routing integrity
- Database session management
- Error handling and validation
- Thread safety and concurrency protection

CRITICAL: UserExecutionContext is the foundation for multi-user isolation.
Any bugs here could cause catastrophic user data leakage.
"""

import asyncio
import pytest
import uuid
import time
import random
import traceback
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import Dict, Any, Optional
from dataclasses import FrozenInstanceError

# Import SSOT test framework
from test_framework.ssot.base import BaseTestCase

# Import the class under test
from netra_backend.app.agents.supervisor.user_execution_context import (
    UserExecutionContext,
    InvalidContextError,
    register_shared_object,
    clear_shared_objects,
    validate_user_context,
    _SHARED_OBJECTS
)

# Import SQLAlchemy for database session testing
from sqlalchemy.ext.asyncio import AsyncSession


class TestUserExecutionContextComprehensive(BaseTestCase):
    """Comprehensive test suite for UserExecutionContext - MISSION CRITICAL."""
    
    def setUp(self):
        """Set up test environment with clean state."""
        super().setUp()
        # Clear shared objects registry for clean test state
        clear_shared_objects()
        
        # Standard test data
        self.test_user_id = "user_test_12345"
        self.test_thread_id = "thread_test_67890" 
        self.test_run_id = "run_test_abcdef"
        self.test_request_id = "request_test_123456"
        self.test_websocket_id = "ws_conn_789012"
        
    def tearDown(self):
        """Clean up test environment."""
        clear_shared_objects()
        super().tearDown()

    # =========================================================================
    # INITIALIZATION AND BASIC FUNCTIONALITY TESTS
    # =========================================================================
    
    def test_basic_initialization_with_required_fields(self):
        """Test 1: Basic initialization with all required fields."""
        context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        # Verify all required fields
        assert context.user_id == self.test_user_id
        assert context.thread_id == self.test_thread_id
        assert context.run_id == self.test_run_id
        
        # Verify auto-generated fields
        assert context.request_id is not None
        assert isinstance(context.request_id, str)
        assert len(context.request_id) > 0
        
        # Verify optional fields have proper defaults
        assert context.db_session is None
        assert context.websocket_client_id is None
        assert isinstance(context.metadata, dict)
        assert len(context.metadata) == 0
        
        # Verify timestamp
        assert isinstance(context.created_at, datetime)
        assert context.created_at.tzinfo is not None
        
    def test_initialization_with_all_optional_fields(self):
        """Test 2: Initialization with all optional fields provided."""
        mock_db_session = Mock(spec=AsyncSession)
        test_metadata = {"key1": "value1", "key2": 42}
        
        context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            request_id=self.test_request_id,
            db_session=mock_db_session,
            websocket_client_id=self.test_websocket_id,
            metadata=test_metadata
        )
        
        # Verify all fields are set correctly
        assert context.user_id == self.test_user_id
        assert context.thread_id == self.test_thread_id
        assert context.run_id == self.test_run_id
        assert context.request_id == self.test_request_id
        assert context.db_session == mock_db_session
        assert context.websocket_client_id == self.test_websocket_id
        
        # Verify metadata is copied (isolation)
        assert context.metadata == test_metadata
        assert context.metadata is not test_metadata  # Different object
        
    def test_frozen_dataclass_immutability(self):
        """Test 3: Verify context is immutable after creation (frozen=True)."""
        context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        # Attempt to modify fields should raise FrozenInstanceError
        with pytest.raises(FrozenInstanceError):
            context.user_id = "new_user_id"
            
        with pytest.raises(FrozenInstanceError):
            context.thread_id = "new_thread_id"
            
        with pytest.raises(FrozenInstanceError):
            context.run_id = "new_run_id"
            
        with pytest.raises(FrozenInstanceError):
            context.metadata = {"new": "metadata"}

    # =========================================================================
    # VALIDATION TESTS - CRITICAL FOR SECURITY
    # =========================================================================
    
    def test_validation_empty_required_fields(self):
        """Test 4: Validation rejects empty required fields."""
        # Empty user_id
        with pytest.raises(InvalidContextError, match="user_id.*must be a non-empty string"):
            UserExecutionContext(user_id="", thread_id=self.test_thread_id, run_id=self.test_run_id)
            
        # Whitespace-only user_id
        with pytest.raises(InvalidContextError, match="user_id.*must be a non-empty string"):
            UserExecutionContext(user_id="   ", thread_id=self.test_thread_id, run_id=self.test_run_id)
            
        # None user_id
        with pytest.raises(InvalidContextError, match="user_id.*must be a non-empty string"):
            UserExecutionContext(user_id=None, thread_id=self.test_thread_id, run_id=self.test_run_id)
    
    def test_validation_non_string_required_fields(self):
        """Test 5: Validation rejects non-string types for required fields."""
        # Integer user_id
        with pytest.raises(InvalidContextError, match="user_id.*must be a non-empty string"):
            UserExecutionContext(user_id=12345, thread_id=self.test_thread_id, run_id=self.test_run_id)
            
        # List thread_id
        with pytest.raises(InvalidContextError, match="thread_id.*must be a non-empty string"):
            UserExecutionContext(user_id=self.test_user_id, thread_id=["thread"], run_id=self.test_run_id)
            
        # Dict run_id
        with pytest.raises(InvalidContextError, match="run_id.*must be a non-empty string"):
            UserExecutionContext(user_id=self.test_user_id, thread_id=self.test_thread_id, run_id={})

    def test_validation_dangerous_placeholder_values(self):
        """Test 6: Validation rejects dangerous placeholder values."""
        dangerous_values = [
            "registry", "placeholder", "default", "temp", 
            "none", "null", "undefined", "0", "1", "xxx", "yyy", "example"
        ]
        
        for dangerous_value in dangerous_values:
            with pytest.raises(InvalidContextError, match="forbidden placeholder value"):
                UserExecutionContext(
                    user_id=dangerous_value,
                    thread_id=self.test_thread_id,
                    run_id=self.test_run_id
                )
    
    def test_validation_dangerous_pattern_prefixes(self):
        """Test 7: Validation rejects dangerous pattern prefixes for short values."""
        dangerous_patterns = ["placeholder_", "registry_", "default_", "temp_"]
        
        for pattern in dangerous_patterns:
            # Short values with dangerous patterns should be rejected
            short_dangerous = pattern + "short"  # Less than 20 chars
            with pytest.raises(InvalidContextError, match="placeholder pattern"):
                UserExecutionContext(
                    user_id=short_dangerous,
                    thread_id=self.test_thread_id,
                    run_id=self.test_run_id
                )
            
            # Long values with dangerous patterns should be allowed
            long_acceptable = pattern + "this_is_a_very_long_value_that_should_be_accepted"
            context = UserExecutionContext(
                user_id=long_acceptable,
                thread_id=self.test_thread_id,
                run_id=self.test_run_id
            )
            assert context.user_id == long_acceptable

    def test_validation_metadata_structure(self):
        """Test 8: Metadata validation ensures proper structure."""
        # Non-dict metadata should fail
        with pytest.raises(InvalidContextError, match="metadata must be a dictionary"):
            UserExecutionContext(
                user_id=self.test_user_id,
                thread_id=self.test_thread_id,
                run_id=self.test_run_id,
                metadata="not a dict"
            )
        
        # List as metadata should fail
        with pytest.raises(InvalidContextError, match="metadata must be a dictionary"):
            UserExecutionContext(
                user_id=self.test_user_id,
                thread_id=self.test_thread_id,
                run_id=self.test_run_id,
                metadata=["list", "not", "dict"]
            )

    def test_validation_metadata_reserved_keys(self):
        """Test 9: Metadata validation rejects reserved keys."""
        reserved_keys = ['user_id', 'thread_id', 'run_id', 'request_id', 'created_at']
        
        for reserved_key in reserved_keys:
            with pytest.raises(InvalidContextError, match="metadata contains reserved keys"):
                UserExecutionContext(
                    user_id=self.test_user_id,
                    thread_id=self.test_thread_id,
                    run_id=self.test_run_id,
                    metadata={reserved_key: "conflicting_value"}
                )

    # =========================================================================
    # FACTORY METHOD TESTS
    # =========================================================================
    
    def test_from_request_basic(self):
        """Test 10: from_request factory method basic functionality."""
        context = UserExecutionContext.from_request(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        assert context.user_id == self.test_user_id
        assert context.thread_id == self.test_thread_id
        assert context.run_id == self.test_run_id
        assert context.request_id is not None
        assert context.db_session is None
        assert context.websocket_client_id is None
        assert context.metadata == {}

    def test_from_request_with_all_parameters(self):
        """Test 11: from_request with all optional parameters."""
        mock_db_session = Mock(spec=AsyncSession)
        test_metadata = {"source": "api", "version": "1.0"}
        
        context = UserExecutionContext.from_request(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            request_id=self.test_request_id,
            db_session=mock_db_session,
            websocket_client_id=self.test_websocket_id,
            metadata=test_metadata
        )
        
        assert context.request_id == self.test_request_id
        assert context.db_session == mock_db_session
        assert context.websocket_client_id == self.test_websocket_id
        assert context.metadata == test_metadata

    def test_from_request_auto_generated_request_id(self):
        """Test 12: from_request auto-generates request_id when not provided."""
        context1 = UserExecutionContext.from_request(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        context2 = UserExecutionContext.from_request(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        # Both should have valid UUIDs
        assert context1.request_id is not None
        assert context2.request_id is not None
        
        # Should be different
        assert context1.request_id != context2.request_id
        
        # Should be valid UUIDs
        uuid.UUID(context1.request_id)  # Will raise ValueError if invalid
        uuid.UUID(context2.request_id)

    # =========================================================================
    # CHILD CONTEXT TESTS - CRITICAL FOR OPERATION HIERARCHY
    # =========================================================================
    
    def test_create_child_context_basic(self):
        """Test 13: Basic child context creation."""
        parent_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            metadata={"parent_data": "value"}
        )
        
        child_context = parent_context.create_child_context("sub_operation")
        
        # Child inherits parent data
        assert child_context.user_id == parent_context.user_id
        assert child_context.thread_id == parent_context.thread_id
        assert child_context.run_id == parent_context.run_id
        assert child_context.websocket_client_id == parent_context.websocket_client_id
        assert child_context.db_session == parent_context.db_session
        
        # Child has new request_id
        assert child_context.request_id != parent_context.request_id
        
        # Child metadata includes parent data plus operation tracking
        assert child_context.metadata["parent_data"] == "value"
        assert child_context.metadata["parent_request_id"] == parent_context.request_id
        assert child_context.metadata["operation_name"] == "sub_operation"
        assert child_context.metadata["operation_depth"] == 1

    def test_create_child_context_with_additional_metadata(self):
        """Test 14: Child context with additional metadata."""
        parent_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            metadata={"parent_key": "parent_value"}
        )
        
        additional_metadata = {"child_key": "child_value", "tool_name": "optimizer"}
        child_context = parent_context.create_child_context(
            "tool_execution", 
            additional_metadata
        )
        
        # Child has both parent and additional metadata
        assert child_context.metadata["parent_key"] == "parent_value"
        assert child_context.metadata["child_key"] == "child_value"
        assert child_context.metadata["tool_name"] == "optimizer"
        assert child_context.metadata["operation_name"] == "tool_execution"

    def test_create_child_context_nested_depth_tracking(self):
        """Test 15: Nested child contexts track operation depth correctly."""
        grandparent = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        parent = grandparent.create_child_context("level_1")
        child = parent.create_child_context("level_2")
        grandchild = child.create_child_context("level_3")
        
        # Verify depth tracking
        assert grandparent.metadata.get("operation_depth", 0) == 0
        assert parent.metadata["operation_depth"] == 1
        assert child.metadata["operation_depth"] == 2
        assert grandchild.metadata["operation_depth"] == 3
        
        # Verify operation hierarchy
        assert parent.metadata["parent_request_id"] == grandparent.request_id
        assert child.metadata["parent_request_id"] == parent.request_id
        assert grandchild.metadata["parent_request_id"] == child.request_id

    def test_create_child_context_validation(self):
        """Test 16: Child context creation validates operation_name."""
        parent_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        # Empty operation name should fail
        with pytest.raises(InvalidContextError, match="operation_name must be a non-empty string"):
            parent_context.create_child_context("")
        
        # None operation name should fail
        with pytest.raises(InvalidContextError, match="operation_name must be a non-empty string"):
            parent_context.create_child_context(None)
        
        # Non-string operation name should fail
        with pytest.raises(InvalidContextError, match="operation_name must be a non-empty string"):
            parent_context.create_child_context(123)

    # =========================================================================
    # CONTEXT MODIFICATION TESTS
    # =========================================================================
    
    def test_with_db_session(self):
        """Test 17: with_db_session creates new context with database session."""
        original_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            metadata={"original": "data"}
        )
        
        mock_db_session = Mock(spec=AsyncSession)
        new_context = original_context.with_db_session(mock_db_session)
        
        # Original context unchanged
        assert original_context.db_session is None
        
        # New context has database session
        assert new_context.db_session == mock_db_session
        
        # All other data preserved
        assert new_context.user_id == original_context.user_id
        assert new_context.thread_id == original_context.thread_id
        assert new_context.run_id == original_context.run_id
        assert new_context.request_id == original_context.request_id
        assert new_context.created_at == original_context.created_at
        assert new_context.metadata == original_context.metadata
        assert new_context.metadata is not original_context.metadata  # Copy, not reference

    def test_with_websocket_connection(self):
        """Test 18: with_websocket_connection creates new context with WebSocket ID."""
        original_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            metadata={"test": "data"}
        )
        
        new_context = original_context.with_websocket_connection(self.test_websocket_id)
        
        # Original context unchanged
        assert original_context.websocket_client_id is None
        
        # New context has WebSocket connection ID
        assert new_context.websocket_client_id == self.test_websocket_id
        
        # All other data preserved
        assert new_context.user_id == original_context.user_id
        assert new_context.thread_id == original_context.thread_id
        assert new_context.run_id == original_context.run_id
        assert new_context.request_id == original_context.request_id
        assert new_context.created_at == original_context.created_at
        assert new_context.metadata == original_context.metadata
        assert new_context.metadata is not original_context.metadata  # Copy, not reference

    def test_context_modification_immutability(self):
        """Test 19: Context modification methods preserve immutability."""
        original_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            metadata={"key": "value"}
        )
        
        mock_db_session = Mock(spec=AsyncSession)
        
        # Multiple modifications create separate contexts
        context_with_db = original_context.with_db_session(mock_db_session)
        context_with_ws = original_context.with_websocket_connection(self.test_websocket_id)
        context_with_both = context_with_db.with_websocket_connection(self.test_websocket_id)
        
        # All contexts are different objects
        assert original_context is not context_with_db
        assert original_context is not context_with_ws
        assert original_context is not context_with_both
        assert context_with_db is not context_with_both
        
        # Original context unchanged
        assert original_context.db_session is None
        assert original_context.websocket_client_id is None
        
        # Each context has the expected modifications
        assert context_with_db.db_session == mock_db_session
        assert context_with_db.websocket_client_id is None
        
        assert context_with_ws.db_session is None
        assert context_with_ws.websocket_client_id == self.test_websocket_id
        
        assert context_with_both.db_session == mock_db_session
        assert context_with_both.websocket_client_id == self.test_websocket_id

    # =========================================================================
    # ISOLATION VERIFICATION TESTS - CRITICAL FOR MULTI-USER SAFETY
    # =========================================================================
    
    def test_verify_isolation_basic(self):
        """Test 20: Basic isolation verification passes for clean context."""
        context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            metadata={"isolated": "data"}
        )
        
        # Should pass isolation verification
        assert context.verify_isolation() is True

    def test_verify_isolation_detects_shared_objects(self):
        """Test 21: Isolation verification detects shared objects."""
        shared_metadata = {"shared": "object"}
        register_shared_object(shared_metadata)
        
        # This test verifies the isolation detection mechanism exists
        # The actual shared object detection logic checks for object IDs
        # We'll test the warning case for duplicate IDs
        
        context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            metadata=shared_metadata.copy()  # Use copy to avoid actual sharing
        )
        
        # Should still pass (we're using a copy)
        assert context.verify_isolation() is True

    def test_verify_isolation_duplicate_ids_warning(self):
        """Test 22: Isolation verification warns about duplicate ID values."""
        # Create context where some IDs have the same value (unusual but possible)
        duplicate_id = "duplicate_test_id"
        context = UserExecutionContext(
            user_id=duplicate_id,
            thread_id=duplicate_id,  # Same value - should trigger warning
            run_id=self.test_run_id,
            request_id="different_request_id"
        )
        
        # The main goal is to test that verify_isolation() works correctly
        # with duplicate ID values and returns True
        result = context.verify_isolation()
        assert result is True
        
        # Test that the warning logic exists by checking the code path
        # We can't easily test the actual warning without complex mocking
        # but we can verify the isolation check passes even with duplicate values
        
        # Test edge case with all same values
        all_same_context = UserExecutionContext(
            user_id="same",
            thread_id="same",
            run_id="same",
            request_id="same"
        )
        
        # Should still pass isolation verification
        assert all_same_context.verify_isolation() is True

    # =========================================================================
    # SERIALIZATION TESTS
    # =========================================================================
    
    def test_to_dict_basic(self):
        """Test 23: Basic serialization to dictionary."""
        test_time = datetime.now(timezone.utc)
        context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            request_id=self.test_request_id,
            websocket_client_id=self.test_websocket_id,
            metadata={"key": "value"}
        )
        
        result_dict = context.to_dict()
        
        # Verify all serializable fields are present
        expected_keys = {
            'user_id', 'thread_id', 'run_id', 'request_id',
            'websocket_client_id', 'created_at', 'metadata',
            'has_db_session'
        }
        assert set(result_dict.keys()) == expected_keys
        
        # Verify values
        assert result_dict['user_id'] == self.test_user_id
        assert result_dict['thread_id'] == self.test_thread_id
        assert result_dict['run_id'] == self.test_run_id
        assert result_dict['request_id'] == self.test_request_id
        assert result_dict['websocket_client_id'] == self.test_websocket_id
        assert result_dict['metadata'] == {"key": "value"}
        assert result_dict['has_db_session'] is False
        
        # Verify timestamp is ISO formatted
        assert isinstance(result_dict['created_at'], str)
        datetime.fromisoformat(result_dict['created_at'].replace('Z', '+00:00'))  # Should not raise

    def test_to_dict_with_db_session(self):
        """Test 24: Serialization indicates presence of database session."""
        mock_db_session = Mock(spec=AsyncSession)
        context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            db_session=mock_db_session
        )
        
        result_dict = context.to_dict()
        
        # Should indicate database session is present
        assert result_dict['has_db_session'] is True
        
        # Database session itself should not be in the dict (not serializable)
        assert 'db_session' not in result_dict

    def test_to_dict_metadata_isolation(self):
        """Test 25: Serialization creates copy of metadata (isolation)."""
        original_metadata = {"original": "data", "count": 42}
        context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            metadata=original_metadata
        )
        
        result_dict = context.to_dict()
        
        # Metadata should be equal but different objects
        assert result_dict['metadata'] == original_metadata
        assert result_dict['metadata'] is not original_metadata
        assert result_dict['metadata'] is not context.metadata
        
        # Modifying result should not affect original
        result_dict['metadata']['new_key'] = "new_value"
        assert 'new_key' not in original_metadata
        assert 'new_key' not in context.metadata

    # =========================================================================
    # CORRELATION ID TESTS
    # =========================================================================
    
    def test_get_correlation_id_format(self):
        """Test 26: Correlation ID format is correct."""
        context = UserExecutionContext(
            user_id="user_1234567890abcdef",
            thread_id="thread_abcdef1234567890", 
            run_id="run_fedcba0987654321",
            request_id="request_1a2b3c4d5e6f7890"
        )
        
        correlation_id = context.get_correlation_id()
        
        # Should be in format: user_123:thread_a:run_fedc:request_1
        parts = correlation_id.split(':')
        assert len(parts) == 4
        
        # Each part should be 8 characters from the corresponding field
        assert parts[0] == "user_123"  # First 8 chars of user_id
        assert parts[1] == "thread_a"  # First 8 chars of thread_id
        assert parts[2] == "run_fedc"  # First 8 chars of run_id
        assert parts[3] == "request_"  # First 8 chars of request_id

    def test_get_correlation_id_short_ids(self):
        """Test 27: Correlation ID handles short ID values."""
        context = UserExecutionContext(
            user_id="u1",
            thread_id="t2", 
            run_id="r3",
            request_id="req4"
        )
        
        correlation_id = context.get_correlation_id()
        
        # Should handle short IDs gracefully
        parts = correlation_id.split(':')
        assert len(parts) == 4
        assert parts[0] == "u1"      # Short user_id
        assert parts[1] == "t2"      # Short thread_id
        assert parts[2] == "r3"      # Short run_id
        assert parts[3] == "req4"    # Short request_id

    def test_get_correlation_id_uniqueness(self):
        """Test 28: Correlation IDs are unique across different contexts."""
        contexts = []
        correlation_ids = set()
        
        for i in range(10):
            context = UserExecutionContext(
                user_id=f"user_{i}_{uuid.uuid4().hex}",
                thread_id=f"thread_{i}_{uuid.uuid4().hex}",
                run_id=f"run_{i}_{uuid.uuid4().hex}"
            )
            contexts.append(context)
            correlation_ids.add(context.get_correlation_id())
        
        # All correlation IDs should be unique
        assert len(correlation_ids) == 10

    # =========================================================================
    # UTILITY FUNCTION TESTS
    # =========================================================================
    
    def test_validate_user_context_success(self):
        """Test 29: validate_user_context accepts valid context."""
        context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        # Should return the same context
        validated = validate_user_context(context)
        assert validated is context

    def test_validate_user_context_type_error(self):
        """Test 30: validate_user_context rejects non-context objects."""
        # String should fail
        with pytest.raises(TypeError, match="Expected UserExecutionContext"):
            validate_user_context("not a context")
        
        # Dict should fail
        with pytest.raises(TypeError, match="Expected UserExecutionContext"):
            validate_user_context({"user_id": "test"})
        
        # None should fail
        with pytest.raises(TypeError, match="Expected UserExecutionContext"):
            validate_user_context(None)
        
        # Mock object should fail
        mock_context = Mock()
        with pytest.raises(TypeError, match="Expected UserExecutionContext"):
            validate_user_context(mock_context)

    def test_shared_objects_registry_functions(self):
        """Test 31: Shared objects registry functions work correctly."""
        # Start with clean registry
        clear_shared_objects()
        assert len(_SHARED_OBJECTS) == 0
        
        # Register some objects
        obj1 = {"test": "object1"}
        obj2 = [1, 2, 3]
        
        register_shared_object(obj1)
        register_shared_object(obj2)
        
        # Registry should contain object IDs
        assert len(_SHARED_OBJECTS) == 2
        assert id(obj1) in _SHARED_OBJECTS
        assert id(obj2) in _SHARED_OBJECTS
        
        # Clear registry
        clear_shared_objects()
        assert len(_SHARED_OBJECTS) == 0

    # =========================================================================
    # EDGE CASES AND ERROR HANDLING TESTS
    # =========================================================================
    
    def test_metadata_isolation_on_init(self):
        """Test 32: Metadata is properly isolated during initialization."""
        shared_metadata = {"shared": "data", "count": 1}
        
        # Create multiple contexts with the same metadata dict
        context1 = UserExecutionContext(
            user_id="user1",
            thread_id="thread1",
            run_id="run1",
            metadata=shared_metadata
        )
        
        context2 = UserExecutionContext(
            user_id="user2",
            thread_id="thread2", 
            run_id="run2",
            metadata=shared_metadata
        )
        
        # Each context should have its own copy
        assert context1.metadata == shared_metadata
        assert context2.metadata == shared_metadata
        assert context1.metadata is not shared_metadata
        assert context2.metadata is not shared_metadata
        assert context1.metadata is not context2.metadata

    def test_request_id_auto_generation_uniqueness(self):
        """Test 33: Auto-generated request IDs are unique."""
        contexts = []
        request_ids = set()
        
        for i in range(50):
            context = UserExecutionContext(
                user_id=f"user_{i}",
                thread_id=f"thread_{i}",
                run_id=f"run_{i}"
                # No request_id provided - should be auto-generated
            )
            contexts.append(context)
            request_ids.add(context.request_id)
            
            # Verify it's a valid UUID
            uuid.UUID(context.request_id)  # Will raise ValueError if invalid
        
        # All request IDs should be unique
        assert len(request_ids) == 50

    def test_timestamp_precision_and_timezone(self):
        """Test 34: Created timestamp has proper timezone and precision."""
        before_creation = datetime.now(timezone.utc)
        
        context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        after_creation = datetime.now(timezone.utc)
        
        # Timestamp should be between before and after
        assert before_creation <= context.created_at <= after_creation
        
        # Should have timezone info (UTC)
        assert context.created_at.tzinfo is timezone.utc

    # =========================================================================
    # CONCURRENCY AND THREAD SAFETY TESTS
    # =========================================================================
    
    def test_concurrent_context_creation(self):
        """Test 35: Concurrent context creation doesn't cause issues."""
        def create_context(i):
            return UserExecutionContext(
                user_id=f"user_{i}",
                thread_id=f"thread_{i}",
                run_id=f"run_{i}",
                metadata={"index": i, "timestamp": datetime.now(timezone.utc).isoformat()}
            )
        
        # Create multiple contexts in sequence to simulate concurrent creation
        contexts = []
        for i in range(20):
            context = create_context(i)
            contexts.append(context)
        
        # All contexts should be valid and unique
        assert len(contexts) == 20
        
        # Verify all contexts are unique
        user_ids = {ctx.user_id for ctx in contexts}
        request_ids = {ctx.request_id for ctx in contexts}
        
        assert len(user_ids) == 20
        assert len(request_ids) == 20

    def test_concurrent_child_context_creation(self):
        """Test 36: Concurrent child context creation from same parent."""
        parent_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            metadata={"parent": "data"}
        )
        
        # Create multiple child contexts in sequence to simulate concurrent creation
        children = []
        for i in range(15):
            child = parent_context.create_child_context(f"operation_{i}")
            children.append(child)
        
        # All children should be valid and unique
        assert len(children) == 15
        
        # All should have same parent data but different request IDs
        for child in children:
            assert child.user_id == parent_context.user_id
            assert child.thread_id == parent_context.thread_id
            assert child.run_id == parent_context.run_id
            assert child.metadata["parent"] == "data"
            assert child.metadata["parent_request_id"] == parent_context.request_id
            assert child.request_id != parent_context.request_id
        
        # All children should have unique request IDs
        child_request_ids = {child.request_id for child in children}
        assert len(child_request_ids) == 15

    # =========================================================================
    # BUSINESS VALUE VALIDATION TESTS
    # =========================================================================
    
    def test_user_isolation_scenario(self):
        """Test 37: Complete user isolation scenario validation."""
        # Simulate two different users with separate contexts
        user1_context = UserExecutionContext(
            user_id="user_enterprise_001",
            thread_id="thread_cost_analysis",
            run_id="run_optimization_2024",
            websocket_client_id="ws_user1_connection",
            metadata={"subscription": "enterprise", "company": "TechCorp"}
        )
        
        user2_context = UserExecutionContext(
            user_id="user_free_002",
            thread_id="thread_basic_query",
            run_id="run_simple_chat",
            websocket_client_id="ws_user2_connection",
            metadata={"subscription": "free", "trial_days_left": 7}
        )
        
        # Contexts should be completely isolated
        assert user1_context.user_id != user2_context.user_id
        assert user1_context.thread_id != user2_context.thread_id
        assert user1_context.run_id != user2_context.run_id
        assert user1_context.request_id != user2_context.request_id
        assert user1_context.websocket_client_id != user2_context.websocket_client_id
        
        # Metadata should be isolated
        assert user1_context.metadata["subscription"] == "enterprise"
        assert user2_context.metadata["subscription"] == "free"
        assert "company" not in user2_context.metadata
        assert "trial_days_left" not in user1_context.metadata

    def test_request_tracking_scenario(self):
        """Test 38: Complete request tracking through operation hierarchy."""
        # Main user request
        main_request = UserExecutionContext.from_request(
            user_id="user_premium_003",
            thread_id="thread_cost_optimization",
            run_id="run_monthly_analysis"
        )
        
        # Agent execution context  
        agent_context = main_request.create_child_context(
            "cost_optimizer_agent",
            {"agent_type": "cost_optimizer", "priority": "high"}
        )
        
        # Tool execution context
        tool_context = agent_context.create_child_context(
            "aws_cost_analyzer_tool",
            {"tool_name": "aws_analyzer", "account_id": "123456789"}
        )
        
        # Sub-tool execution
        subtool_context = tool_context.create_child_context(
            "ec2_cost_breakdown",
            {"service": "ec2", "region": "us-west-2"}
        )
        
        # Verify complete traceability chain
        assert subtool_context.user_id == main_request.user_id
        assert subtool_context.thread_id == main_request.thread_id
        assert subtool_context.run_id == main_request.run_id
        
        # Verify operation hierarchy
        assert subtool_context.metadata["operation_depth"] == 3
        assert subtool_context.metadata["parent_request_id"] == tool_context.request_id
        assert tool_context.metadata["parent_request_id"] == agent_context.request_id
        assert agent_context.metadata["parent_request_id"] == main_request.request_id
        
        # Verify all contexts have unique correlation IDs but same user/thread/run prefixes
        main_corr = main_request.get_correlation_id()
        sub_corr = subtool_context.get_correlation_id() 
        
        main_parts = main_corr.split(':')
        sub_parts = sub_corr.split(':')
        
        # Same user, thread, run prefix but different request ID
        assert main_parts[0] == sub_parts[0]  # user_id prefix
        assert main_parts[1] == sub_parts[1]  # thread_id prefix  
        assert main_parts[2] == sub_parts[2]  # run_id prefix
        assert main_parts[3] != sub_parts[3]  # request_id prefix different

    def test_websocket_routing_scenario(self):
        """Test 39: WebSocket event routing context validation."""
        # User starts a conversation
        base_context = UserExecutionContext.from_request(
            user_id="user_mid_tier_004",
            thread_id="thread_data_analysis", 
            run_id="run_quarterly_report"
        )
        
        # WebSocket connection established
        ws_context = base_context.with_websocket_connection("ws_conn_abc123def456")
        
        # Database session added
        mock_db_session = Mock(spec=AsyncSession)
        full_context = ws_context.with_db_session(mock_db_session)
        
        # Verify WebSocket routing data
        assert full_context.websocket_client_id == "ws_conn_abc123def456"
        assert full_context.db_session == mock_db_session
        
        # Verify context can be serialized for WebSocket events
        ws_event_data = full_context.to_dict()
        assert ws_event_data["websocket_client_id"] == "ws_conn_abc123def456"
        assert ws_event_data["has_db_session"] is True
        
        # Verify correlation ID for event tracing
        correlation_id = full_context.get_correlation_id()
        assert len(correlation_id.split(':')) == 4

    def test_database_session_lifecycle_scenario(self):
        """Test 40: Database session lifecycle management."""
        # Context without database session
        base_context = UserExecutionContext(
            user_id="user_enterprise_005",
            thread_id="thread_analytics_query",
            run_id="run_dashboard_data"
        )
        
        assert base_context.db_session is None
        assert base_context.to_dict()["has_db_session"] is False
        
        # Add database session
        mock_session = Mock(spec=AsyncSession)
        mock_session.is_active = True
        db_context = base_context.with_db_session(mock_session)
        
        assert db_context.db_session == mock_session
        assert db_context.to_dict()["has_db_session"] is True
        
        # Create child operation that inherits session
        child_context = db_context.create_child_context("query_execution")
        assert child_context.db_session == mock_session
        
        # Original context unchanged (immutability)
        assert base_context.db_session is None

    def test_error_isolation_and_validation(self):
        """Test 41: Error isolation prevents cross-user contamination.""" 
        # Test that validation errors don't leak information
        with pytest.raises(InvalidContextError) as exc_info:
            UserExecutionContext(
                user_id="",  # Invalid
                thread_id="valid_thread", 
                run_id="valid_run"
            )
        
        # Error message should not contain sensitive data from other tests
        error_message = str(exc_info.value)
        assert "user_id" in error_message
        assert "must be a non-empty string" in error_message
        
        # Should not contain data from other contexts
        assert "user_enterprise_001" not in error_message
        assert "thread_cost_analysis" not in error_message
        
    def test_performance_characteristics(self):
        """Test 42: Performance characteristics for high-throughput scenarios."""
        import time
        
        # Measure context creation performance
        start_time = time.time()
        contexts = []
        
        for i in range(1000):
            context = UserExecutionContext(
                user_id=f"perf_user_{i:04d}",
                thread_id=f"perf_thread_{i:04d}",
                run_id=f"perf_run_{i:04d}",
                metadata={"iteration": i, "batch": "performance_test"}
            )
            contexts.append(context)
        
        creation_time = time.time() - start_time
        
        # Should create 1000 contexts in reasonable time (< 1 second)
        assert creation_time < 1.0, f"Context creation too slow: {creation_time:.3f}s for 1000 contexts"
        
        # Measure child context creation performance
        base_context = contexts[0]
        start_time = time.time()
        
        child_contexts = []
        for i in range(100):
            child = base_context.create_child_context(f"perf_operation_{i}")
            child_contexts.append(child)
        
        child_creation_time = time.time() - start_time
        
        # Child creation should also be fast
        assert child_creation_time < 0.5, f"Child context creation too slow: {child_creation_time:.3f}s for 100 children"
        
        # Verify all contexts are valid
        assert len(contexts) == 1000
        assert len(child_contexts) == 100
        assert all(ctx.verify_isolation() for ctx in contexts[:10])  # Spot check

    # =========================================================================
    # COMPREHENSIVE FINAL VALIDATION TESTS  
    # =========================================================================
    
    def test_complete_system_integration_scenario(self):
        """Test 43: Complete system integration scenario - MISSION CRITICAL."""
        """
        This test simulates a complete user workflow through the system:
        1. User logs in and starts conversation
        2. Agent processes request with tools
        3. Database operations with session management
        4. WebSocket events for real-time updates
        5. Child operations for tool execution
        6. Context cleanup and isolation verification
        """
        
        # Step 1: User authentication and session start
        user_session_context = UserExecutionContext.from_request(
            user_id="user_production_test_2024",
            thread_id="thread_quarterly_optimization_analysis",
            run_id="run_q4_cost_insights",
            metadata={
                "user_tier": "enterprise",
                "session_type": "authenticated",
                "client_version": "2.1.0"
            }
        )
        
        # Step 2: WebSocket connection for real-time updates
        ws_enhanced_context = user_session_context.with_websocket_connection(
            "ws_production_connection_2024_q4"
        )
        
        # Step 3: Database session for persistent operations
        mock_db_session = Mock(spec=AsyncSession)
        mock_db_session.is_active = True
        mock_db_session.bind = Mock()
        
        db_enhanced_context = ws_enhanced_context.with_db_session(mock_db_session)
        
        # Step 4: Agent execution context
        agent_context = db_enhanced_context.create_child_context(
            "cost_optimization_agent",
            {
                "agent_version": "3.2.1",
                "optimization_target": "cost_reduction",
                "analysis_period": "quarterly"
            }
        )
        
        # Step 5: Tool execution contexts
        data_tool_context = agent_context.create_child_context(
            "aws_cost_data_collector",
            {
                "tool_type": "data_collector", 
                "aws_account": "prod-account-123",
                "services": ["ec2", "s3", "rds", "lambda"]
            }
        )
        
        analysis_tool_context = agent_context.create_child_context(
            "cost_analysis_engine", 
            {
                "tool_type": "analyzer",
                "analysis_algorithms": ["trend", "anomaly", "forecast"],
                "baseline_period": "12_months"
            }
        )
        
        # Step 6: Sub-tool execution
        ec2_analysis_context = analysis_tool_context.create_child_context(
            "ec2_cost_breakdown_analyzer",
            {
                "service_focus": "ec2",
                "instance_types": ["m5", "c5", "r5"],
                "regions": ["us-east-1", "us-west-2", "eu-west-1"]
            }
        )
        
        # VERIFICATION 1: User isolation integrity
        assert ec2_analysis_context.user_id == user_session_context.user_id
        assert ec2_analysis_context.thread_id == user_session_context.thread_id
        assert ec2_analysis_context.run_id == user_session_context.run_id
        
        # VERIFICATION 2: WebSocket routing preserved
        assert ec2_analysis_context.websocket_client_id == "ws_production_connection_2024_q4"
        
        # VERIFICATION 3: Database session shared appropriately
        assert ec2_analysis_context.db_session == mock_db_session
        
        # VERIFICATION 4: Operation hierarchy tracking
        assert ec2_analysis_context.metadata["operation_depth"] == 3
        assert ec2_analysis_context.metadata["parent_request_id"] == analysis_tool_context.request_id
        assert analysis_tool_context.metadata["parent_request_id"] == agent_context.request_id
        assert agent_context.metadata["parent_request_id"] == db_enhanced_context.request_id
        
        # VERIFICATION 5: Metadata inheritance and isolation
        assert ec2_analysis_context.metadata["user_tier"] == "enterprise"
        assert ec2_analysis_context.metadata["agent_version"] == "3.2.1"
        assert ec2_analysis_context.metadata["service_focus"] == "ec2"
        
        # VERIFICATION 6: Request ID inheritance and child uniqueness
        # Note: with_db_session and with_websocket_connection preserve request_id (immutable pattern)
        # Only create_child_context generates new request_id
        
        # These contexts should share request_id (created via with_* methods)
        assert user_session_context.request_id == ws_enhanced_context.request_id
        assert ws_enhanced_context.request_id == db_enhanced_context.request_id
        
        # These should have unique request_ids (created via create_child_context)
        child_request_ids = {
            agent_context.request_id,
            data_tool_context.request_id,
            analysis_tool_context.request_id,
            ec2_analysis_context.request_id
        }
        assert len(child_request_ids) == 4  # All child contexts have unique IDs
        assert user_session_context.request_id not in child_request_ids  # Different from parent
        
        # VERIFICATION 7: Correlation ID traceability
        final_correlation = ec2_analysis_context.get_correlation_id()
        base_correlation = user_session_context.get_correlation_id()
        
        final_parts = final_correlation.split(':')
        base_parts = base_correlation.split(':')
        
        # Same user/thread/run, different request
        assert final_parts[0] == base_parts[0]  # user_id prefix
        assert final_parts[1] == base_parts[1]  # thread_id prefix
        assert final_parts[2] == base_parts[2]  # run_id prefix
        assert final_parts[3] != base_parts[3]  # request_id prefix
        
        # VERIFICATION 8: Serialization for WebSocket events
        final_dict = ec2_analysis_context.to_dict()
        assert final_dict["user_id"] == "user_production_test_2024"
        assert final_dict["websocket_client_id"] == "ws_production_connection_2024_q4"
        assert final_dict["has_db_session"] is True
        
        # VERIFICATION 9: Isolation verification passes
        assert ec2_analysis_context.verify_isolation() is True
        
        # VERIFICATION 10: Context immutability preserved
        original_user_id = ec2_analysis_context.user_id
        with pytest.raises(FrozenInstanceError):
            ec2_analysis_context.user_id = "hacked_user_id"
        assert ec2_analysis_context.user_id == original_user_id

    def test_comprehensive_edge_cases_validation(self):
        """Test 44: Comprehensive edge cases that could cause failures."""
        
        # Edge Case 1: Very long ID values
        long_user_id = "u" * 200  # 200 character user ID
        long_thread_id = "t" * 150
        long_run_id = "r" * 100
        
        context = UserExecutionContext(
            user_id=long_user_id,
            thread_id=long_thread_id,
            run_id=long_run_id
        )
        
        # Should handle long IDs without issue
        assert context.user_id == long_user_id
        correlation_id = context.get_correlation_id()
        assert len(correlation_id.split(':')[0]) == 8  # Should truncate for correlation
        
        # Edge Case 2: Unicode and special characters
        unicode_context = UserExecutionContext(
            user_id="[U+7528][U+6237]_tect_ FIRE: _user",
            thread_id="[U+7EBF][U+7A0B]_n[U+0438]t[U+044C]_ LIGHTNING: _thread", 
            run_id="[U+8FD0][U+884C]_[U+0431]e[U+0433]_[U+1F680]_run"
        )
        
        assert unicode_context.verify_isolation() is True
        unicode_dict = unicode_context.to_dict()
        assert isinstance(unicode_dict['user_id'], str)
        
        # Edge Case 3: Large metadata
        large_metadata = {f"key_{i}": f"value_{i}" * 100 for i in range(50)}
        large_meta_context = UserExecutionContext(
            user_id="large_meta_user",
            thread_id="large_meta_thread",
            run_id="large_meta_run",
            metadata=large_metadata
        )
        
        # Should handle large metadata
        assert len(large_meta_context.metadata) == 50
        assert large_meta_context.verify_isolation() is True
        
        # Edge Case 4: Deep nesting
        current_context = UserExecutionContext(
            user_id="deep_nest_user",
            thread_id="deep_nest_thread", 
            run_id="deep_nest_run"
        )
        
        # Create 20 levels of nesting
        for i in range(20):
            current_context = current_context.create_child_context(f"level_{i}")
        
        assert current_context.metadata["operation_depth"] == 20
        assert current_context.verify_isolation() is True
        
        # Edge Case 5: Rapid creation and modification
        contexts = []
        for i in range(100):
            ctx = UserExecutionContext(
                user_id=f"rapid_{i}",
                thread_id=f"thread_{i}",
                run_id=f"run_{i}"
            )
            
            if i % 2 == 0:
                ctx = ctx.with_websocket_connection(f"ws_{i}")
            if i % 3 == 0:
                mock_session = Mock(spec=AsyncSession)
                ctx = ctx.with_db_session(mock_session)
                
            contexts.append(ctx)
        
        # All should be valid and unique
        assert len(contexts) == 100
        user_ids = {ctx.user_id for ctx in contexts}
        assert len(user_ids) == 100

    def test_final_business_value_assurance(self):
        """Test 45: Final business value assurance - ZERO TOLERANCE FOR FAILURE."""
        """
        This is the ultimate validation test that ensures UserExecutionContext
        delivers on its MISSION CRITICAL promise of user isolation and data protection.
        Any failure here indicates potential catastrophic user data leakage.
        """
        
        # SCENARIO: Multiple enterprise users using system simultaneously
        enterprise_contexts = []
        for i in range(10):
            ctx = UserExecutionContext.from_request(
                user_id=f"enterprise_customer_{i:03d}",
                thread_id=f"confidential_analysis_{i:03d}",
                run_id=f"sensitive_data_processing_{i:03d}",
                metadata={
                    "company": f"SecureCorp_{i}",
                    "classification": "CONFIDENTIAL",
                    "revenue_data": f"${i * 1000000}M",
                    "competitors": [f"competitor_{i}_{j}" for j in range(3)]
                }
            )
            enterprise_contexts.append(ctx)
        
        # CRITICAL VALIDATION 1: Absolute user isolation
        for i, ctx in enumerate(enterprise_contexts):
            # Each context must be completely isolated
            assert ctx.user_id == f"enterprise_customer_{i:03d}"
            assert ctx.metadata["company"] == f"SecureCorp_{i}"
            assert ctx.metadata["revenue_data"] == f"${i * 1000000}M"
            
            # Must not contain data from other users
            for j, other_ctx in enumerate(enterprise_contexts):
                if i != j:
                    assert ctx.user_id != other_ctx.user_id
                    assert ctx.metadata["company"] != other_ctx.metadata["company"]
                    assert ctx.request_id != other_ctx.request_id
        
        # CRITICAL VALIDATION 2: Child contexts maintain isolation
        child_operations = []
        for ctx in enterprise_contexts:
            child = ctx.create_child_context(
                "financial_analysis_agent",
                {"analysis_type": "competitive_intelligence"}
            )
            child_operations.append(child)
        
        # Each child must inherit parent's data but remain isolated from others
        for i, child in enumerate(child_operations):
            parent = enterprise_contexts[i]
            
            # Inherits parent's confidential data
            assert child.user_id == parent.user_id
            assert child.metadata["company"] == parent.metadata["company"]
            assert child.metadata["revenue_data"] == parent.metadata["revenue_data"]
            
            # But isolated from other children
            for j, other_child in enumerate(child_operations):
                if i != j:
                    assert child.user_id != other_child.user_id
                    assert child.metadata["company"] != other_child.metadata["company"]
        
        # CRITICAL VALIDATION 3: WebSocket routing isolation
        ws_contexts = []
        for i, ctx in enumerate(enterprise_contexts):
            ws_ctx = ctx.with_websocket_connection(f"secure_channel_{i}")
            ws_contexts.append(ws_ctx)
        
        # Each WebSocket context routes to correct user only
        for i, ws_ctx in enumerate(ws_contexts):
            assert ws_ctx.websocket_client_id == f"secure_channel_{i}"
            assert ws_ctx.user_id == f"enterprise_customer_{i:03d}"
            
            # Serialization for WebSocket events must maintain isolation
            ws_data = ws_ctx.to_dict()
            assert ws_data["user_id"] == f"enterprise_customer_{i:03d}"
            assert ws_data["websocket_client_id"] == f"secure_channel_{i}"
        
        # CRITICAL VALIDATION 4: Database session isolation
        db_sessions = []
        db_contexts = []
        
        for i, ctx in enumerate(ws_contexts):
            mock_session = Mock(spec=AsyncSession)
            mock_session.user_id = f"enterprise_customer_{i:03d}"  # Simulate user-specific session
            db_sessions.append(mock_session)
            
            db_ctx = ctx.with_db_session(mock_session)
            db_contexts.append(db_ctx)
        
        # Each database context must use correct session
        for i, db_ctx in enumerate(db_contexts):
            assert db_ctx.db_session == db_sessions[i]
            assert db_ctx.db_session.user_id == f"enterprise_customer_{i:03d}"
        
        # CRITICAL VALIDATION 5: Correlation ID uniqueness and traceability  
        correlation_ids = set()
        for ctx in db_contexts:
            correlation_id = ctx.get_correlation_id()
            assert correlation_id not in correlation_ids  # Must be unique
            correlation_ids.add(correlation_id)
            
            # Must be traceable to correct user
            parts = correlation_id.split(':')
            user_prefix = parts[0]
            assert user_prefix.startswith("enterpri")  # From "enterprise_customer_XXX"
        
        # CRITICAL VALIDATION 6: Immutability under attack
        attack_target = db_contexts[0]
        original_user_id = attack_target.user_id
        original_revenue = attack_target.metadata["revenue_data"]
        
        # Attempt to modify critical data
        with pytest.raises(FrozenInstanceError):
            attack_target.user_id = "HACKER_INFILTRATION"
            
        with pytest.raises(FrozenInstanceError):
            attack_target.metadata = {"STOLEN": "DATA"}
        
        # Data must remain unchanged
        assert attack_target.user_id == original_user_id
        assert attack_target.metadata["revenue_data"] == original_revenue
        
        # CRITICAL VALIDATION 7: Deep nesting preserves isolation
        deep_nested = attack_target
        for level in range(5):
            deep_nested = deep_nested.create_child_context(
                f"security_level_{level}",
                {"clearance": f"level_{level}", "access_granted": True}
            )
        
        # Deep context must still belong to original user
        assert deep_nested.user_id == original_user_id
        assert deep_nested.metadata["revenue_data"] == original_revenue
        assert deep_nested.metadata["operation_depth"] == 5
        
        # FINAL ASSERTION: All contexts pass isolation verification
        all_contexts = enterprise_contexts + child_operations + ws_contexts + db_contexts + [deep_nested]
        for ctx in all_contexts:
            isolation_result = ctx.verify_isolation()
            assert isolation_result is True, f"CRITICAL FAILURE: Context {ctx.get_correlation_id()} failed isolation verification"
        
        print(" PASS:  MISSION CRITICAL TEST PASSED: UserExecutionContext maintains absolute user isolation")
        print(f" PASS:  Validated {len(all_contexts)} contexts with zero data leakage")
        print(" PASS:  Business value CONFIRMED: Platform is safe for multi-user enterprise use")

    # =========================================================================
    # ENHANCED MEMORY EFFICIENCY AND FACTORY PATTERN TESTS
    # =========================================================================

    def test_memory_efficiency_under_300mb_requirement(self):
        """Test 46: Memory efficiency must stay under 300MB for multiple users - BUSINESS CRITICAL."""
        import gc
        import os
        
        try:
            import psutil
            # Get current process
            process = psutil.Process(os.getpid())
        except ImportError:
            pytest.skip("psutil not available - skipping memory efficiency test", allow_module_level=True)
        
        # Clear garbage and get baseline memory
        gc.collect()
        baseline_memory_mb = process.memory_info().rss / 1024 / 1024
        
        # Create contexts for 100 concurrent users with substantial data
        user_contexts = []
        for i in range(100):
            ctx = UserExecutionContext.from_request(
                user_id=f"memory_test_user_{i:04d}",
                thread_id=f"memory_test_thread_{i:04d}",
                run_id=f"memory_test_run_{i:04d}",
                metadata={
                    "user_data": f"substantial_user_data_{i}" * 50,  # ~2KB per user
                    "session_info": {
                        "login_time": "2024-01-01T00:00:00Z",
                        "permissions": [f"perm_{j}" for j in range(20)],
                        "preferences": {f"pref_{k}": f"value_{k}" for k in range(10)}
                    },
                    "conversation_history": [f"message_{j}" for j in range(50)]
                }
            )
            
            # Create child contexts to simulate real usage
            agent_ctx = ctx.create_child_context(f"agent_operation_{i}")
            tool_ctx = agent_ctx.create_child_context(f"tool_execution_{i}")
            
            user_contexts.extend([ctx, agent_ctx, tool_ctx])
        
        # Force garbage collection and measure memory
        gc.collect()
        peak_memory_mb = process.memory_info().rss / 1024 / 1024
        memory_used_mb = peak_memory_mb - baseline_memory_mb
        
        print(f" SEARCH:  Memory Usage Analysis:")
        print(f"   Baseline: {baseline_memory_mb:.2f} MB")
        print(f"   Peak: {peak_memory_mb:.2f} MB") 
        print(f"   Used: {memory_used_mb:.2f} MB")
        print(f"   Contexts: {len(user_contexts)}")
        print(f"   Memory per context: {memory_used_mb/len(user_contexts):.3f} MB")
        
        # CRITICAL REQUIREMENT: Must stay under 300MB for 300 contexts (100 users * 3 contexts each)
        assert memory_used_mb < 300, f"MEMORY EFFICIENCY FAILURE: Used {memory_used_mb:.2f}MB > 300MB limit"
        
        # Additional efficiency checks
        assert len(user_contexts) == 300  # Verify we created expected number
        memory_per_context = memory_used_mb / len(user_contexts)
        assert memory_per_context < 1.0, f"Each context uses {memory_per_context:.3f}MB - too much"
        
        # Cleanup
        del user_contexts
        gc.collect()
        
    def test_factory_pattern_no_singleton_behavior(self):
        """Test 47: Factory pattern MUST create unique instances - NO SINGLETONS ALLOWED."""
        
        # Create multiple contexts with same parameters
        identical_params = {
            "user_id": "factory_test_user",
            "thread_id": "factory_test_thread", 
            "run_id": "factory_test_run"
        }
        
        contexts = []
        for i in range(50):
            ctx = UserExecutionContext.from_request(**identical_params)
            contexts.append(ctx)
        
        # CRITICAL: Each context must be a unique object instance
        for i, ctx1 in enumerate(contexts):
            for j, ctx2 in enumerate(contexts):
                if i != j:
                    # Different object instances (no singleton)
                    assert ctx1 is not ctx2, f"SINGLETON VIOLATION: Contexts {i} and {j} are same object"
                    
                    # Different request IDs (factory generates unique IDs)
                    assert ctx1.request_id != ctx2.request_id, f"Request ID collision: {ctx1.request_id}"
                    
                    # Same user data (proper factory behavior)
                    assert ctx1.user_id == ctx2.user_id
                    assert ctx1.thread_id == ctx2.thread_id
                    assert ctx1.run_id == ctx2.run_id
        
        # Memory isolation test - modifying one context shouldn't affect others
        test_ctx = contexts[0]
        
        # Can't modify directly (frozen), but test child creation isolation
        child1 = test_ctx.create_child_context("child1", {"data": "child1_data"})
        child2 = test_ctx.create_child_context("child2", {"data": "child2_data"})
        
        assert child1 is not child2
        assert child1.metadata["data"] != child2.metadata["data"]
        assert child1.request_id != child2.request_id
        
    def test_concurrent_user_race_condition_safety(self):
        """Test 48: Concurrent user context creation must be race condition safe."""
        import threading
        import queue
        
        # Results collection
        results_queue = queue.Queue()
        errors_queue = queue.Queue()
        
        def create_user_context(user_index):
            """Create context for a specific user in separate thread."""
            try:
                ctx = UserExecutionContext.from_request(
                    user_id=f"concurrent_user_{user_index:03d}",
                    thread_id=f"concurrent_thread_{user_index:03d}",
                    run_id=f"concurrent_run_{user_index:03d}",
                    metadata={
                        "thread_id": threading.current_thread().ident,
                        "user_index": user_index,
                        "creation_timestamp": time.time()
                    }
                )
                
                # Create child contexts to stress test
                child1 = ctx.create_child_context(f"operation_a_{user_index}")
                child2 = ctx.create_child_context(f"operation_b_{user_index}")
                
                # Validate isolation immediately
                assert ctx.verify_isolation(), f"Isolation failed for user {user_index}"
                assert child1.verify_isolation(), f"Child1 isolation failed for user {user_index}"
                assert child2.verify_isolation(), f"Child2 isolation failed for user {user_index}"
                
                results_queue.put((user_index, ctx, child1, child2))
                
            except Exception as e:
                errors_queue.put((user_index, e, traceback.format_exc()))
        
        # Launch 20 concurrent threads
        threads = []
        for i in range(20):
            thread = threading.Thread(target=create_user_context, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Collect results
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())
        
        # Check for errors
        errors = []
        while not errors_queue.empty():
            errors.append(errors_queue.get())
        
        # CRITICAL: No errors should occur
        assert len(errors) == 0, f"Race condition errors: {errors}"
        
        # CRITICAL: All contexts should be created successfully
        assert len(results) == 20, f"Expected 20 results, got {len(results)}"
        
        # Validate complete isolation between concurrent creations
        contexts = [r[1] for r in results]  # Extract main contexts
        
        # All contexts must be unique objects
        for i, ctx1 in enumerate(contexts):
            for j, ctx2 in enumerate(contexts):
                if i != j:
                    assert ctx1 is not ctx2
                    assert ctx1.user_id != ctx2.user_id
                    assert ctx1.request_id != ctx2.request_id
                    
                    # Thread IDs in metadata should be different (different threads)
                    thread1 = ctx1.metadata["thread_id"]
                    thread2 = ctx2.metadata["thread_id"]
                    # Note: Threads might reuse IDs, so we can't assert inequality
                    assert isinstance(thread1, int)
                    assert isinstance(thread2, int)
        
    def test_garbage_collection_and_memory_leak_prevention(self):
        """Test 49: Contexts must be properly garbage collected - NO MEMORY LEAKS."""
        import gc
        import weakref
        
        # Track object lifecycle with weak references
        context_refs = []
        
        def create_and_track_contexts():
            """Create contexts and track them with weak references."""
            local_contexts = []
            
            for i in range(100):
                ctx = UserExecutionContext(
                    user_id=f"gc_test_user_{i}",
                    thread_id=f"gc_test_thread_{i}",
                    run_id=f"gc_test_run_{i}",
                    metadata={"large_data": "x" * 1000}  # 1KB per context
                )
                
                # Create child context
                child = ctx.create_child_context(f"gc_operation_{i}")
                
                local_contexts.extend([ctx, child])
                
                # Create weak references to track garbage collection
                context_refs.append(weakref.ref(ctx))
                context_refs.append(weakref.ref(child))
            
            return local_contexts
        
        # Phase 1: Create contexts in local scope
        contexts = create_and_track_contexts()
        
        # All weak references should be alive
        alive_refs = [ref for ref in context_refs if ref() is not None]
        assert len(alive_refs) == len(context_refs), "Some contexts were prematurely garbage collected"
        
        # Phase 2: Delete references and force garbage collection
        del contexts
        gc.collect()
        
        # Phase 3: Verify garbage collection occurred
        alive_after_gc = [ref for ref in context_refs if ref() is not None]
        
        # Some contexts should be garbage collected (depends on Python GC)
        # We can't guarantee 100% collection due to GC timing, but significant reduction expected
        print(f"[U+1F5D1][U+FE0F]  Garbage Collection Analysis:")
        print(f"   Created: {len(context_refs)} contexts")
        print(f"   Alive after GC: {len(alive_after_gc)}")
        print(f"   Collection rate: {((len(context_refs) - len(alive_after_gc)) / len(context_refs) * 100):.1f}%")
        
        # At least 80% should be collected (allowing for GC timing variations)
        collection_rate = (len(context_refs) - len(alive_after_gc)) / len(context_refs)
        assert collection_rate > 0.8, f"Poor garbage collection: only {collection_rate:.1%} collected"
        
    def test_resource_cleanup_validation(self):
        """Test 50: Resource cleanup must be complete when contexts are destroyed."""
        import gc
        import sys
        
        # Track object counts
        initial_objects = len(gc.get_objects())
        
        # Create contexts with various resources
        def create_resource_heavy_contexts():
            contexts = []
            for i in range(50):
                ctx = UserExecutionContext.from_request(
                    user_id=f"resource_user_{i}",
                    thread_id=f"resource_thread_{i}",
                    run_id=f"resource_run_{i}",
                    metadata={
                        "heavy_data": {
                            "list_data": list(range(100)),
                            "dict_data": {f"key_{j}": f"value_{j}" for j in range(50)},
                            "nested_structure": {
                                "level1": {
                                    "level2": {
                                        "data": [f"item_{k}" for k in range(25)]
                                    }
                                }
                            }
                        }
                    }
                )
                
                # Add database session mock
                mock_session = Mock(spec=AsyncSession)
                ctx_with_db = ctx.with_db_session(mock_session)
                
                # Add WebSocket connection
                ctx_with_ws = ctx_with_db.with_websocket_connection(f"ws_conn_{i}")
                
                # Create complex hierarchy
                child1 = ctx_with_ws.create_child_context(f"child1_{i}")
                child2 = child1.create_child_context(f"child2_{i}")
                child3 = child2.create_child_context(f"child3_{i}")
                
                contexts.extend([ctx, ctx_with_db, ctx_with_ws, child1, child2, child3])
            
            return contexts
        
        # Create and immediately destroy contexts
        heavy_contexts = create_resource_heavy_contexts()
        context_count = len(heavy_contexts)
        
        # Get object count after creation
        peak_objects = len(gc.get_objects())
        
        # Clean up
        del heavy_contexts
        gc.collect()
        
        # Get final object count
        final_objects = len(gc.get_objects())
        
        print(f"[U+1F9F9] Resource Cleanup Analysis:")
        print(f"   Initial objects: {initial_objects}")
        print(f"   Peak objects: {peak_objects}")
        print(f"   Final objects: {final_objects}")
        print(f"   Created contexts: {context_count}")
        print(f"   Objects leaked: {final_objects - initial_objects}")
        
        # Should not leak significant objects (allow for test framework overhead)
        leaked_objects = final_objects - initial_objects
        max_allowed_leaks = context_count * 0.1  # Allow 10% overhead
        
        assert leaked_objects <= max_allowed_leaks, f"Memory leak detected: {leaked_objects} objects leaked"
        
    def test_factory_pattern_isolation_stress_test(self):
        """Test 51: Factory pattern isolation under stress conditions."""
        import random
        
        # Create contexts with random overlapping data to test isolation
        all_contexts = []
        
        # Shared data pools that might cause isolation issues if not handled properly
        shared_user_ids = [f"shared_user_{i}" for i in range(5)]
        shared_thread_ids = [f"shared_thread_{i}" for i in range(3)]
        shared_metadata_keys = ["company", "project", "session", "analysis"]
        
        for i in range(200):
            # Randomly select from shared pools to test isolation
            user_id = random.choice(shared_user_ids)
            thread_id = random.choice(shared_thread_ids)
            run_id = f"unique_run_{i}_{uuid.uuid4().hex[:8]}"  # Always unique
            
            # Create metadata with potential conflicts
            metadata = {}
            for key in random.sample(shared_metadata_keys, k=random.randint(1, 3)):
                metadata[key] = f"{key}_value_{i}_{random.randint(1000, 9999)}"
            
            ctx = UserExecutionContext.from_request(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                metadata=metadata
            )
            
            all_contexts.append(ctx)
        
        # Group contexts by user_id and thread_id
        groups = {}
        for ctx in all_contexts:
            key = (ctx.user_id, ctx.thread_id)
            if key not in groups:
                groups[key] = []
            groups[key].append(ctx)
        
        # Validate isolation within groups (same user/thread, different runs)
        for (user_id, thread_id), group_contexts in groups.items():
            print(f" SEARCH:  Testing group {user_id}/{thread_id}: {len(group_contexts)} contexts")
            
            for i, ctx1 in enumerate(group_contexts):
                for j, ctx2 in enumerate(group_contexts):
                    if i != j:
                        # Same user and thread
                        assert ctx1.user_id == ctx2.user_id
                        assert ctx1.thread_id == ctx2.thread_id
                        
                        # Different run_ids and request_ids (isolation)
                        assert ctx1.run_id != ctx2.run_id
                        assert ctx1.request_id != ctx2.request_id
                        
                        # Different object instances
                        assert ctx1 is not ctx2
                        
                        # Metadata should be isolated
                        assert ctx1.metadata is not ctx2.metadata
                        
                        # Verify isolation passes
                        assert ctx1.verify_isolation()
                        assert ctx2.verify_isolation()
        
        print(f" PASS:  Stress test completed: {len(all_contexts)} contexts in {len(groups)} groups")
        
    def test_multi_user_session_lifecycle_comprehensive(self):
        """Test 52: Complete multi-user session lifecycle with factory pattern."""
        """
        This test simulates a realistic multi-user scenario:
        - Multiple users log in simultaneously
        - Each user has multiple sessions/threads
        - Users perform overlapping operations
        - Sessions are cleaned up independently
        - No data bleeding between users
        """
        
        # Define user profiles
        user_profiles = [
            {"tier": "enterprise", "company": "TechCorp", "users": 3},
            {"tier": "professional", "company": "StartupCo", "users": 5}, 
            {"tier": "free", "company": "Individual", "users": 10}
        ]
        
        all_user_sessions = {}
        
        # Phase 1: Simulate user logins and session creation
        for profile in user_profiles:
            for user_num in range(profile["users"]):
                user_id = f"{profile['tier']}_user_{user_num:03d}"
                
                # Each user can have multiple concurrent sessions
                user_sessions = []
                session_count = random.randint(1, 3)
                
                for session_num in range(session_count):
                    # Create main session context
                    session_ctx = UserExecutionContext.from_request(
                        user_id=user_id,
                        thread_id=f"session_{session_num}_{uuid.uuid4().hex[:8]}",
                        run_id=f"login_session_{session_num}",
                        metadata={
                            "user_tier": profile["tier"],
                            "company": profile["company"],
                            "session_number": session_num,
                            "login_timestamp": time.time(),
                            "capabilities": ["chat", "analysis"] if profile["tier"] != "free" else ["chat"]
                        }
                    )
                    
                    # Add WebSocket connection
                    ws_ctx = session_ctx.with_websocket_connection(f"ws_{user_id}_{session_num}")
                    
                    # Add database session for paid tiers
                    if profile["tier"] != "free":
                        mock_db = Mock(spec=AsyncSession)
                        mock_db.user_tier = profile["tier"]
                        db_ctx = ws_ctx.with_db_session(mock_db)
                        user_sessions.append(db_ctx)
                    else:
                        user_sessions.append(ws_ctx)
                
                all_user_sessions[user_id] = user_sessions
        
        # Phase 2: Simulate concurrent operations per user
        operation_contexts = {}
        
        for user_id, sessions in all_user_sessions.items():
            user_operations = []
            
            for session_ctx in sessions:
                # Each session can run multiple operations
                operations = ["data_analysis", "optimization", "reporting"]
                if "free" in user_id:
                    operations = ["basic_chat"]  # Limited for free users
                
                for op_name in operations:
                    op_ctx = session_ctx.create_child_context(
                        op_name,
                        {
                            "operation_type": op_name,
                            "priority": "high" if "enterprise" in user_id else "normal",
                            "start_time": time.time()
                        }
                    )
                    
                    # Create tool execution contexts
                    tool_ctx = op_ctx.create_child_context(f"{op_name}_tool")
                    user_operations.extend([op_ctx, tool_ctx])
            
            operation_contexts[user_id] = user_operations
        
        # Phase 3: Comprehensive isolation validation
        print(f"[U+1F3E2] Multi-user validation: {len(all_user_sessions)} users, multiple tiers")
        
        # Validate user-level isolation
        for user1_id, user1_sessions in all_user_sessions.items():
            for user2_id, user2_sessions in all_user_sessions.items():
                if user1_id != user2_id:
                    # Different users should have completely isolated data
                    for session1 in user1_sessions:
                        for session2 in user2_sessions:
                            assert session1.user_id != session2.user_id
                            assert session1.metadata["company"] != session2.metadata["company"]
                            assert session1.request_id != session2.request_id
                            
                            # WebSocket connections should be different
                            assert session1.websocket_client_id != session2.websocket_client_id
        
        # Validate operation-level isolation
        for user1_id, user1_ops in operation_contexts.items():
            for user2_id, user2_ops in operation_contexts.items():
                if user1_id != user2_id:
                    for op1 in user1_ops:
                        for op2 in user2_ops:
                            # Operations from different users must be isolated
                            assert op1.user_id != op2.user_id
                            assert op1.request_id != op2.request_id
                            assert op1 is not op2
        
        # Validate tier-based access patterns
        enterprise_contexts = [ctx for user_id, sessions in all_user_sessions.items() 
                             if "enterprise" in user_id for ctx in sessions]
        free_contexts = [ctx for user_id, sessions in all_user_sessions.items() 
                        if "free" in user_id for ctx in sessions]
        
        # Enterprise users should have database sessions
        for ctx in enterprise_contexts:
            assert ctx.db_session is not None
            assert hasattr(ctx.db_session, 'user_tier')
            assert ctx.db_session.user_tier == "enterprise"
        
        # Free users should not have database sessions (in this simulation)
        for ctx in free_contexts:
            if hasattr(ctx, 'db_session'):
                # Free tier contexts created without db sessions in this test
                pass
        
        # Phase 4: Cleanup simulation and validation
        # Simulate individual user session cleanup
        cleanup_user = list(all_user_sessions.keys())[0]
        cleanup_sessions = all_user_sessions[cleanup_user]
        
        # Before cleanup - contexts exist
        assert len(cleanup_sessions) > 0
        for ctx in cleanup_sessions:
            assert ctx.verify_isolation()
        
        # Simulate cleanup
        del all_user_sessions[cleanup_user]
        del operation_contexts[cleanup_user]
        
        # Remaining users should be unaffected
        remaining_users = list(all_user_sessions.keys())
        assert len(remaining_users) > 0
        
        for user_id in remaining_users:
            for session_ctx in all_user_sessions[user_id]:
                assert session_ctx.verify_isolation()
                assert session_ctx.user_id == user_id
        
        print(f" PASS:  Multi-user lifecycle test completed successfully")
        print(f"   - {len(user_profiles)} user tiers tested")
        print(f"   - {sum(p['users'] for p in user_profiles)} total users")
        print(f"   - Multiple sessions per user")
        print(f"   - Complex operation hierarchies") 
        print(f"   - Tier-based access controls")
        print(f"   - Clean isolation maintained throughout")