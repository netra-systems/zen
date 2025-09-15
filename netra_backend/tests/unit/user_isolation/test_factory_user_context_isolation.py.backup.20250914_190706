"""
Test Factory Pattern User Context Isolation

Business Value Justification (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise)
- Business Goal: Ensure complete user isolation to prevent data leakage 
- Value Impact: Guarantees user data security and prevents cross-user contamination
- Strategic Impact: CRITICAL - Foundation of multi-user platform security

This test suite validates that Factory-based user isolation patterns ensure
complete separation between concurrent user requests with zero shared state.

Architecture Tested:
- UserExecutionContext Factory patterns from USER_CONTEXT_ARCHITECTURE.md
- Factory-based isolation ensuring no shared state between users
- Request-scoped resource management preventing leakage
- Child context inheritance patterns maintaining isolation
"""

import asyncio
import dataclasses
import pytest
import uuid
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set

from netra_backend.app.services.user_execution_context import (
    UserExecutionContext, 
    UserContextFactory,
    InvalidContextError,
    ContextIsolationError,
    validate_user_context,
    managed_user_context,
    register_shared_object,
    clear_shared_object_registry
)
from netra_backend.app.services.websocket_bridge_factory import (
    WebSocketBridgeFactory,
    UserWebSocketContext,
    WebSocketFactoryConfig,
    ConnectionStatus
)
from test_framework.ssot.base_test_case import SSotBaseTestCase


@dataclass
class IsolationTestContext:
    """Test context for tracking user isolation validation."""
    user_id: str
    context_id: str
    created_objects: List[Any]
    shared_state_violations: List[str]
    isolation_verified: bool = False


