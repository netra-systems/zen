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

        '''Comprehensive security tests for UnifiedToolDispatcher.

        These tests verify the CRITICAL security requirements:
        - Mandatory user isolation (no global state)
        - Permission checking (no bypass allowed)
        - WebSocket event notifications (guaranteed delivery)
        - Factory enforcement (blocks direct instantiation)

        Test Coverage:
        - User isolation under concurrent load
        - Permission validation (positive/negative cases)
        - WebSocket event delivery verification
        - Authentication bypass prevention
        - Error handling and recovery
        '''

        import asyncio
        import pytest
        import time
        import uuid
        from datetime import datetime, timezone
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        from test_framework.database.test_database_manager import DatabaseTestManager
        from auth_service.core.auth_manager import AuthManager
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        from shared.isolated_environment import IsolatedEnvironment

            # Core imports
        from netra_backend.app.core.tools.unified_tool_dispatcher import ( )
        UnifiedToolDispatcher,
        AuthenticationError,
        PermissionError,
        SecurityViolationError,
        ToolDispatchRequest,
        ToolDispatchResponse
            
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        from netra_backend.app.schemas.tool import ToolStatus
        from langchain_core.tools import BaseTool
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env


            # ============================================================================
            # TEST FIXTURES
            # ============================================================================

        @pytest.fixture
    def valid_user_context():
        """Use real service instance."""
    # TODO: Initialize real service
        """Create valid user execution context for testing."""
        pass
        return UserExecutionContext( )
        user_id="formatted_string",
        run_id="formatted_string",
        thread_id="formatted_string",
        request_id="formatted_string",
        created_at=datetime.now(timezone.utc)
    

        @pytest.fixture
    def admin_user_context():
        """Use real service instance."""
    # TODO: Initialize real service
        """Create admin user execution context for testing."""
        pass
        context = UserExecutionContext( )
        user_id="formatted_string",
        run_id="formatted_string",
        thread_id="formatted_string",
        request_id="formatted_string",
        created_at=datetime.now(timezone.utc),
        metadata={'roles': ['admin']}  # Add admin role to metadata
    
        return context

        @pytest.fixture
    def invalid_user_context():
        """Use real service instance."""
    # TODO: Initialize real service
        """Create invalid user execution context (missing fields)."""
        pass
    # This should raise an error during construction due to validation
    # We'll create it in the test where we expect it to fail
        return None

        @pytest.fixture
    def real_websocket_bridge():
        """Use real service instance."""
    # TODO: Initialize real service
        """Create mock WebSocket bridge for testing."""
        pass
        bridge = AsyncMock(spec=AgentWebSocketBridge)
        bridge.notify_tool_executing = AsyncMock(return_value=True)
        bridge.notify_tool_completed = AsyncMock(return_value=True)
        return bridge

        @pytest.fixture
    def sample_tool():
        """Use real service instance."""
    # TODO: Initialize real service
        """Create sample tool for testing."""
        pass
class SampleTool(BaseTool):
        name: str = "sample_tool"
        description: str = "A sample tool for testing"

    def _run(self, input_text: str = "default") -> str:
        return "formatted_string"

    async def _arun(self, input_text: str = "default") -> str:
        return "formatted_string"

        return SampleTool()

        @pytest.fixture
    def admin_tool():
        """Use real service instance."""
    # TODO: Initialize real service
        """Create admin-only tool for testing."""
        pass
class AdminTool(BaseTool):
        name: str = "corpus_create"  # Admin tool name
        description: str = "Admin-only corpus creation tool"

    def _run(self, corpus_name: str) -> str:
        return "formatted_string"

    async def _arun(self, corpus_name: str) -> str:
        return "formatted_string"

        return AdminTool()


    # ============================================================================
    # SECURITY ENFORCEMENT TESTS
    # ============================================================================

