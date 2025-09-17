class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()

        '''
        Phase 1 Migration Edge Case Tests for UserExecutionContext

        This module tests edge cases that could break the system during the Phase 1 migration
        of SupervisorAgent, TriageSubAgent, and DataSubAgent to UserExecutionContext pattern.

        Critical edge cases tested:
        - Null or undefined context scenarios
        - Circular context references
        - Memory leaks from context retention
        - Database connection pool exhaustion
        - Async race conditions
        - WebSocket event propagation failures
        - Maximum concurrent user limits
        - Network timeout scenarios
        - Database failure recovery
        - Context inheritance chain limits
        '''

        import asyncio
        import gc
        import pytest
        import threading
        import time
        import uuid
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from datetime import datetime, timezone
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy.exc import DisconnectionError, TimeoutError as SQLTimeoutError
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        from test_framework.database.test_database_manager import DatabaseTestManager
        from auth_service.core.auth_manager import AuthManager
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        from shared.isolated_environment import IsolatedEnvironment

        from netra_backend.app.agents.supervisor.user_execution_context import ( )
        UserExecutionContext,
        InvalidContextError,
        validate_user_context,
        register_shared_object,
        clear_shared_objects
        
        from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
        from netra_backend.app.agents.triage.unified_triage_agent import TriageSubAgent
        from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env


class TestContextNullUndefinedEdgeCases:
        """Test edge cases involving null, undefined, or malformed contexts."""

    def test_none_context_handling(self):
        '''
        Edge Case: System receives None instead of UserExecutionContext.

        This can happen during serialization failures or API boundary issues.
        '''
        pass
    # Test validate_user_context with None
        with pytest.raises(TypeError) as exc_info:
        validate_user_context(None)
        assert "Expected UserExecutionContext" in str(exc_info.value)

        # Test validate_user_context with wrong type
        with pytest.raises(TypeError):
        validate_user_context({"user_id": "test"})  # Dict instead of context

        with pytest.raises(TypeError):
        validate_user_context("invalid_context")  # String instead of context

    def test_malformed_context_attributes(self):
        '''
        Edge Case: Context has unexpected attribute types or values.

        This can happen during deserialization or type conversion errors.
        '''
        pass
    # Test with numeric user_id (should be string)
        with pytest.raises(InvalidContextError):
        UserExecutionContext( )
        user_id=12345,  # Number instead of string
        thread_id="thread_123",
        run_id="run_456"
        

        # Test with list as thread_id (should be string)
        with pytest.raises(InvalidContextError):
        UserExecutionContext( )
        user_id="user_123",
        thread_id=["thread", "123"],  # List instead of string
        run_id="run_456"
            

            # Test with boolean as run_id (should be string)
        with pytest.raises(InvalidContextError):
        UserExecutionContext( )
        user_id="user_123",
        thread_id="thread_456",
        run_id=True  # Boolean instead of string
                

    def test_whitespace_only_context_fields(self):
        '''
        Edge Case: Context fields contain only whitespace characters.

        This can happen with form input or string processing edge cases.
        '''
        pass
        whitespace_patterns = [ ]
        " ",           # Single space
        "\t",          # Tab
        "
        ",          # Newline
        "\r",          # Carriage return
        "\r
        ",        # Windows line ending
        "   ",         # Multiple spaces
        "\t
        \r ",     # Mixed whitespace
    

        for whitespace in whitespace_patterns:
        with pytest.raises(InvalidContextError):
        UserExecutionContext( )
        user_id=whitespace,
        thread_id="thread_123",
        run_id="run_456"
            

        with pytest.raises(InvalidContextError):
        UserExecutionContext( )
        user_id="user_123",
        thread_id=whitespace,
        run_id="run_456"
                

        with pytest.raises(InvalidContextError):
        UserExecutionContext( )
        user_id="user_123",
        thread_id="thread_456",
        run_id=whitespace
                    

    def test_unicode_edge_cases(self):
        '''
        Edge Case: Context fields contain problematic Unicode characters.

        This can cause encoding/decoding issues or database storage problems.
        '''
        pass
        unicode_edge_cases = [ ]
        "user_\u0000null",        # Null character
        "user_\uFFFDreplacement", # Unicode replacement character
        "user_\U0010FFFFmax",     # Maximum Unicode code point
        "user_\u200Bzero_width", # Zero-width space
        "user_\uFEFFbom",         # Byte order mark
        "user_\u001Fcontrol",     # Control character
    

        for unicode_str in unicode_edge_cases:
        try:
        context = UserExecutionContext( )
        user_id=unicode_str,
        thread_id="thread_123",
        run_id="run_456"
            
            # If creation succeeds, verify safe serialization
        context_dict = context.to_dict()
        assert isinstance(context_dict["user_id"], str)
        except (InvalidContextError, UnicodeError, ValueError):
                # It's acceptable to reject problematic Unicode
        pass


