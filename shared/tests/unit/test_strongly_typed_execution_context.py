"""Unit tests for StronglyTypedUserExecutionContext.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Type Safety & Context Isolation
- Value Impact: Prevents type drift that causes $500K+ ARR loss from context mixing
- Strategic Impact: Foundation for reliable multi-user execution engine operations

CRITICAL REQUIREMENTS per CLAUDE.md:
1. NO MOCKS - Test real context creation and validation patterns
2. Type Safety - Validate all strongly typed ID enforcement
3. Context Isolation - Test forbidden placeholder prevention
4. Factory Patterns - Test context creation through proper factories
5. Child Context - Test hierarchical context creation and validation
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from shared.types.execution_types import (
    StronglyTypedUserExecutionContext,
    ContextValidationError,
    IsolationViolationError,
    upgrade_legacy_context,
    downgrade_to_legacy_context
)
from shared.types.core_types import (
    UserID, ThreadID, RunID, RequestID, WebSocketID,
    ensure_user_id, ensure_thread_id, ensure_run_id, ensure_request_id
)


class TestStronglyTypedUserExecutionContextCreation:
    """Test creation and validation of StronglyTypedUserExecutionContext."""
    
    def test_create_valid_context_with_all_fields(self):
        """Test creating context with all valid fields."""
        # Generate real unique IDs (no placeholders)
        user_id = UserID(f"user_{uuid.uuid4().hex[:12]}")
        thread_id = ThreadID(f"thread_{uuid.uuid4().hex[:12]}")
        run_id = RunID(f"run_{uuid.uuid4().hex[:12]}")
        request_id = RequestID(f"req_{uuid.uuid4().hex[:12]}")
        websocket_id = WebSocketID(f"ws_{uuid.uuid4().hex[:12]}")
        
        # Create context with all fields
        context = StronglyTypedUserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            request_id=request_id,
            websocket_client_id=websocket_id,
            agent_context={"test_key": "test_value"},
            audit_metadata={"audit_key": "audit_value"}
        )
        
        # Validate all fields are correctly set
        assert context.user_id == user_id
        assert context.thread_id == thread_id
        assert context.run_id == run_id
        assert context.request_id == request_id
        assert context.websocket_client_id == websocket_id
        assert context.agent_context == {"test_key": "test_value"}
        assert context.audit_metadata == {"audit_key": "audit_value"}
        assert context.operation_depth == 0
        assert context.parent_request_id is None
        assert isinstance(context.created_at, datetime)
    
    def test_create_minimal_context_with_required_fields_only(self):
        """Test creating context with only required fields."""
        # Generate real unique IDs
        user_id = UserID(f"user_{uuid.uuid4().hex[:12]}")
        thread_id = ThreadID(f"thread_{uuid.uuid4().hex[:12]}")
        run_id = RunID(f"run_{uuid.uuid4().hex[:12]}")
        request_id = RequestID(f"req_{uuid.uuid4().hex[:12]}")
        
        # Create minimal context
        context = StronglyTypedUserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            request_id=request_id
        )
        
        # Validate required fields
        assert context.user_id == user_id
        assert context.thread_id == thread_id
        assert context.run_id == run_id
        assert context.request_id == request_id
        
        # Validate default values
        assert context.websocket_client_id is None
        assert context.agent_context == {}
        assert context.audit_metadata == {}
        assert context.operation_depth == 0
        assert context.parent_request_id is None
    
    def test_context_immutability_via_frozen_dataclass(self):
        """Test that context is immutable after creation."""
        user_id = UserID(f"user_{uuid.uuid4().hex[:12]}")
        thread_id = ThreadID(f"thread_{uuid.uuid4().hex[:12]}")
        run_id = RunID(f"run_{uuid.uuid4().hex[:12]}")
        request_id = RequestID(f"req_{uuid.uuid4().hex[:12]}")
        
        context = StronglyTypedUserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            request_id=request_id
        )
        
        # Test that direct field modification raises error
        with pytest.raises(Exception):  # dataclass frozen=True raises FrozenInstanceError
            context.user_id = UserID("different_user")
        
        with pytest.raises(Exception):
            context.operation_depth = 5


class TestStronglyTypedUserExecutionContextValidation:
    """Test validation logic for StronglyTypedUserExecutionContext."""
    
    def test_reject_empty_user_id(self):
        """Test that empty user_id is rejected."""
        thread_id = ThreadID(f"thread_{uuid.uuid4().hex[:12]}")
        run_id = RunID(f"run_{uuid.uuid4().hex[:12]}")
        request_id = RequestID(f"req_{uuid.uuid4().hex[:12]}")
        
        with pytest.raises(ContextValidationError, match="Invalid user_id"):
            StronglyTypedUserExecutionContext(
                user_id=UserID(""),
                thread_id=thread_id,
                run_id=run_id,
                request_id=request_id
            )
        
        with pytest.raises(ContextValidationError, match="Invalid user_id"):
            StronglyTypedUserExecutionContext(
                user_id=UserID("   "),  # whitespace only
                thread_id=thread_id,
                run_id=run_id,
                request_id=request_id
            )
    
    def test_reject_placeholder_values(self):
        """Test that forbidden placeholder values are rejected."""
        thread_id = ThreadID(f"thread_{uuid.uuid4().hex[:12]}")
        run_id = RunID(f"run_{uuid.uuid4().hex[:12]}")
        request_id = RequestID(f"req_{uuid.uuid4().hex[:12]}")
        
        # Test forbidden user_id values
        forbidden_user_ids = [
            "test_user", "mock_user", "placeholder", "default", "example"
        ]
        
        for forbidden_id in forbidden_user_ids:
            with pytest.raises(ContextValidationError, match="Forbidden placeholder value"):
                StronglyTypedUserExecutionContext(
                    user_id=UserID(forbidden_id),
                    thread_id=thread_id,
                    run_id=run_id,
                    request_id=request_id
                )
        
        # Test forbidden thread_id values
        user_id = UserID(f"user_{uuid.uuid4().hex[:12]}")
        with pytest.raises(ContextValidationError, match="Forbidden placeholder value"):
            StronglyTypedUserExecutionContext(
                user_id=user_id,
                thread_id=ThreadID("test_thread"),
                run_id=run_id,
                request_id=request_id
            )
    
    def test_reject_invalid_operation_depth(self):
        """Test that invalid operation depth is rejected."""
        user_id = UserID(f"user_{uuid.uuid4().hex[:12]}")
        thread_id = ThreadID(f"thread_{uuid.uuid4().hex[:12]}")
        run_id = RunID(f"run_{uuid.uuid4().hex[:12]}")
        request_id = RequestID(f"req_{uuid.uuid4().hex[:12]}")
        
        # Test negative depth
        with pytest.raises(ContextValidationError, match="Invalid operation_depth"):
            StronglyTypedUserExecutionContext(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                request_id=request_id,
                operation_depth=-1
            )
        
        # Test depth too high
        with pytest.raises(ContextValidationError, match="Invalid operation_depth"):
            StronglyTypedUserExecutionContext(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                request_id=request_id,
                operation_depth=15  # > 10 max
            )
    
    def test_validate_context_data_types(self):
        """Test validation of context data types."""
        user_id = UserID(f"user_{uuid.uuid4().hex[:12]}")
        thread_id = ThreadID(f"thread_{uuid.uuid4().hex[:12]}")
        run_id = RunID(f"run_{uuid.uuid4().hex[:12]}")
        request_id = RequestID(f"req_{uuid.uuid4().hex[:12]}")
        
        # Test invalid agent_context type
        with pytest.raises(ContextValidationError, match="agent_context must be a dictionary"):
            StronglyTypedUserExecutionContext(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                request_id=request_id,
                agent_context="not_a_dict"  # type: ignore
            )
        
        # Test invalid audit_metadata type
        with pytest.raises(ContextValidationError, match="audit_metadata must be a dictionary"):
            StronglyTypedUserExecutionContext(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                request_id=request_id,
                audit_metadata=["not", "a", "dict"]  # type: ignore
            )


class TestStronglyTypedUserExecutionContextChildCreation:
    """Test child context creation and hierarchical patterns."""
    
    def test_create_child_context_with_auto_generated_id(self):
        """Test creating child context with auto-generated request_id."""
        # Create parent context
        parent_user_id = UserID(f"user_{uuid.uuid4().hex[:12]}")
        parent_thread_id = ThreadID(f"thread_{uuid.uuid4().hex[:12]}")
        parent_run_id = RunID(f"run_{uuid.uuid4().hex[:12]}")
        parent_request_id = RequestID(f"req_{uuid.uuid4().hex[:12]}")
        
        parent_context = StronglyTypedUserExecutionContext(
            user_id=parent_user_id,
            thread_id=parent_thread_id,
            run_id=parent_run_id,
            request_id=parent_request_id,
            agent_context={"parent_key": "parent_value"},
            audit_metadata={"audit_parent": "audit_value"}
        )
        
        # Create child context
        child_context = parent_context.create_child_context()
        
        # Validate inheritance
        assert child_context.user_id == parent_user_id
        assert child_context.thread_id == parent_thread_id
        assert child_context.run_id == parent_run_id
        assert child_context.request_id != parent_request_id  # Should be different
        assert child_context.parent_request_id == parent_request_id
        assert child_context.operation_depth == parent_context.operation_depth + 1
        
        # Validate context copying
        assert child_context.agent_context == {"parent_key": "parent_value"}
        assert child_context.audit_metadata == {"audit_parent": "audit_value"}
        
        # Validate timestamps
        assert child_context.created_at > parent_context.created_at
    
    def test_create_child_context_with_custom_request_id(self):
        """Test creating child context with custom request_id."""
        # Create parent context
        parent_user_id = UserID(f"user_{uuid.uuid4().hex[:12]}")
        parent_thread_id = ThreadID(f"thread_{uuid.uuid4().hex[:12]}")
        parent_run_id = RunID(f"run_{uuid.uuid4().hex[:12]}")
        parent_request_id = RequestID(f"req_{uuid.uuid4().hex[:12]}")
        
        parent_context = StronglyTypedUserExecutionContext(
            user_id=parent_user_id,
            thread_id=parent_thread_id,
            run_id=parent_run_id,
            request_id=parent_request_id
        )
        
        # Create child with custom request_id
        custom_request_id = RequestID(f"child_req_{uuid.uuid4().hex[:12]}")
        child_context = parent_context.create_child_context(custom_request_id)
        
        # Validate custom request_id is used
        assert child_context.request_id == custom_request_id
        assert child_context.parent_request_id == parent_request_id
    
    def test_multi_level_child_context_hierarchy(self):
        """Test creating multi-level child context hierarchy."""
        # Create root context
        root_user_id = UserID(f"user_{uuid.uuid4().hex[:12]}")
        root_thread_id = ThreadID(f"thread_{uuid.uuid4().hex[:12]}")
        root_run_id = RunID(f"run_{uuid.uuid4().hex[:12]}")
        root_request_id = RequestID(f"req_{uuid.uuid4().hex[:12]}")
        
        root_context = StronglyTypedUserExecutionContext(
            user_id=root_user_id,
            thread_id=root_thread_id,
            run_id=root_run_id,
            request_id=root_request_id
        )
        
        # Create level 1 child
        level1_context = root_context.create_child_context()
        assert level1_context.operation_depth == 1
        assert level1_context.parent_request_id == root_request_id
        
        # Create level 2 child
        level2_context = level1_context.create_child_context()
        assert level2_context.operation_depth == 2
        assert level2_context.parent_request_id == level1_context.request_id
        
        # Validate all contexts share same user/thread/run
        contexts = [root_context, level1_context, level2_context]
        for context in contexts:
            assert context.user_id == root_user_id
            assert context.thread_id == root_thread_id
            assert context.run_id == root_run_id


class TestStronglyTypedUserExecutionContextCompatibility:
    """Test compatibility features and legacy migration."""
    
    def test_metadata_property_backward_compatibility(self):
        """Test metadata property provides unified view."""
        user_id = UserID(f"user_{uuid.uuid4().hex[:12]}")
        thread_id = ThreadID(f"thread_{uuid.uuid4().hex[:12]}")
        run_id = RunID(f"run_{uuid.uuid4().hex[:12]}")
        request_id = RequestID(f"req_{uuid.uuid4().hex[:12]}")
        
        context = StronglyTypedUserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            request_id=request_id,
            agent_context={"agent_key": "agent_value"},
            audit_metadata={"audit_key": "audit_value"}
        )
        
        # Test unified metadata property
        expected_metadata = {
            "agent_key": "agent_value",
            "audit_key": "audit_value"
        }
        assert context.metadata == expected_metadata
    
    def test_websocket_connection_id_alias(self):
        """Test websocket_connection_id property alias."""
        user_id = UserID(f"user_{uuid.uuid4().hex[:12]}")
        thread_id = ThreadID(f"thread_{uuid.uuid4().hex[:12]}")
        run_id = RunID(f"run_{uuid.uuid4().hex[:12]}")
        request_id = RequestID(f"req_{uuid.uuid4().hex[:12]}")
        websocket_id = WebSocketID(f"ws_{uuid.uuid4().hex[:12]}")
        
        context = StronglyTypedUserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            request_id=request_id,
            websocket_client_id=websocket_id
        )
        
        # Test alias works
        assert context.websocket_connection_id == websocket_id
        assert context.websocket_connection_id == context.websocket_client_id
    
    def test_upgrade_legacy_dict_context(self):
        """Test upgrading legacy dict-based context."""
        # Create legacy context as dict
        legacy_dict = {
            'user_id': f'user_{uuid.uuid4().hex[:12]}',
            'thread_id': f'thread_{uuid.uuid4().hex[:12]}',
            'run_id': f'run_{uuid.uuid4().hex[:12]}',
            'request_id': f'req_{uuid.uuid4().hex[:12]}',
            'websocket_client_id': f'ws_{uuid.uuid4().hex[:12]}',
            'agent_context': {'legacy_key': 'legacy_value'},
            'audit_metadata': {'legacy_audit': 'audit_value'},
            'operation_depth': 2,
            'parent_request_id': f'parent_{uuid.uuid4().hex[:12]}'
        }
        
        # Upgrade to strongly typed
        typed_context = upgrade_legacy_context(legacy_dict)
        
        # Validate conversion
        assert str(typed_context.user_id) == legacy_dict['user_id']
        assert str(typed_context.thread_id) == legacy_dict['thread_id']
        assert str(typed_context.run_id) == legacy_dict['run_id']
        assert str(typed_context.request_id) == legacy_dict['request_id']
        assert str(typed_context.websocket_client_id) == legacy_dict['websocket_client_id']
        assert typed_context.agent_context == legacy_dict['agent_context']
        assert typed_context.audit_metadata == legacy_dict['audit_metadata']
        assert typed_context.operation_depth == legacy_dict['operation_depth']
        assert str(typed_context.parent_request_id) == legacy_dict['parent_request_id']
    
    def test_downgrade_to_legacy_format(self):
        """Test downgrading typed context to legacy dict format."""
        # Create typed context
        user_id = UserID(f"user_{uuid.uuid4().hex[:12]}")
        thread_id = ThreadID(f"thread_{uuid.uuid4().hex[:12]}")
        run_id = RunID(f"run_{uuid.uuid4().hex[:12]}")
        request_id = RequestID(f"req_{uuid.uuid4().hex[:12]}")
        websocket_id = WebSocketID(f"ws_{uuid.uuid4().hex[:12]}")
        
        typed_context = StronglyTypedUserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            request_id=request_id,
            websocket_client_id=websocket_id,
            agent_context={"typed_key": "typed_value"},
            audit_metadata={"typed_audit": "audit_value"}
        )
        
        # Downgrade to legacy format
        legacy_dict = downgrade_to_legacy_context(typed_context)
        
        # Validate conversion
        assert legacy_dict['user_id'] == str(user_id)
        assert legacy_dict['thread_id'] == str(thread_id)
        assert legacy_dict['run_id'] == str(run_id)
        assert legacy_dict['request_id'] == str(request_id)
        assert legacy_dict['websocket_client_id'] == str(websocket_id)
        assert legacy_dict['agent_context'] == {"typed_key": "typed_value"}
        assert legacy_dict['audit_metadata'] == {"typed_audit": "audit_value"}
        assert 'created_at' in legacy_dict
    
    def test_round_trip_conversion(self):
        """Test that upgrade->downgrade->upgrade preserves data."""
        # Start with legacy dict
        original_dict = {
            'user_id': f'user_{uuid.uuid4().hex[:12]}',
            'thread_id': f'thread_{uuid.uuid4().hex[:12]}',
            'run_id': f'run_{uuid.uuid4().hex[:12]}',
            'request_id': f'req_{uuid.uuid4().hex[:12]}',
            'agent_context': {'test_key': 'test_value'},
            'audit_metadata': {'audit_key': 'audit_value'}
        }
        
        # Upgrade to typed
        typed_context = upgrade_legacy_context(original_dict)
        
        # Downgrade back to dict
        round_trip_dict = downgrade_to_legacy_context(typed_context)
        
        # Upgrade again
        final_typed_context = upgrade_legacy_context(round_trip_dict)
        
        # Validate key fields preserved
        assert str(final_typed_context.user_id) == original_dict['user_id']
        assert str(final_typed_context.thread_id) == original_dict['thread_id']
        assert str(final_typed_context.run_id) == original_dict['run_id']
        assert str(final_typed_context.request_id) == original_dict['request_id']
        assert final_typed_context.agent_context == original_dict['agent_context']
        assert final_typed_context.audit_metadata == original_dict['audit_metadata']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])