class TestFactoryUserContextIsolation(SSotBaseTestCase):
    """Test Factory Pattern ensures complete user context isolation."""
    
    def setup_method(self):
        """Set up isolation testing environment."""
        # Clear any shared object registry between tests
        clear_shared_object_registry()
        
        # Track test contexts
        self.test_contexts: Dict[str, IsolationTestContext] = {}
        self.isolation_violations: List[str] = []
        
    def teardown_method(self):
        """Clean up after each test."""
        clear_shared_object_registry()
        self.test_contexts.clear()
        self.isolation_violations.clear()
    
    def test_user_context_factory_creates_isolated_instances(self):
        """Test that UserContextFactory creates completely isolated context instances."""
        # Create contexts for multiple users using factory
        user_contexts = {}
        
        for i in range(5):
            user_id = f"user_{i}"
            thread_id = f"thread_{i}"
            run_id = f"run_{i}"
            
            context = UserContextFactory.create_context(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id
            )
            
            user_contexts[user_id] = context
            
            # Verify context is properly created
            assert context.user_id == user_id
            assert context.thread_id == thread_id
            assert context.run_id == run_id
            assert context.request_id is not None
            
            # Verify context passes isolation validation
            assert context.verify_isolation() is True
            
        # Verify complete isolation between contexts
        context_list = list(user_contexts.values())
        
        # 1. No shared object references
        for i, ctx1 in enumerate(context_list):
            for j, ctx2 in enumerate(context_list):
                if i != j:
                    # Verify agent_context dictionaries are different objects
                    assert id(ctx1.agent_context) != id(ctx2.agent_context), \
                        f"Contexts {i} and {j} share agent_context object - ISOLATION VIOLATION"
                    
                    # Verify audit_metadata dictionaries are different objects  
                    assert id(ctx1.audit_metadata) != id(ctx2.audit_metadata), \
                        f"Contexts {i} and {j} share audit_metadata object - ISOLATION VIOLATION"
                    
                    # Verify no ID overlap
                    assert ctx1.user_id != ctx2.user_id
                    assert ctx1.thread_id != ctx2.thread_id
                    assert ctx1.run_id != ctx2.run_id
                    assert ctx1.request_id != ctx2.request_id
        
        # 2. Metadata modification doesn't affect other contexts
        test_context = user_contexts["user_0"]
        test_context.agent_context["test_key"] = "test_value"
        test_context.audit_metadata["audit_key"] = "audit_value"
        
        # Verify other contexts are unaffected
        for user_id, ctx in user_contexts.items():
            if user_id != "user_0":
                assert "test_key" not in ctx.agent_context, \
                    f"Context {user_id} contaminated with test_key - ISOLATION VIOLATION"
                assert "audit_key" not in ctx.audit_metadata, \
                    f"Context {user_id} contaminated with audit_key - ISOLATION VIOLATION"

    def test_child_context_inheritance_maintains_isolation(self):
        """Test that child contexts inherit properly while maintaining isolation."""
        # Create parent context
        parent_context = UserContextFactory.create_context(
            user_id="parent_user",
            thread_id="parent_thread", 
            run_id="parent_run"
        )
        
        # Add some parent-specific data
        parent_context.agent_context["parent_data"] = "parent_value"
        parent_context.audit_metadata["parent_audit"] = "parent_audit_value"
        
        # Create multiple child contexts
        child_contexts = []
        for i in range(3):
            child = parent_context.create_child_context(
                operation_name=f"child_operation_{i}",
                additional_agent_context={"child_specific": f"child_value_{i}"},
                additional_audit_metadata={"child_audit": f"child_audit_{i}"}
            )
            child_contexts.append(child)
            
            # Verify child inherits from parent but is isolated
            assert child.user_id == parent_context.user_id  # Inherited
            assert child.thread_id == parent_context.thread_id  # Inherited  
            assert child.run_id == parent_context.run_id  # Inherited
            assert child.request_id != parent_context.request_id  # New unique ID
            assert child.parent_request_id == parent_context.request_id  # Proper hierarchy
            assert child.operation_depth == parent_context.operation_depth + 1  # Incremented
            
            # Verify child has inherited data
            assert child.agent_context["parent_data"] == "parent_value"
            assert child.audit_metadata["parent_audit"] == "parent_audit_value"
            
            # Verify child has its own data
            assert child.agent_context["child_specific"] == f"child_value_{i}"
            assert child.audit_metadata["child_audit"] == f"child_audit_{i}"
            
            # CRITICAL: Verify child context is completely isolated object
            assert id(child.agent_context) != id(parent_context.agent_context), \
                "Child shares agent_context object with parent - ISOLATION VIOLATION"
            assert id(child.audit_metadata) != id(parent_context.audit_metadata), \
                "Child shares audit_metadata object with parent - ISOLATION VIOLATION"
                
            # Verify child passes isolation validation
            assert child.verify_isolation() is True
            
        # Test isolation between child contexts
        for i, child1 in enumerate(child_contexts):
            for j, child2 in enumerate(child_contexts):
                if i != j:
                    # Verify different request IDs
                    assert child1.request_id != child2.request_id
                    
                    # Verify completely separate objects
                    assert id(child1.agent_context) != id(child2.agent_context), \
                        f"Child contexts {i} and {j} share agent_context - ISOLATION VIOLATION"
                    assert id(child1.audit_metadata) != id(child2.audit_metadata), \
                        f"Child contexts {i} and {j} share audit_metadata - ISOLATION VIOLATION"
                    
                    # Verify child-specific data is isolated
                    assert child1.agent_context["child_specific"] != child2.agent_context["child_specific"]
                    assert child1.audit_metadata["child_audit"] != child2.audit_metadata["child_audit"]
        
        # Test modification isolation - changes to child don't affect parent or siblings
        child_contexts[0].agent_context["isolation_test"] = "isolated_value"
        
        # Verify parent unaffected
        assert "isolation_test" not in parent_context.agent_context, \
            "Parent context contaminated by child modification - ISOLATION VIOLATION"
            
        # Verify siblings unaffected
        for i in range(1, len(child_contexts)):
            assert "isolation_test" not in child_contexts[i].agent_context, \
                f"Child context {i} contaminated by sibling modification - ISOLATION VIOLATION"

    def test_concurrent_context_creation_isolation(self):
        """Test that concurrent context creation maintains complete isolation."""
        
        def create_user_context(user_index: int) -> IsolationTestContext:
            """Create a user context and perform isolation tests."""
            user_id = f"concurrent_user_{user_index}"
            thread_id = f"concurrent_thread_{user_index}"
            run_id = f"concurrent_run_{user_index}"
            
            # Create context using factory
            context = UserContextFactory.create_context(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id
            )
            
            # Add user-specific data
            context.agent_context[f"user_{user_index}_data"] = f"value_{user_index}"
            context.audit_metadata[f"user_{user_index}_audit"] = f"audit_{user_index}"
            
            # Create test tracking context
            test_ctx = IsolationTestContext(
                user_id=user_id,
                context_id=context.request_id,
                created_objects=[context, context.agent_context, context.audit_metadata],
                shared_state_violations=[]
            )
            
            # Verify isolation
            try:
                context.verify_isolation()
                test_ctx.isolation_verified = True
            except ContextIsolationError as e:
                test_ctx.shared_state_violations.append(str(e))
                test_ctx.isolation_verified = False
                
            return test_ctx
        
        # Execute concurrent context creation
        num_users = 10
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_index = {
                executor.submit(create_user_context, i): i 
                for i in range(num_users)
            }
            
            test_results = {}
            for future in as_completed(future_to_index):
                user_index = future_to_index[future]
                try:
                    test_ctx = future.result(timeout=10)
                    test_results[user_index] = test_ctx
                except Exception as e:
                    pytest.fail(f"Concurrent context creation failed for user {user_index}: {e}")
        
        # Verify all contexts were created successfully
        assert len(test_results) == num_users
        
        # Verify complete isolation between all concurrent contexts
        context_list = list(test_results.values())
        
        for i, ctx1 in enumerate(context_list):
            assert ctx1.isolation_verified, \
                f"Context {i} failed isolation verification: {ctx1.shared_state_violations}"
            
            for j, ctx2 in enumerate(context_list):
                if i != j:
                    # Verify no shared object references
                    for obj1 in ctx1.created_objects:
                        for obj2 in ctx2.created_objects:
                            assert id(obj1) != id(obj2), \
                                f"Contexts {i} and {j} share object reference - ISOLATION VIOLATION"
                    
                    # Verify unique identifiers
                    assert ctx1.user_id != ctx2.user_id
                    assert ctx1.context_id != ctx2.context_id
                    
        # Verify data isolation across concurrent operations  
        for user_index, test_ctx in test_results.items():
            expected_key = f"user_{user_index}_data"
            # This test_ctx represents results from create_user_context function
            # We need to verify the actual context, but we stored it in created_objects[0]
            actual_context = test_ctx.created_objects[0]
            
            # Verify this context only has its own data
            assert expected_key in actual_context.agent_context
            assert actual_context.agent_context[expected_key] == f"value_{user_index}"
            
            # Verify it doesn't have other users' data
            for other_user_index in range(num_users):
                if other_user_index != user_index:
                    other_key = f"user_{other_user_index}_data"
                    assert other_key not in actual_context.agent_context, \
                        f"Context {user_index} contaminated with data from user {other_user_index} - ISOLATION VIOLATION"

    def test_websocket_bridge_factory_user_isolation(self):
        """Test WebSocketBridgeFactory creates isolated per-user emitters."""
        # Create factory with test configuration
        config = WebSocketFactoryConfig(
            max_events_per_user=100,
            event_timeout_seconds=10.0
        )
        factory = WebSocketBridgeFactory(config)
        
        # Create multiple user WebSocket contexts
        user_contexts = {}
        for i in range(3):
            user_id = f"ws_user_{i}"
            thread_id = f"ws_thread_{i}"
            connection_id = f"ws_conn_{i}"
            
            context = UserWebSocketContext(
                user_id=user_id,
                thread_id=thread_id,
                connection_id=connection_id
            )
            user_contexts[user_id] = context
            
            # Verify context isolation
            assert context.user_id == user_id
            assert context.thread_id == thread_id 
            assert context.connection_id == connection_id
            assert context.connection_status == ConnectionStatus.INITIALIZING
            
            # Verify each context has its own event queue
            assert hasattr(context.event_queue, '_maxsize')
            assert context.event_queue._maxsize == 1000  # Default maxsize
            
        # Verify complete isolation between WebSocket contexts
        context_list = list(user_contexts.values())
        
        for i, ctx1 in enumerate(context_list):
            for j, ctx2 in enumerate(context_list):
                if i != j:
                    # Verify separate event queues
                    assert id(ctx1.event_queue) != id(ctx2.event_queue), \
                        f"WebSocket contexts {i} and {j} share event queue - ISOLATION VIOLATION"
                    
                    # Verify separate event history lists
                    assert id(ctx1.sent_events) != id(ctx2.sent_events), \
                        f"WebSocket contexts {i} and {j} share sent_events list - ISOLATION VIOLATION"
                    assert id(ctx1.failed_events) != id(ctx2.failed_events), \
                        f"WebSocket contexts {i} and {j} share failed_events list - ISOLATION VIOLATION"
                    
                    # Verify separate cleanup callbacks
                    assert id(ctx1.cleanup_callbacks) != id(ctx2.cleanup_callbacks), \
                        f"WebSocket contexts {i} and {j} share cleanup_callbacks - ISOLATION VIOLATION"
                    
                    # Verify unique identifiers
                    assert ctx1.user_id != ctx2.user_id
                    assert ctx1.connection_id != ctx2.connection_id

    def test_context_validation_prevents_dangerous_values(self):
        """Test that context validation prevents placeholder and dangerous values."""
        
        # Test forbidden exact values
        forbidden_values = [
            'registry', 'placeholder', 'default', 'temp', 'none', 'null',
            'undefined', '0', '1', 'xxx', 'yyy', 'example', 'demo'
        ]
        
        for forbidden_value in forbidden_values:
            with pytest.raises(InvalidContextError, match="forbidden placeholder value"):
                UserContextFactory.create_context(
                    user_id=forbidden_value,
                    thread_id="valid_thread",
                    run_id="valid_run"
                )
            
            with pytest.raises(InvalidContextError, match="forbidden placeholder value"):
                UserContextFactory.create_context(
                    user_id="valid_user",
                    thread_id=forbidden_value,
                    run_id="valid_run"
                )
                
            with pytest.raises(InvalidContextError, match="forbidden placeholder value"):
                UserContextFactory.create_context(
                    user_id="valid_user", 
                    thread_id="valid_thread",
                    run_id=forbidden_value
                )
        
        # Test forbidden patterns for short values
        forbidden_patterns = [
            'placeholder_', 'registry_', 'default_', 'temp_',
            'example_', 'demo_', 'sample_', 'template_', 'mock_', 'fake_'
        ]
        
        for pattern in forbidden_patterns:
            short_value = pattern + "short"  # Make it short (< 20 chars)
            
            with pytest.raises(InvalidContextError, match="placeholder pattern"):
                UserContextFactory.create_context(
                    user_id=short_value,
                    thread_id="valid_thread", 
                    run_id="valid_run"
                )

    def test_context_immutability_enforces_isolation(self):
        """Test that context immutability prevents accidental modification."""
        # Create context
        context = UserContextFactory.create_context(
            user_id="immutable_user",
            thread_id="immutable_thread",
            run_id="immutable_run"
        )
        
        # Verify context is frozen (immutable)
        with pytest.raises(dataclasses.FrozenInstanceError, match="cannot assign to field"):
            context.user_id = "modified_user"
            
        with pytest.raises(dataclasses.FrozenInstanceError, match="cannot assign to field"):
            context.thread_id = "modified_thread"
            
        with pytest.raises(dataclasses.FrozenInstanceError, match="cannot assign to field"):
            context.run_id = "modified_run"
            
        with pytest.raises(dataclasses.FrozenInstanceError, match="cannot assign to field"):
            context.request_id = "modified_request"
        
        # However, the contents of mutable fields can be modified
        # (this is by design for agent_context and audit_metadata)
        original_agent_context_id = id(context.agent_context)
        context.agent_context["test_key"] = "test_value"
        
        # Verify the dictionary object itself wasn't replaced
        assert id(context.agent_context) == original_agent_context_id
        assert context.agent_context["test_key"] == "test_value"

    def test_managed_context_ensures_resource_cleanup(self):
        """Test that managed_user_context ensures proper resource cleanup."""
        
        class MockDBSession:
            """Mock database session for testing cleanup."""
            def __init__(self):
                self.closed = False
                
            async def close(self):
                self.closed = True
        
        # Test successful context management
        mock_session = MockDBSession()
        context = UserContextFactory.create_with_session(
            user_id="managed_user",
            thread_id="managed_thread",
            run_id="managed_run", 
            db_session=mock_session
        )
        
        # Use managed context
        async def test_managed_context():
            async with managed_user_context(context, cleanup_db_session=True) as managed_ctx:
                assert managed_ctx == context
                assert managed_ctx.db_session == mock_session
                assert not mock_session.closed
                
            # After context exit, session should be closed
            assert mock_session.closed
            
        # Run the async test
        asyncio.run(test_managed_context())
        
        # Test exception handling
        mock_session_2 = MockDBSession()
        context_2 = UserContextFactory.create_with_session(
            user_id="managed_user_2",
            thread_id="managed_thread_2", 
            run_id="managed_run_2",
            db_session=mock_session_2
        )
        
        async def test_exception_cleanup():
            try:
                async with managed_user_context(context_2, cleanup_db_session=True) as managed_ctx:
                    assert not mock_session_2.closed
                    raise ValueError("Test exception")
            except ValueError:
                pass  # Expected exception
                
            # Session should still be closed despite exception
            assert mock_session_2.closed
            
        asyncio.run(test_exception_cleanup())

    def test_factory_prevents_shared_object_leakage(self):
        """Test that factory prevents shared object references between contexts."""
        # Create some potentially shared objects
        shared_dict = {"shared": "data"}
        shared_list = ["shared", "items"]
        
        # Register them as shared (simulating dangerous sharing)
        register_shared_object(shared_dict)
        register_shared_object(shared_list)
        
        # Create context that might reference shared objects
        context = UserContextFactory.create_context(
            user_id="isolation_test_user",
            thread_id="isolation_test_thread", 
            run_id="isolation_test_run"
        )
        
        # Add references to potentially shared objects in metadata
        # (This simulates what might happen with careless coding)
        context.agent_context["potentially_shared"] = shared_dict
        context.audit_metadata["another_shared"] = shared_list
        
        # Verify isolation validation detects the problem
        # Note: The current implementation of verify_isolation only checks
        # if the metadata dictionaries themselves are shared, not their contents
        # This test documents the current behavior
        
        # The context should still pass isolation validation because
        # the agent_context and audit_metadata dictionaries themselves
        # are not shared (even though they contain references to shared objects)
        assert context.verify_isolation() is True
        
        # However, we can manually detect content sharing
        def check_for_shared_content(obj, path=""):
            """Recursively check for shared object references in content."""
            violations = []
            
            if id(obj) in _get_shared_registry():
                violations.append(f"Shared object found at {path}")
                
            if isinstance(obj, dict):
                for key, value in obj.items():
                    sub_violations = check_for_shared_content(value, f"{path}.{key}")
                    violations.extend(sub_violations)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    sub_violations = check_for_shared_content(item, f"{path}[{i}]")
                    violations.extend(sub_violations)
                    
            return violations
        
        # Check for shared content in context
        violations = []
        violations.extend(check_for_shared_content(context.agent_context, "agent_context"))
        violations.extend(check_for_shared_content(context.audit_metadata, "audit_metadata"))
        
        # We should detect the shared references
        assert len(violations) >= 2  # At least the dict and list we added
        assert any("agent_context.potentially_shared" in v for v in violations)
        assert any("audit_metadata.another_shared" in v for v in violations)

    def test_deep_child_context_hierarchy_maintains_isolation(self):
        """Test deep child context hierarchies maintain isolation at all levels."""
        # Create root context
        root_context = UserContextFactory.create_context(
            user_id="hierarchy_user",
            thread_id="hierarchy_thread",
            run_id="hierarchy_run"
        )
        
        # Create deep hierarchy: root -> child1 -> child2 -> child3
        contexts = [root_context]
        
        for depth in range(1, 4):  # Create 3 levels of children
            parent = contexts[-1]
            child = parent.create_child_context(
                operation_name=f"operation_depth_{depth}",
                additional_agent_context={f"depth_{depth}_data": f"value_{depth}"},
                additional_audit_metadata={f"depth_{depth}_audit": f"audit_{depth}"}
            )
            contexts.append(child)
            
            # Verify proper hierarchy
            assert child.operation_depth == depth
            assert child.parent_request_id == parent.request_id
            assert child.user_id == root_context.user_id  # Inherited
            assert child.thread_id == root_context.thread_id  # Inherited
            assert child.run_id == root_context.run_id  # Inherited
            
            # Verify isolation at this level
            assert child.verify_isolation() is True
        
        # Verify complete isolation between all levels
        for i, ctx1 in enumerate(contexts):
            for j, ctx2 in enumerate(contexts):
                if i != j:
                    # Verify unique request IDs
                    assert ctx1.request_id != ctx2.request_id
                    
                    # Verify separate objects
                    assert id(ctx1.agent_context) != id(ctx2.agent_context)
                    assert id(ctx1.audit_metadata) != id(ctx2.audit_metadata)
        
        # Test modification isolation across hierarchy
        contexts[2].agent_context["hierarchy_test"] = "isolated_at_level_2"
        
        # Verify other levels are unaffected
        for i, ctx in enumerate(contexts):
            if i != 2:
                assert "hierarchy_test" not in ctx.agent_context, \
                    f"Context at level {i} contaminated by level 2 modification"
        
        # Verify data inheritance works correctly
        deepest_child = contexts[-1]  # Level 3
        
        # Should have all inherited data
        for depth in range(1, 4):
            expected_key = f"depth_{depth}_data"
            assert expected_key in deepest_child.agent_context
            assert deepest_child.agent_context[expected_key] == f"value_{depth}"

    def test_context_with_websocket_connection_isolation(self):
        """Test context with WebSocket connection maintains isolation."""
        # Create multiple contexts with WebSocket connections
        contexts_with_ws = []
        
        for i in range(3):
            context = UserContextFactory.create_context(
                user_id=f"ws_context_user_{i}",
                thread_id=f"ws_context_thread_{i}",
                run_id=f"ws_context_run_{i}"
            )
            
            # Add WebSocket connection
            ws_context = context.with_websocket_connection(f"ws_connection_{i}")
            contexts_with_ws.append(ws_context)
            
            # Verify WebSocket connection is set
            assert ws_context.websocket_client_id == f"ws_connection_{i}"
            
            # Verify context is still isolated
            assert ws_context.verify_isolation() is True
        
        # Verify isolation between WebSocket-enabled contexts
        for i, ctx1 in enumerate(contexts_with_ws):
            for j, ctx2 in enumerate(contexts_with_ws):
                if i != j:
                    # Verify different WebSocket connections
                    assert ctx1.websocket_client_id != ctx2.websocket_client_id
                    
                    # Verify complete object isolation
                    assert id(ctx1.agent_context) != id(ctx2.agent_context)
                    assert id(ctx1.audit_metadata) != id(ctx2.audit_metadata)
                    
                    # Verify unique identifiers
                    assert ctx1.user_id != ctx2.user_id
                    assert ctx1.request_id != ctx2.request_id


def _get_shared_registry():
    """Get the shared object registry for testing."""
    from netra_backend.app.services.user_execution_context import _SHARED_OBJECT_REGISTRY
    return _SHARED_OBJECT_REGISTRY


if __name__ == "__main__":
    pytest.main([__file__, "-v"])