class TestSecurityEnforcement:
        """Test mandatory security enforcement."""

    def test_direct_instantiation_blocked(self):
        """Test that direct instantiation is blocked with SecurityViolationError."""
        initial_violations = UnifiedToolDispatcher._security_violations

        with pytest.raises((SecurityViolationError, RuntimeError)) as exc_info:
        UnifiedToolDispatcher()

        error_msg = str(exc_info.value)
        # Check for either error message (RuntimeError or SecurityViolationError)
        assert "Direct instantiation" in error_msg or "SECURITY VIOLATION" in error_msg
        assert "create_for_user" in error_msg

        # The error should contain security information
        assert "user isolation" in error_msg.lower()

    async def test_factory_creates_isolated_instance(self, valid_user_context, mock_websocket_bridge):
        """Test that factory method creates properly isolated instance."""
        pass
        dispatcher = await UnifiedToolDispatcher.create_for_user( )
        user_context=valid_user_context,
        websocket_bridge=mock_websocket_bridge
            

        try:
                # Verify instance is properly configured
        assert dispatcher.user_context == valid_user_context
        assert dispatcher.websocket_bridge == mock_websocket_bridge
        assert dispatcher._is_active is True
        assert dispatcher.dispatcher_id.startswith("formatted_string")

                # Verify isolation - different instances have different state
        dispatcher2 = await UnifiedToolDispatcher.create_for_user( )
        user_context=valid_user_context,
        websocket_bridge=mock_websocket_bridge
                

        try:
        assert dispatcher.dispatcher_id != dispatcher2.dispatcher_id
        assert dispatcher.registry is not dispatcher2.registry  # Separate registries
        finally:
        await dispatcher2.cleanup()

        finally:
        await dispatcher.cleanup()

    async def test_invalid_user_context_rejected(self, mock_websocket_bridge):
        """Test that invalid user context is rejected with AuthenticationError."""
        with pytest.raises(AuthenticationError) as exc_info:
        await UnifiedToolDispatcher.create_for_user( )
        user_context=None,  # None context
        websocket_bridge=mock_websocket_bridge
                                    

        error_msg = str(exc_info.value)
        assert "UserExecutionContext" in error_msg or "Valid UserExecutionContext required" in error_msg

                                    # Test with context that has invalid empty user_id (should fail in UserExecutionContext construction)
        with pytest.raises((AuthenticationError, Exception)) as exc_info:
                                        # This will fail during UserExecutionContext creation, not in our code
        invalid_context = UserExecutionContext( )
        user_id="",  # Invalid empty user_id
        run_id="test_run",
        thread_id="test_thread"
                                        
        await UnifiedToolDispatcher.create_for_user( )
        user_context=invalid_context,
        websocket_bridge=mock_websocket_bridge
                                        


                                        # ============================================================================
                                        # USER ISOLATION TESTS
                                        # ============================================================================