class TestCircularReferenceEdgeCases:
        """Test edge cases involving circular references and shared objects."""

    def test_metadata_circular_reference_detection(self):
        '''
        Edge Case: Metadata contains circular references.

        This can cause infinite loops during serialization or JSON encoding.
        '''
        pass
    # Create circular reference in metadata
        circular_metadata = {"level": 0}
        circular_metadata["self"] = circular_metadata

        try:
        context = UserExecutionContext( )
        user_id="user_123",
        thread_id="thread_456",
        run_id="run_789",
        metadata=circular_metadata
        

        # If creation succeeds, verify it handles circular references safely
        try:
        context_dict = context.to_dict()
            # Should not contain circular reference (or handle it safely)
        assert isinstance(context_dict, dict)
        except (ValueError, RecursionError):
                # Acceptable if circular references are detected during serialization
        pass

        except (InvalidContextError, ValueError, RecursionError):
                    # Acceptable if circular references are detected during creation
        pass

    def test_deep_nested_metadata_structures(self):
        '''
        Edge Case: Deeply nested metadata structures that could cause stack overflow.

        This tests the limits of recursive processing in metadata handling.
        '''
        pass
    # Create deeply nested structure
    def create_deep_structure(depth):
        pass
        if depth == 0:
        return "leaf_value"
        return {"level": depth, "nested": create_deep_structure(depth - 1)}

        deep_metadata = create_deep_structure(100)  # 100 levels deep

        try:
        context = UserExecutionContext( )
        user_id="user_123",
        thread_id="thread_456",
        run_id="run_789",
        metadata={"deep_structure": deep_metadata}
            

            # Verify safe serialization (should not cause stack overflow)
        context_dict = context.to_dict()
        assert isinstance(context_dict, dict)

        except (RecursionError, InvalidContextError):
                # Acceptable if deep structures are rejected
        pass

    def test_shared_object_isolation_violation(self):
        '''
        Edge Case: Multiple contexts share the same metadata object.

        This could lead to cross-context data contamination.
        '''
        pass
        shared_metadata = {"shared": True, "data": [1, 2, 3]}
        register_shared_object(shared_metadata)

        try:
        # Create first context with shared metadata
        context1 = UserExecutionContext( )
        user_id="user_001",
        thread_id="thread_001",
        run_id="run_001",
        metadata=shared_metadata
        

        # Create second context with same shared metadata
        context2 = UserExecutionContext( )
        user_id="user_002",
        thread_id="thread_002",
        run_id="run_002",
        metadata=shared_metadata
        

        # Verify isolation (contexts should have separate metadata instances)
        assert id(context1.metadata) != id(context2.metadata)

        # Verify isolation check works
        try:
        context1.verify_isolation()
        context2.verify_isolation()
        except InvalidContextError:
                # Acceptable if shared objects are detected
        pass

        finally:
        clear_shared_objects()