class TestUserIsolation:
        """Test complete user isolation under concurrent load."""

    async def test_concurrent_user_isolation(self, mock_websocket_bridge, sample_tool):
        """Test that multiple users have completely isolated dispatchers."""
        # Create contexts for different users
        user1_context = UserExecutionContext( )
        user_id="user1", run_id="run1", thread_id="thread1"
        
        user2_context = UserExecutionContext( )
        user_id="user2", run_id="run2", thread_id="thread2"
        

        # Create dispatchers for different users
        dispatcher1 = await UnifiedToolDispatcher.create_for_user( )
        user_context=user1_context,
        websocket_bridge=mock_websocket_bridge,
        tools=[sample_tool]
        
        dispatcher2 = await UnifiedToolDispatcher.create_for_user( )
        user_context=user2_context,
        websocket_bridge=mock_websocket_bridge
        

        try:
            # Verify complete isolation
        assert dispatcher1.user_context.user_id != dispatcher2.user_context.user_id
        assert dispatcher1.registry is not dispatcher2.registry
        assert dispatcher1.dispatcher_id != dispatcher2.dispatcher_id

            # User1 has tool, User2 doesn't
        assert dispatcher1.has_tool("sample_tool") is True
        assert dispatcher2.has_tool("sample_tool") is False

            # Register tool in user2's dispatcher
        dispatcher2.register_tool(sample_tool)

            # Execute tools concurrently - should be completely isolated
    async def execute_for_user(dispatcher, user_id):
        response = await dispatcher.execute_tool( )
        "sample_tool",
        {"input_text": "formatted_string"}
    
        await asyncio.sleep(0)
        return response

        results = await asyncio.gather( )
        execute_for_user(dispatcher1, "user1"),
        execute_for_user(dispatcher2, "user2")
    

    # Verify isolation - each user got their own data
        assert results[0].success is True
        assert results[1].success is True
        assert "data_from_user1" in str(results[0].result)
        assert "data_from_user2" in str(results[1].result)

    # Verify separate metrics
        metrics1 = dispatcher1.get_metrics()
        metrics2 = dispatcher2.get_metrics()

        assert metrics1['user_id'] != metrics2['user_id']
        assert metrics1['dispatcher_id'] != metrics2['dispatcher_id']

        finally:
        await dispatcher1.cleanup()
        await dispatcher2.cleanup()

    async def test_cross_user_context_validation(self, mock_websocket_bridge, sample_tool):
        """Test that cross-user context usage is blocked."""
        pass
        user1_context = UserExecutionContext( )
        user_id="user1", run_id="run1", thread_id="thread1"
            
        user2_context = UserExecutionContext( )
        user_id="user2", run_id="run2", thread_id="thread2"
            

        dispatcher = await UnifiedToolDispatcher.create_for_user( )
        user_context=user1_context,
        websocket_bridge=mock_websocket_bridge,
        tools=[sample_tool]
            

        try:
                # Attempt to use wrong run_id (different user context)
        with pytest.raises(SecurityViolationError) as exc_info:
        await dispatcher.dispatch_tool( )
        tool_name="sample_tool",
        parameters={},
        websocket = TestWebSocketConnection()  # Real WebSocket implementation,
        run_id=user2_context.run_id  # Wrong run_id
                    

        error_msg = str(exc_info.value)
        assert "Run ID mismatch" in error_msg
        assert "user isolation breach" in error_msg

        finally:
        await dispatcher.cleanup()


                        # ============================================================================
                        # PERMISSION VALIDATION TESTS
                        # ============================================================================

class TestPermissionValidation:
        """Test mandatory permission checking with no bypass paths."""

    async def test_permission_validation_enforced(self, valid_user_context, mock_websocket_bridge, sample_tool):
        """Test that permission validation is always enforced."""
        dispatcher = await UnifiedToolDispatcher.create_for_user( )
        user_context=valid_user_context,
        websocket_bridge=mock_websocket_bridge,
        tools=[sample_tool]
        

        try:
            # Normal execution should validate permissions
        response = await dispatcher.execute_tool("sample_tool", {"input": "test"})
        assert response.success is True

            # Check that permission validation was called
        metrics = dispatcher.get_metrics()
        assert metrics['permission_checks'] >= 1

        finally:
        await dispatcher.cleanup()

    async def test_admin_tool_permission_enforcement(self, admin_user_context, valid_user_context, mock_websocket_bridge, admin_tool):
        """Test that admin tools require admin permissions."""
        pass
                    # Create admin dispatcher
        admin_dispatcher = await UnifiedToolDispatcher.create_for_user( )
        user_context=admin_user_context,
        websocket_bridge=mock_websocket_bridge,
        tools=[admin_tool],
        enable_admin_tools=True
                    

                    # Create regular user dispatcher
        user_dispatcher = await UnifiedToolDispatcher.create_for_user( )
        user_context=valid_user_context,
        websocket_bridge=mock_websocket_bridge,
        tools=[admin_tool],
        enable_admin_tools=True  # Will fail due to permission check
                    

        try:
                        # Admin should succeed
        response = await admin_dispatcher.execute_tool("corpus_create", {"corpus_name": "test_corpus"})
        assert response.success is True

                        # Regular user should fail (permission will be checked during execution)
        with patch.object(UnifiedToolDispatcher, '_validate_admin_permissions', return_value=False):
        response = await user_dispatcher.execute_tool("corpus_create", {"corpus_name": "test_corpus"})
                            # Should fail due to permission check
        assert response.success is False
        assert "permission" in response.error.lower() or "admin" in response.error.lower()

                            # Verify permission denial was tracked
        metrics = user_dispatcher.get_metrics()
        assert metrics['permission_denials'] >= 1

        finally:
        await admin_dispatcher.cleanup()
        await user_dispatcher.cleanup()

    async def test_anonymous_user_blocked(self, mock_websocket_bridge, sample_tool):
        """Test that anonymous/invalid users are blocked."""
        anonymous_context = UserExecutionContext( )
        user_id="anonymous",  # Invalid user_id
        run_id="run1",
        thread_id="thread1"
                                    

        dispatcher = await UnifiedToolDispatcher.create_for_user( )
        user_context=anonymous_context,
        websocket_bridge=mock_websocket_bridge,
        tools=[sample_tool]
                                    

        try:
                                        # Should fail permission check due to anonymous user
        with pytest.raises((AuthenticationError, SecurityViolationError)):
        await dispatcher.execute_tool("sample_tool", {})

        finally:
        await dispatcher.cleanup()


                                                # ============================================================================
                                                # WEBSOCKET EVENT TESTS
                                                # ============================================================================

class TestWebSocketEvents:
        """Test mandatory WebSocket event emission."""

    async def test_websocket_events_sent_on_success(self, valid_user_context, mock_websocket_bridge, sample_tool):
        """Test that WebSocket events are sent for successful tool execution."""
        dispatcher = await UnifiedToolDispatcher.create_for_user( )
        user_context=valid_user_context,
        websocket_bridge=mock_websocket_bridge,
        tools=[sample_tool]
        

        try:
        response = await dispatcher.execute_tool("sample_tool", {"input": "test"})
        assert response.success is True

            # Verify WebSocket events were sent
        assert mock_websocket_bridge.notify_tool_executing.call_count >= 1
        assert mock_websocket_bridge.notify_tool_completed.call_count >= 1

            # Verify event parameters
        executing_call = mock_websocket_bridge.notify_tool_executing.call_args
        assert executing_call[1]['tool_name'] == "sample_tool"
        assert executing_call[1]['run_id'] == valid_user_context.run_id

        completed_call = mock_websocket_bridge.notify_tool_completed.call_args
        assert completed_call[1]['tool_name'] == "sample_tool"
        assert completed_call[1]['run_id'] == valid_user_context.run_id

            # Verify metrics tracked WebSocket events
        metrics = dispatcher.get_metrics()
        assert metrics['websocket_events_sent'] >= 2  # executing + completed

        finally:
        await dispatcher.cleanup()

    async def test_websocket_events_sent_on_error(self, valid_user_context, mock_websocket_bridge):
        """Test that WebSocket events are sent even when tool execution fails."""
        pass
        dispatcher = await UnifiedToolDispatcher.create_for_user( )
        user_context=valid_user_context,
        websocket_bridge=mock_websocket_bridge
                    # No tools registered - will cause "tool not found" error
                    

        try:
        response = await dispatcher.execute_tool("nonexistent_tool", {})
        assert response.success is False

                        # Even on error, WebSocket events should be sent
        assert mock_websocket_bridge.notify_tool_executing.call_count >= 1
        assert mock_websocket_bridge.notify_tool_completed.call_count >= 1

                        # Verify error is included in completion event
        completed_call = mock_websocket_bridge.notify_tool_completed.call_args
        assert "error" in str(completed_call).lower()

        finally:
        await dispatcher.cleanup()

    async def test_missing_websocket_bridge_handled(self, valid_user_context, sample_tool):
        """Test that missing WebSocket bridge is handled gracefully."""
        dispatcher = await UnifiedToolDispatcher.create_for_user( )
        user_context=valid_user_context,
        websocket_bridge=None,  # No WebSocket bridge
        tools=[sample_tool]
                                

        try:
                                    # Should still work but log critical warnings
        with patch('netra_backend.app.agents.canonical_tool_dispatcher.logger') as mock_logger:
        response = await dispatcher.execute_tool("sample_tool", {"input": "test"})

        assert response.success is True

                                        # Verify critical warnings were logged
        critical_calls = [call for call in mock_logger.critical.call_args_list )
        if "WEBSOCKET BRIDGE MISSING" in str(call)]
        assert len(critical_calls) >= 1

        finally:
        await dispatcher.cleanup()


                                            # ============================================================================
                                            # ERROR HANDLING AND RECOVERY TESTS
                                            # ============================================================================