class TestMemoryLeakEdgeCases:
        """Test edge cases that could cause memory leaks."""

    def test_context_retention_memory_leak(self):
        '''
        Edge Case: Contexts are not properly garbage collected.

        This could happen if contexts are retained by closures or event handlers.
        '''
        pass
        import gc
        import weakref

    # Create many contexts and track with weak references
        weak_refs = []

    def create_and_track_contexts(count):
        pass
        for i in range(count):
        context = UserExecutionContext( )
        user_id="",
        thread_id="",
        run_id="",
        metadata={"index": i, "data": list(range(100))}  # Some data
        
        weak_refs.append(weakref.ref(context))
        # Simulate context usage
        _ = context.to_dict()
        _ = context.get_correlation_id()
        del context  # Remove strong reference

        # Create 50 contexts
        create_and_track_contexts(50)

        # Force garbage collection multiple times
        for _ in range(3):
        gc.collect()
        time.sleep(0.01)  # Small delay

            # Check how many contexts were collected
        alive_contexts = sum(1 for ref in weak_refs if ref() is not None)
        collected_contexts = len(weak_refs) - alive_contexts

            # Most contexts should be collected (allowing for some GC variance)
        assert collected_contexts >= len(weak_refs) * 0.8, ""

    def test_child_context_chain_memory_usage(self):
        '''
        Edge Case: Long chains of child contexts consume excessive memory.

        This could happen in recursive operations or deeply nested workflows.
        '''
        pass
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

    # Create a long chain of child contexts
        current_context = UserExecutionContext( )
        user_id="user_chain_test",
        thread_id="thread_chain_test",
        run_id="run_chain_test"
    

        contexts = [current_context]

    # Create chain of 100 child contexts
        for i in range(100):
        current_context = current_context.create_child_context( )
        operation_name="",
        additional_metadata={"step": i, "data": list(range(10))}
        
        contexts.append(current_context)

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 10MB for 100 contexts)
        assert memory_increase < 10 * 1024 * 1024, ""

        # Clean up contexts
        del contexts
        gc.collect()

    def test_metadata_memory_explosion(self):
        '''
        Edge Case: Metadata grows exponentially in child contexts.

        This could happen if each child context copies and expands parent metadata.
        '''
        pass
    # Start with some metadata
        initial_metadata = {"data": list(range(100))}

        context = UserExecutionContext( )
        user_id="user_explosion_test",
        thread_id="thread_explosion_test",
        run_id="run_explosion_test",
        metadata=initial_metadata
    

    # Create child contexts that might accumulate metadata
        for i in range(10):
        context = context.create_child_context( )
        operation_name="",
        additional_metadata={"": list(range(50))}
        

        # Verify metadata size is reasonable
        metadata_size = len(str(context.metadata))
        assert metadata_size < 100000, ""


class TestConcurrencyRaceConditions:
        """Test edge cases related to concurrent access and race conditions."""

@pytest.mark.asyncio
    async def test_concurrent_context_creation(self):
        '''
Edge Case: Many contexts created concurrently causing race conditions.

This could cause ID collisions or resource contention.
'''
pass
async def create_context(index):
    pass
await asyncio.sleep(0)
return UserExecutionContext( )
user_id="",
thread_id="",
run_id="",
metadata={"index": index, "timestamp": time.time()}
    

    # Create 100 contexts concurrently
tasks = [create_context(i) for i in range(100)]
contexts = await asyncio.gather(*tasks)

    # Verify all contexts are unique
user_ids = [ctx.user_id for ctx in contexts]
request_ids = [ctx.request_id for ctx in contexts]

assert len(set(user_ids)) == 100  # All user_ids unique
assert len(set(request_ids)) == 100  # All request_ids unique

    # Verify each context is properly formed
for ctx in contexts:
    assert isinstance(ctx.user_id, str)
assert isinstance(ctx.request_id, str)
assert ctx.user_id.startswith("concurrent_user_")

@pytest.mark.asyncio
    async def test_concurrent_child_context_creation(self):
        '''
Edge Case: Multiple child contexts created concurrently from same parent.

This could cause race conditions in request ID generation or metadata handling.
'''
pass
parent_context = UserExecutionContext( )
user_id="parent_concurrent",
thread_id="parent_thread",
run_id="parent_run",
metadata={"parent_data": "shared"}
            

async def create_child_context(index):
    pass
await asyncio.sleep(0)
return parent_context.create_child_context( )
operation_name="",
additional_metadata={"child_index": index}
    

    # Create 50 child contexts concurrently
tasks = [create_child_context(i) for i in range(50)]
child_contexts = await asyncio.gather(*tasks)

    # Verify all child contexts are unique