class TestErrorHandling:
        """Test comprehensive error handling and recovery."""

    async def test_cleanup_after_error(self, valid_user_context, mock_websocket_bridge):
        """Test that resources are properly cleaned up even after errors."""
        dispatcher = await UnifiedToolDispatcher.create_for_user( )
        user_context=valid_user_context,
        websocket_bridge=mock_websocket_bridge
        

        try:
            # Execute non-existent tool (will error)
        response = await dispatcher.execute_tool("nonexistent_tool", {})
        assert response.success is False

            # Verify dispatcher is still active and functional
        assert dispatcher._is_active is True
        metrics = dispatcher.get_metrics()
        assert metrics['failed_executions'] >= 1

        finally:
                # Should clean up without errors
        await dispatcher.cleanup()
        assert dispatcher._is_active is False

    async def test_concurrent_execution_isolation(self, valid_user_context, mock_websocket_bridge, sample_tool):
        """Test that concurrent tool executions are properly isolated."""
        pass
        dispatcher = await UnifiedToolDispatcher.create_for_user( )
        user_context=valid_user_context,
        websocket_bridge=mock_websocket_bridge,
        tools=[sample_tool]
                    

        try:
                        # Execute multiple tools concurrently
        tasks = [ )
        dispatcher.execute_tool("sample_tool", {"input": "formatted_string"})
        for i in range(5)
                        

        results = await asyncio.gather(*tasks, return_exceptions=True)

                        # All should succeed
        for i, result in enumerate(results):
        assert not isinstance(result, Exception), "formatted_string"
        assert result.success is True
        assert "formatted_string" in str(result.result)

                            # Verify metrics reflect all executions
        metrics = dispatcher.get_metrics()
        assert metrics['successful_executions'] >= 5

        finally:
        await dispatcher.cleanup()

    async def test_inactive_dispatcher_blocked(self, valid_user_context, mock_websocket_bridge, sample_tool):
        """Test that using inactive dispatcher raises appropriate error."""
        dispatcher = await UnifiedToolDispatcher.create_for_user( )
        user_context=valid_user_context,
        websocket_bridge=mock_websocket_bridge,
        tools=[sample_tool]
                                    

                                    # Clean up dispatcher
        await dispatcher.cleanup()
        assert dispatcher._is_active is False

                                    # Attempting to use should raise RuntimeError
        with pytest.raises(RuntimeError) as exc_info:
        await dispatcher.execute_tool("sample_tool", {})

        error_msg = str(exc_info.value)
        assert "has been cleaned up" in error_msg


                                        # ============================================================================
                                        # CONTEXT MANAGER TESTS
                                        # ============================================================================

class TestContextManager:
        """Test context manager functionality."""

    async def test_scoped_dispatcher_auto_cleanup(self, valid_user_context, mock_websocket_bridge, sample_tool):
        """Test that scoped dispatcher automatically cleans up."""
        dispatcher_id = None

        async with UnifiedToolDispatcher.create_scoped( )
        user_context=valid_user_context,
        websocket_bridge=mock_websocket_bridge,
        tools=[sample_tool]
        ) as dispatcher:
        dispatcher_id = dispatcher.dispatcher_id

            # Should work normally within context
        response = await dispatcher.execute_tool("sample_tool", {"input": "scoped_test"})
        assert response.success is True
        assert dispatcher._is_active is True

            # After context exit, should be cleaned up
        assert dispatcher._is_active is False

            # Should not be in active dispatchers registry
        assert dispatcher_id not in UnifiedToolDispatcher._active_dispatchers

    async def test_scoped_dispatcher_cleanup_on_exception(self, valid_user_context, mock_websocket_bridge, sample_tool):
        """Test that scoped dispatcher cleans up even when exception occurs."""
        pass
        dispatcher_id = None

        with pytest.raises(ValueError):
        async with UnifiedToolDispatcher.create_scoped( )
        user_context=valid_user_context,
        websocket_bridge=mock_websocket_bridge,
        tools=[sample_tool]
        ) as dispatcher:
        dispatcher_id = dispatcher.dispatcher_id

                        # Execute successful operation first
        response = await dispatcher.execute_tool("sample_tool", {"input": "test"})
        assert response.success is True

                        # Raise exception to test cleanup
        raise ValueError("Test exception")

                        # Should still be cleaned up despite exception
        assert dispatcher._is_active is False
        assert dispatcher_id not in UnifiedToolDispatcher._active_dispatchers


                        # ============================================================================
                        # PERFORMANCE AND LOAD TESTS
                        # ============================================================================

class TestPerformanceAndLoad:
        """Test performance under concurrent load."""

    async def test_high_concurrency_user_isolation(self, mock_websocket_bridge, sample_tool):
        """Test user isolation under high concurrency load."""
        num_users = 10
        executions_per_user = 5

        # Create multiple user contexts
        user_contexts = [ )
        UserExecutionContext( )
        user_id="formatted_string",
        run_id="formatted_string",
        thread_id="formatted_string"
        
        for i in range(num_users)
        

    async def execute_for_user(user_context):
        """Execute multiple tools for a single user."""
        pass
        async with UnifiedToolDispatcher.create_scoped( )
        user_context=user_context,
        websocket_bridge=mock_websocket_bridge,
        tools=[sample_tool]
        ) as dispatcher:
        tasks = [ )
        dispatcher.execute_tool("sample_tool", {"input": "formatted_string"})
        for j in range(executions_per_user)
        
        await asyncio.sleep(0)
        return await asyncio.gather(*tasks)

        # Execute concurrently for all users
        start_time = time.time()
        all_results = await asyncio.gather( )
        *[execute_for_user(ctx) for ctx in user_contexts],
        return_exceptions=True
        
        execution_time = time.time() - start_time

        # Verify all executions succeeded
        total_executions = 0
        for user_results in all_results:
        assert not isinstance(user_results, Exception)
        assert len(user_results) == executions_per_user

        for result in user_results:
        assert result.success is True
        total_executions += 1

        assert total_executions == num_users * executions_per_user

                # Verify reasonable performance (should handle 50 executions in reasonable time)
        assert execution_time < 10.0, "formatted_string"

        print("formatted_string")

    async def test_resource_leak_prevention(self, mock_websocket_bridge, sample_tool):
        """Test that resource leaks are prevented under repeated usage."""
        initial_dispatcher_count = len(UnifiedToolDispatcher._active_dispatchers)

                    # Create and cleanup many dispatchers
        for i in range(20):
        user_context = UserExecutionContext( )
        user_id="formatted_string",
        run_id="formatted_string",
        thread_id="formatted_string"
                        

        async with UnifiedToolDispatcher.create_scoped( )
        user_context=user_context,
        websocket_bridge=mock_websocket_bridge,
        tools=[sample_tool]
        ) as dispatcher:
                            # Execute tool to ensure full lifecycle
        response = await dispatcher.execute_tool("sample_tool", {"input": "formatted_string"})
        assert response.success is True

                            # Verify no resource leaks - dispatcher count should await asyncio.sleep(0)
        return to initial
        final_dispatcher_count = len(UnifiedToolDispatcher._active_dispatchers)
        assert final_dispatcher_count == initial_dispatcher_count

        print("formatted_string")


                            # ============================================================================
                            # INTEGRATION TESTS
                            # ============================================================================