request_ids = [ctx.request_id for ctx in child_contexts]
assert len(set(request_ids)) == 50  # All request_ids unique

    # Verify parent data is preserved in all children
for ctx in child_contexts:
    assert ctx.user_id == parent_context.user_id
assert ctx.thread_id == parent_context.thread_id
assert ctx.run_id == parent_context.run_id
assert ctx.request_id != parent_context.request_id
assert "parent_data" in ctx.metadata

def test_thread_safety_context_operations(self):
    '''
Edge Case: Context operations in multithreaded environment.

This could cause race conditions in validation or serialization.
'''
pass
def create_and_serialize_context(thread_id):
    pass
try:
    context = UserExecutionContext( )
user_id="",
thread_id="",
run_id="",
metadata={"thread_id": thread_id, "data": list(range(10))}
        

        # Perform various operations
context_dict = context.to_dict()
correlation_id = context.get_correlation_id()

        # Create child context
child = context.create_child_context( )
operation_name=""
        

return { }
"success": True,
"context_id": context.user_id,
"dict_size": len(context_dict),
"correlation_id": correlation_id,
"child_id": child.request_id
        
except Exception as e:
    return {"success": False, "error": str(e)}

            # Run in multiple threads
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(create_and_serialize_context, i) for i in range(20)]
results = [future.result() for future in as_completed(futures)]

                # Verify all operations succeeded
successful_results = [item for item in []]]
assert len(successful_results) == 20

                # Verify unique IDs across threads
context_ids = [r["context_id"] for r in successful_results]
assert len(set(context_ids)) == 20


class TestDatabaseConnectionEdgeCases:
        """Test edge cases related to database connections and sessions."""

    def test_null_database_session(self):
        '''
        Edge Case: Context created with None database session.

        This should be handled gracefully without breaking the context.
        '''
        pass
        context = UserExecutionContext( )
        user_id="user_no_db",
        thread_id="thread_no_db",
        run_id="run_no_db",
        db_session=None
    

        assert context.db_session is None

    # Should serialize safely
        context_dict = context.to_dict()
        assert context_dict["has_db_session"] is False

    def test_invalid_database_session_type(self):
        '''
        Edge Case: Context created with invalid session type.

        This could happen during dependency injection failures.
        '''
        pass
        invalid_sessions = [ ]
        "not_a_session",
        123,
        {"fake": "session"},
    

        for invalid_session in invalid_sessions:
        # Context creation should still work (validation is at usage time)
        context = UserExecutionContext( )
        user_id="user_invalid_db",
        thread_id="thread_invalid_db",
        run_id="run_invalid_db",
        db_session=invalid_session
        

        # Should indicate session is present (even if invalid)
        context_dict = context.to_dict()
        assert context_dict["has_db_session"] is True

@pytest.mark.asyncio
    async def test_database_session_context_switching(self):
        '''
Edge Case: Rapidly switching database sessions in context.

This could cause connection leaks or session confusion.
'''
pass
base_context = UserExecutionContext( )
user_id="user_session_switch",
thread_id="thread_session_switch",
run_id="run_session_switch"
            

            # Create multiple mock sessions
sessions = [Mock(spec=AsyncSession) for _ in range(10)]

            # Switch sessions rapidly
contexts_with_sessions = []
for i, session in enumerate(sessions):
    ctx = base_context.with_db_session(session)
contexts_with_sessions.append(ctx)

                # Verify each context has correct session
assert ctx.db_session is session
assert ctx.user_id == base_context.user_id  # Other fields preserved

                # Verify all contexts have different session references
session_ids = [id(ctx.db_session) for ctx in contexts_with_sessions]
assert len(set(session_ids)) == 10  # All unique


class TestWebSocketEventEdgeCases:
    """Test edge cases related to WebSocket event propagation."""

    def test_null_websocket_connection(self):
        '''
        Edge Case: Context with None WebSocket connection ID.

        This should not break context operations or serialization.
        '''
        pass
        context = UserExecutionContext( )
        user_id="user_no_ws",
        thread_id="thread_no_ws",
        run_id="run_no_ws",
        websocket_connection_id=None
    

        assert context.websocket_connection_id is None

    # Should serialize safely
        context_dict = context.to_dict()
        assert context_dict["websocket_connection_id"] is None

    def test_invalid_websocket_connection_type(self):
        '''
        Edge Case: Context with invalid WebSocket connection ID type.

        This could happen with type conversion errors.
        '''
        pass
        invalid_connections = [ ]
        123,           # Number instead of string
        ["conn_1"],    # List instead of string
        {"id": "1"},   # Dict instead of string
        True,          # Boolean instead of string
    

        for invalid_conn in invalid_connections:
        # Context should still be created (WebSocket ID type validation is lenient)
        context = UserExecutionContext( )
        user_id="user_invalid_ws",
        thread_id="thread_invalid_ws",
        run_id="run_invalid_ws",
        websocket_connection_id=invalid_conn
        

        assert context.websocket_connection_id == invalid_conn

    def test_websocket_connection_switching(self):
        '''
        Edge Case: Rapidly switching WebSocket connections.

        This could happen during connection drops and reconnections.
        '''
        pass
        base_context = UserExecutionContext( )
        user_id="user_ws_switch",
        thread_id="thread_ws_switch",
        run_id="run_ws_switch"
    

        connection_ids = ["" for i in range(20)]

        contexts_with_ws = []
        for conn_id in connection_ids:
        ctx = base_context.with_websocket_connection(conn_id)
        contexts_with_ws.append(ctx)

        # Verify connection ID is set correctly
        assert ctx.websocket_connection_id == conn_id
        assert ctx.user_id == base_context.user_id  # Other fields preserved

        # Verify all contexts have different connection IDs
        ws_ids = [ctx.websocket_connection_id for ctx in contexts_with_ws]
        assert len(set(ws_ids)) == 20  # All unique


class TestSystemLimitEdgeCases:
        """Test edge cases related to system limits and resource exhaustion."""

    def test_maximum_concurrent_contexts(self):
        '''
        Edge Case: Create maximum number of concurrent contexts.

        This tests system limits and resource exhaustion scenarios.
        '''
        pass
        contexts = []
        max_contexts = 1000  # Reasonable limit for testing

        try:
        for i in range(max_contexts):
        context = UserExecutionContext( )
        user_id="",
        thread_id="",
        run_id="",
        metadata={"index": i}
            
        contexts.append(context)

            # Verify context is properly formed
        if i % 100 == 0:  # Check every 100th context
        assert context.user_id == ""
        context_dict = context.to_dict()
        assert isinstance(context_dict, dict)

            # Verify all contexts are unique
        user_ids = [ctx.user_id for ctx in contexts]
        assert len(set(user_ids)) == max_contexts

        finally:
                # Clean up contexts
        del contexts
        gc.collect()

    def test_context_metadata_size_limits(self):
        '''
        Edge Case: Context metadata exceeding reasonable size limits.

        This tests handling of extremely large metadata payloads.
        '''
        pass
    # Create progressively larger metadata
        large_metadata_sizes = [1000, 10000, 100000]  # Character counts

        for size in large_metadata_sizes:
        large_data = "x" * size

        try:
        context = UserExecutionContext( )
        user_id="user_large_meta",
        thread_id="thread_large_meta",
        run_id="run_large_meta",
        metadata={"large_field": large_data, "size": size}
            

            # Verify context can still be serialized (though it might be truncated)
        context_dict = context.to_dict()
        assert isinstance(context_dict, dict)

            # Verify string representation is bounded
        str_repr = str(context)
        assert len(str_repr) < 50000  # Should be bounded regardless of metadata size

        except (MemoryError, InvalidContextError):
                # Acceptable if extremely large metadata is rejected
        pass

    def test_context_inheritance_depth_limits(self):
        '''
        Edge Case: Deep context inheritance chains.

        This tests limits on how deep child context chains can go.
        '''
        pass
        current_context = UserExecutionContext( )
        user_id="user_deep_chain",
        thread_id="thread_deep_chain",
        run_id="run_deep_chain"
    

        max_depth = 50  # Reasonable inheritance depth limit
        contexts = [current_context]

        for depth in range(1, max_depth + 1):
        try:
        current_context = current_context.create_child_context( )
        operation_name="",
        additional_metadata={"depth": depth}
            
        contexts.append(current_context)

            # Verify depth tracking works
        assert current_context.metadata["operation_depth"] == depth

        except (RecursionError, InvalidContextError):
                # Acceptable if deep inheritance is limited
        break

                # Should have created at least some levels
        assert len(contexts) > 1

                # Verify final context has proper ancestry
        final_context = contexts[-1]
        assert "parent_request_id" in final_context.metadata
        assert final_context.metadata["operation_depth"] >= 1