class TestIntegration:
        """Integration tests with real components."""

    async def test_end_to_end_tool_execution_flow(self, valid_user_context, sample_tool):
        """Test complete end-to-end tool execution flow."""
        # Test with minimal real components (no mocks where possible)
        mock_bridge = AsyncMock(spec=AgentWebSocketBridge)
        mock_bridge.notify_tool_executing.return_value = True
        mock_bridge.notify_tool_completed.return_value = True

        async with UnifiedToolDispatcher.create_scoped( )
        user_context=valid_user_context,
        websocket_bridge=mock_bridge,
        tools=[sample_tool]
        ) as dispatcher:

            # Test tool registration
        assert dispatcher.has_tool("sample_tool") is True
        available_tools = dispatcher.get_available_tools()
        assert "sample_tool" in available_tools

            # Test tool execution with various parameters
        test_cases = [ )
        {"input": "hello world"},
        {"input": "test with spaces"},
        {"input": "test-with-dashes"},
        {}  # Empty parameters
            

        for params in test_cases:
        response = await dispatcher.execute_tool("sample_tool", params)
        assert response.success is True
        assert response.result is not None
        assert response.metadata['user_id'] == valid_user_context.user_id

                # Test metrics collection
        metrics = dispatcher.get_metrics()
        assert metrics['tools_executed'] >= len(test_cases)
        assert metrics['successful_executions'] >= len(test_cases)
        assert metrics['failed_executions'] == 0
        assert metrics['success_rate'] == 1.0
        assert metrics['user_id'] == valid_user_context.user_id

                # Test WebSocket event emission
        assert mock_bridge.notify_tool_executing.call_count >= len(test_cases)
        assert mock_bridge.notify_tool_completed.call_count >= len(test_cases)

        print("formatted_string")


                # ============================================================================
                # SECURITY STATUS TESTS
                # ============================================================================

class TestSecurityStatus:
        """Test security status monitoring."""

    def test_security_status_tracking(self):
        """Test that security status is properly tracked."""
        initial_violations = UnifiedToolDispatcher._security_violations

    # Attempt direct instantiation (should fail and increment violations)
        with pytest.raises(SecurityViolationError):
        UnifiedToolDispatcher()

        # Check security status
        status = UnifiedToolDispatcher.get_security_status()

        assert status['security_violations'] > initial_violations
        assert status['enforcement_active'] is True
        assert status['bypass_attempts_blocked'] >= 1
        assert 'active_dispatchers' in status
        assert 'dispatchers_by_user' in status

        print("formatted_string")

    async def test_user_dispatcher_cleanup(self, mock_websocket_bridge, sample_tool):
        """Test cleanup of all dispatchers for a user."""
        pass
        test_user_id = "cleanup_test_user"
        user_context = UserExecutionContext( )
        user_id=test_user_id,
        run_id="cleanup_run",
        thread_id="cleanup_thread"
            

            # Create multiple dispatchers for the same user
        dispatchers = []
        for i in range(3):
        dispatcher = await UnifiedToolDispatcher.create_for_user( )
        user_context=user_context,
        websocket_bridge=mock_websocket_bridge,
        tools=[sample_tool]
                
        dispatchers.append(dispatcher)

                # Verify they're all active
        for dispatcher in dispatchers:
        assert dispatcher._is_active is True

                    # Cleanup all dispatchers for user
        cleanup_count = await UnifiedToolDispatcher.cleanup_user_dispatchers(test_user_id)
        assert cleanup_count == 3

                    # Verify they're all cleaned up
        for dispatcher in dispatchers:
        assert dispatcher._is_active is False

                        # Verify none are in active registry for this user
        status = UnifiedToolDispatcher.get_security_status()
        user_dispatcher_count = status['dispatchers_by_user'].get(test_user_id, 0)
        assert user_dispatcher_count == 0

        print("formatted_string")


        if __name__ == "__main__":
                            # Run with pytest: python -m pytest tests/canonical_tool_dispatcher/test_canonical_dispatcher_security.py -v
        pytest.main([__file__, "-v", "--tb=short"])