@pytest.mark.asyncio
    async def test_async_operation_timeout_edge_cases(self):
        '''
Edge Case: Context operations that timeout in async scenarios.

This simulates network timeouts, database timeouts, or slow operations.
'''
pass
                    # Create context normally
context = UserExecutionContext( )
user_id="user_timeout_test",
thread_id="thread_timeout_test",
run_id="run_timeout_test"
                    

                    # Simulate slow operations
async def slow_operation():
    pass
await asyncio.sleep(0.1)  # Simulate slow operation
await asyncio.sleep(0)
return context.to_dict()

async def very_slow_operation():
    pass
await asyncio.sleep(1.0)  # Very slow operation
await asyncio.sleep(0)
return context.get_correlation_id()

    # Test operation with timeout
try:
    result = await asyncio.wait_for(slow_operation(), timeout=0.2)
assert isinstance(result, dict)
except asyncio.TimeoutError:
    pytest.fail("Normal operation should not timeout")

            # Test very slow operation with short timeout
with pytest.raises(asyncio.TimeoutError):
    await asyncio.wait_for(very_slow_operation(), timeout=0.05)


class TestErrorRecoveryEdgeCases:
        """Test edge cases related to error recovery and rollback scenarios."""

    def test_context_creation_partial_failure(self):
        '''
        Edge Case: Context creation fails partially through validation.

        This tests cleanup and error handling during context initialization.
        '''
        pass
    # Mock the validation to fail partway through
        with patch.object(UserExecutionContext, '_validate_metadata') as mock_validate:
        mock_validate.side_effect = InvalidContextError("Metadata validation failed")

        with pytest.raises(InvalidContextError):
        UserExecutionContext( )
        user_id="user_partial_fail",
        thread_id="thread_partial_fail",
        run_id="run_partial_fail",
        metadata={"test": "data"}
            

    def test_context_serialization_failure_recovery(self):
        '''
        Edge Case: Context serialization fails due to non-serializable data.

        This tests graceful handling of serialization errors.
        '''
        pass
    # Create context with non-serializable metadata
        non_serializable_data = lambda x: None x  # Function object

        context = UserExecutionContext( )
        user_id="user_serial_fail",
        thread_id="thread_serial_fail",
        run_id="run_serial_fail",
        metadata={"func": non_serializable_data}
    

    # Serialization might fail, but should be handled gracefully
        try:
        context_dict = context.to_dict()
        # If it succeeds, verify it's safe
        assert isinstance(context_dict, dict)
        except (TypeError, ValueError):
            # Acceptable if non-serializable data causes serialization to fail
        pass

    def test_context_child_creation_failure_rollback(self):
        '''
        Edge Case: Child context creation fails and needs rollback.

        This tests that parent context remains unmodified if child creation fails.
        '''
        pass
        parent_context = UserExecutionContext( )
        user_id="user_child_fail",
        thread_id="thread_child_fail",
        run_id="run_child_fail",
        metadata={"parent": "data"}
    

        original_parent_data = parent_context.metadata.copy()

    # Try to create child with invalid operation name
        try:
        parent_context.create_child_context( )
        operation_name=None,  # Invalid operation name
        additional_metadata={"child": "data"}
        
        except InvalidContextError:
            # Verify parent context is unchanged
        assert parent_context.metadata == original_parent_data
        assert "child" not in parent_context.metadata


        if __name__ == "__main__":
        pytest.main([__file__, "-v", "--tb=short"])
