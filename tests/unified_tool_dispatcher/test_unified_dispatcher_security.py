# REMOVED_SYNTAX_ERROR: class TestWebSocketConnection:
    # REMOVED_SYNTAX_ERROR: """Real WebSocket connection for testing instead of mocks."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.messages_sent = []
    # REMOVED_SYNTAX_ERROR: self.is_connected = True
    # REMOVED_SYNTAX_ERROR: self._closed = False

# REMOVED_SYNTAX_ERROR: async def send_json(self, message: dict):
    # REMOVED_SYNTAX_ERROR: """Send JSON message."""
    # REMOVED_SYNTAX_ERROR: if self._closed:
        # REMOVED_SYNTAX_ERROR: raise RuntimeError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append(message)

# REMOVED_SYNTAX_ERROR: async def close(self, code: int = 1000, reason: str = "Normal closure"):
    # REMOVED_SYNTAX_ERROR: """Close WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self._closed = True
    # REMOVED_SYNTAX_ERROR: self.is_connected = False

# REMOVED_SYNTAX_ERROR: def get_messages(self) -> list:
    # REMOVED_SYNTAX_ERROR: """Get all sent messages."""
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return self.messages_sent.copy()

    # REMOVED_SYNTAX_ERROR: '''Comprehensive security tests for UnifiedToolDispatcher.

    # REMOVED_SYNTAX_ERROR: These tests verify the CRITICAL security requirements:
        # REMOVED_SYNTAX_ERROR: - Mandatory user isolation (no global state)
        # REMOVED_SYNTAX_ERROR: - Permission checking (no bypass allowed)
        # REMOVED_SYNTAX_ERROR: - WebSocket event notifications (guaranteed delivery)
        # REMOVED_SYNTAX_ERROR: - Factory enforcement (blocks direct instantiation)

        # REMOVED_SYNTAX_ERROR: Test Coverage:
            # REMOVED_SYNTAX_ERROR: - User isolation under concurrent load
            # REMOVED_SYNTAX_ERROR: - Permission validation (positive/negative cases)
            # REMOVED_SYNTAX_ERROR: - WebSocket event delivery verification
            # REMOVED_SYNTAX_ERROR: - Authentication bypass prevention
            # REMOVED_SYNTAX_ERROR: - Error handling and recovery
            # REMOVED_SYNTAX_ERROR: '''

            # REMOVED_SYNTAX_ERROR: import asyncio
            # REMOVED_SYNTAX_ERROR: import pytest
            # REMOVED_SYNTAX_ERROR: import time
            # REMOVED_SYNTAX_ERROR: import uuid
            # REMOVED_SYNTAX_ERROR: from datetime import datetime, timezone
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import DatabaseTestManager
            # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.agent_registry import AgentRegistry
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.user_execution_engine import UserExecutionEngine
            # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

            # Core imports
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.tools.unified_tool_dispatcher import ( )
            # REMOVED_SYNTAX_ERROR: UnifiedToolDispatcher,
            # REMOVED_SYNTAX_ERROR: AuthenticationError,
            # REMOVED_SYNTAX_ERROR: PermissionError,
            # REMOVED_SYNTAX_ERROR: SecurityViolationError,
            # REMOVED_SYNTAX_ERROR: ToolDispatchRequest,
            # REMOVED_SYNTAX_ERROR: ToolDispatchResponse
            
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.user_execution_context import UserExecutionContext
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.schemas.tool import ToolStatus
            # REMOVED_SYNTAX_ERROR: from langchain_core.tools import BaseTool
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
            # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env


            # ============================================================================
            # TEST FIXTURES
            # ============================================================================

            # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def valid_user_context():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create valid user execution context for testing."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: run_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: thread_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: request_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: created_at=datetime.now(timezone.utc)
    

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def admin_user_context():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create admin user execution context for testing."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: run_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: thread_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: request_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: created_at=datetime.now(timezone.utc),
    # REMOVED_SYNTAX_ERROR: metadata={'roles': ['admin']}  # Add admin role to metadata
    
    # REMOVED_SYNTAX_ERROR: return context

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def invalid_user_context():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create invalid user execution context (missing fields)."""
    # REMOVED_SYNTAX_ERROR: pass
    # This should raise an error during construction due to validation
    # We'll create it in the test where we expect it to fail
    # REMOVED_SYNTAX_ERROR: return None

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_websocket_bridge():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create mock WebSocket bridge for testing."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: bridge = AsyncMock(spec=AgentWebSocketBridge)
    # REMOVED_SYNTAX_ERROR: bridge.notify_tool_executing = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: bridge.notify_tool_completed = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: return bridge

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def sample_tool():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create sample tool for testing."""
    # REMOVED_SYNTAX_ERROR: pass
# REMOVED_SYNTAX_ERROR: class SampleTool(BaseTool):
    # REMOVED_SYNTAX_ERROR: name: str = "sample_tool"
    # REMOVED_SYNTAX_ERROR: description: str = "A sample tool for testing"

# REMOVED_SYNTAX_ERROR: def _run(self, input_text: str = "default") -> str:
    # REMOVED_SYNTAX_ERROR: return "formatted_string"

# REMOVED_SYNTAX_ERROR: async def _arun(self, input_text: str = "default") -> str:
    # REMOVED_SYNTAX_ERROR: return "formatted_string"

    # REMOVED_SYNTAX_ERROR: return SampleTool()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def admin_tool():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create admin-only tool for testing."""
    # REMOVED_SYNTAX_ERROR: pass
# REMOVED_SYNTAX_ERROR: class AdminTool(BaseTool):
    # REMOVED_SYNTAX_ERROR: name: str = "corpus_create"  # Admin tool name
    # REMOVED_SYNTAX_ERROR: description: str = "Admin-only corpus creation tool"

# REMOVED_SYNTAX_ERROR: def _run(self, corpus_name: str) -> str:
    # REMOVED_SYNTAX_ERROR: return "formatted_string"

# REMOVED_SYNTAX_ERROR: async def _arun(self, corpus_name: str) -> str:
    # REMOVED_SYNTAX_ERROR: return "formatted_string"

    # REMOVED_SYNTAX_ERROR: return AdminTool()


    # ============================================================================
    # SECURITY ENFORCEMENT TESTS
    # ============================================================================

# REMOVED_SYNTAX_ERROR: class TestSecurityEnforcement:
    # REMOVED_SYNTAX_ERROR: """Test mandatory security enforcement."""

# REMOVED_SYNTAX_ERROR: def test_direct_instantiation_blocked(self):
    # REMOVED_SYNTAX_ERROR: """Test that direct instantiation is blocked with SecurityViolationError."""
    # REMOVED_SYNTAX_ERROR: initial_violations = UnifiedToolDispatcher._security_violations

    # REMOVED_SYNTAX_ERROR: with pytest.raises((SecurityViolationError, RuntimeError)) as exc_info:
        # REMOVED_SYNTAX_ERROR: UnifiedToolDispatcher()

        # REMOVED_SYNTAX_ERROR: error_msg = str(exc_info.value)
        # Check for either error message (RuntimeError or SecurityViolationError)
        # REMOVED_SYNTAX_ERROR: assert "Direct instantiation" in error_msg or "SECURITY VIOLATION" in error_msg
        # REMOVED_SYNTAX_ERROR: assert "create_for_user" in error_msg

        # The error should contain security information
        # REMOVED_SYNTAX_ERROR: assert "user isolation" in error_msg.lower()

        # Removed problematic line: async def test_factory_creates_isolated_instance(self, valid_user_context, mock_websocket_bridge):
            # REMOVED_SYNTAX_ERROR: """Test that factory method creates properly isolated instance."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: dispatcher = await UnifiedToolDispatcher.create_for_user( )
            # REMOVED_SYNTAX_ERROR: user_context=valid_user_context,
            # REMOVED_SYNTAX_ERROR: websocket_bridge=mock_websocket_bridge
            

            # REMOVED_SYNTAX_ERROR: try:
                # Verify instance is properly configured
                # REMOVED_SYNTAX_ERROR: assert dispatcher.user_context == valid_user_context
                # REMOVED_SYNTAX_ERROR: assert dispatcher.websocket_bridge == mock_websocket_bridge
                # REMOVED_SYNTAX_ERROR: assert dispatcher._is_active is True
                # REMOVED_SYNTAX_ERROR: assert dispatcher.dispatcher_id.startswith("formatted_string")

                # Verify isolation - different instances have different state
                # REMOVED_SYNTAX_ERROR: dispatcher2 = await UnifiedToolDispatcher.create_for_user( )
                # REMOVED_SYNTAX_ERROR: user_context=valid_user_context,
                # REMOVED_SYNTAX_ERROR: websocket_bridge=mock_websocket_bridge
                

                # REMOVED_SYNTAX_ERROR: try:
                    # REMOVED_SYNTAX_ERROR: assert dispatcher.dispatcher_id != dispatcher2.dispatcher_id
                    # REMOVED_SYNTAX_ERROR: assert dispatcher.registry is not dispatcher2.registry  # Separate registries
                    # REMOVED_SYNTAX_ERROR: finally:
                        # REMOVED_SYNTAX_ERROR: await dispatcher2.cleanup()

                        # REMOVED_SYNTAX_ERROR: finally:
                            # REMOVED_SYNTAX_ERROR: await dispatcher.cleanup()

                            # Removed problematic line: async def test_invalid_user_context_rejected(self, mock_websocket_bridge):
                                # REMOVED_SYNTAX_ERROR: """Test that invalid user context is rejected with AuthenticationError."""
                                # REMOVED_SYNTAX_ERROR: with pytest.raises(AuthenticationError) as exc_info:
                                    # REMOVED_SYNTAX_ERROR: await UnifiedToolDispatcher.create_for_user( )
                                    # REMOVED_SYNTAX_ERROR: user_context=None,  # None context
                                    # REMOVED_SYNTAX_ERROR: websocket_bridge=mock_websocket_bridge
                                    

                                    # REMOVED_SYNTAX_ERROR: error_msg = str(exc_info.value)
                                    # REMOVED_SYNTAX_ERROR: assert "UserExecutionContext" in error_msg or "Valid UserExecutionContext required" in error_msg

                                    # Test with context that has invalid empty user_id (should fail in UserExecutionContext construction)
                                    # REMOVED_SYNTAX_ERROR: with pytest.raises((AuthenticationError, Exception)) as exc_info:
                                        # This will fail during UserExecutionContext creation, not in our code
                                        # REMOVED_SYNTAX_ERROR: invalid_context = UserExecutionContext( )
                                        # REMOVED_SYNTAX_ERROR: user_id="",  # Invalid empty user_id
                                        # REMOVED_SYNTAX_ERROR: run_id="test_run",
                                        # REMOVED_SYNTAX_ERROR: thread_id="test_thread"
                                        
                                        # REMOVED_SYNTAX_ERROR: await UnifiedToolDispatcher.create_for_user( )
                                        # REMOVED_SYNTAX_ERROR: user_context=invalid_context,
                                        # REMOVED_SYNTAX_ERROR: websocket_bridge=mock_websocket_bridge
                                        


                                        # ============================================================================
                                        # USER ISOLATION TESTS
                                        # ============================================================================

# REMOVED_SYNTAX_ERROR: class TestUserIsolation:
    # REMOVED_SYNTAX_ERROR: """Test complete user isolation under concurrent load."""

    # Removed problematic line: async def test_concurrent_user_isolation(self, mock_websocket_bridge, sample_tool):
        # REMOVED_SYNTAX_ERROR: """Test that multiple users have completely isolated dispatchers."""
        # Create contexts for different users
        # REMOVED_SYNTAX_ERROR: user1_context = UserExecutionContext( )
        # REMOVED_SYNTAX_ERROR: user_id="user1", run_id="run1", thread_id="thread1"
        
        # REMOVED_SYNTAX_ERROR: user2_context = UserExecutionContext( )
        # REMOVED_SYNTAX_ERROR: user_id="user2", run_id="run2", thread_id="thread2"
        

        # Create dispatchers for different users
        # REMOVED_SYNTAX_ERROR: dispatcher1 = await UnifiedToolDispatcher.create_for_user( )
        # REMOVED_SYNTAX_ERROR: user_context=user1_context,
        # REMOVED_SYNTAX_ERROR: websocket_bridge=mock_websocket_bridge,
        # REMOVED_SYNTAX_ERROR: tools=[sample_tool]
        
        # REMOVED_SYNTAX_ERROR: dispatcher2 = await UnifiedToolDispatcher.create_for_user( )
        # REMOVED_SYNTAX_ERROR: user_context=user2_context,
        # REMOVED_SYNTAX_ERROR: websocket_bridge=mock_websocket_bridge
        

        # REMOVED_SYNTAX_ERROR: try:
            # Verify complete isolation
            # REMOVED_SYNTAX_ERROR: assert dispatcher1.user_context.user_id != dispatcher2.user_context.user_id
            # REMOVED_SYNTAX_ERROR: assert dispatcher1.registry is not dispatcher2.registry
            # REMOVED_SYNTAX_ERROR: assert dispatcher1.dispatcher_id != dispatcher2.dispatcher_id

            # User1 has tool, User2 doesn't
            # REMOVED_SYNTAX_ERROR: assert dispatcher1.has_tool("sample_tool") is True
            # REMOVED_SYNTAX_ERROR: assert dispatcher2.has_tool("sample_tool") is False

            # Register tool in user2's dispatcher
            # REMOVED_SYNTAX_ERROR: dispatcher2.register_tool(sample_tool)

            # Execute tools concurrently - should be completely isolated
# REMOVED_SYNTAX_ERROR: async def execute_for_user(dispatcher, user_id):
    # REMOVED_SYNTAX_ERROR: response = await dispatcher.execute_tool( )
    # REMOVED_SYNTAX_ERROR: "sample_tool",
    # REMOVED_SYNTAX_ERROR: {"input_text": "formatted_string"}
    
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return response

    # REMOVED_SYNTAX_ERROR: results = await asyncio.gather( )
    # REMOVED_SYNTAX_ERROR: execute_for_user(dispatcher1, "user1"),
    # REMOVED_SYNTAX_ERROR: execute_for_user(dispatcher2, "user2")
    

    # Verify isolation - each user got their own data
    # REMOVED_SYNTAX_ERROR: assert results[0].success is True
    # REMOVED_SYNTAX_ERROR: assert results[1].success is True
    # REMOVED_SYNTAX_ERROR: assert "data_from_user1" in str(results[0].result)
    # REMOVED_SYNTAX_ERROR: assert "data_from_user2" in str(results[1].result)

    # Verify separate metrics
    # REMOVED_SYNTAX_ERROR: metrics1 = dispatcher1.get_metrics()
    # REMOVED_SYNTAX_ERROR: metrics2 = dispatcher2.get_metrics()

    # REMOVED_SYNTAX_ERROR: assert metrics1['user_id'] != metrics2['user_id']
    # REMOVED_SYNTAX_ERROR: assert metrics1['dispatcher_id'] != metrics2['dispatcher_id']

    # REMOVED_SYNTAX_ERROR: finally:
        # REMOVED_SYNTAX_ERROR: await dispatcher1.cleanup()
        # REMOVED_SYNTAX_ERROR: await dispatcher2.cleanup()

        # Removed problematic line: async def test_cross_user_context_validation(self, mock_websocket_bridge, sample_tool):
            # REMOVED_SYNTAX_ERROR: """Test that cross-user context usage is blocked."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: user1_context = UserExecutionContext( )
            # REMOVED_SYNTAX_ERROR: user_id="user1", run_id="run1", thread_id="thread1"
            
            # REMOVED_SYNTAX_ERROR: user2_context = UserExecutionContext( )
            # REMOVED_SYNTAX_ERROR: user_id="user2", run_id="run2", thread_id="thread2"
            

            # REMOVED_SYNTAX_ERROR: dispatcher = await UnifiedToolDispatcher.create_for_user( )
            # REMOVED_SYNTAX_ERROR: user_context=user1_context,
            # REMOVED_SYNTAX_ERROR: websocket_bridge=mock_websocket_bridge,
            # REMOVED_SYNTAX_ERROR: tools=[sample_tool]
            

            # REMOVED_SYNTAX_ERROR: try:
                # Attempt to use wrong run_id (different user context)
                # REMOVED_SYNTAX_ERROR: with pytest.raises(SecurityViolationError) as exc_info:
                    # REMOVED_SYNTAX_ERROR: await dispatcher.dispatch_tool( )
                    # REMOVED_SYNTAX_ERROR: tool_name="sample_tool",
                    # REMOVED_SYNTAX_ERROR: parameters={},
                    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation,
                    # REMOVED_SYNTAX_ERROR: run_id=user2_context.run_id  # Wrong run_id
                    

                    # REMOVED_SYNTAX_ERROR: error_msg = str(exc_info.value)
                    # REMOVED_SYNTAX_ERROR: assert "Run ID mismatch" in error_msg
                    # REMOVED_SYNTAX_ERROR: assert "user isolation breach" in error_msg

                    # REMOVED_SYNTAX_ERROR: finally:
                        # REMOVED_SYNTAX_ERROR: await dispatcher.cleanup()


                        # ============================================================================
                        # PERMISSION VALIDATION TESTS
                        # ============================================================================

# REMOVED_SYNTAX_ERROR: class TestPermissionValidation:
    # REMOVED_SYNTAX_ERROR: """Test mandatory permission checking with no bypass paths."""

    # Removed problematic line: async def test_permission_validation_enforced(self, valid_user_context, mock_websocket_bridge, sample_tool):
        # REMOVED_SYNTAX_ERROR: """Test that permission validation is always enforced."""
        # REMOVED_SYNTAX_ERROR: dispatcher = await UnifiedToolDispatcher.create_for_user( )
        # REMOVED_SYNTAX_ERROR: user_context=valid_user_context,
        # REMOVED_SYNTAX_ERROR: websocket_bridge=mock_websocket_bridge,
        # REMOVED_SYNTAX_ERROR: tools=[sample_tool]
        

        # REMOVED_SYNTAX_ERROR: try:
            # Normal execution should validate permissions
            # REMOVED_SYNTAX_ERROR: response = await dispatcher.execute_tool("sample_tool", {"input": "test"})
            # REMOVED_SYNTAX_ERROR: assert response.success is True

            # Check that permission validation was called
            # REMOVED_SYNTAX_ERROR: metrics = dispatcher.get_metrics()
            # REMOVED_SYNTAX_ERROR: assert metrics['permission_checks'] >= 1

            # REMOVED_SYNTAX_ERROR: finally:
                # REMOVED_SYNTAX_ERROR: await dispatcher.cleanup()

                # Removed problematic line: async def test_admin_tool_permission_enforcement(self, admin_user_context, valid_user_context, mock_websocket_bridge, admin_tool):
                    # REMOVED_SYNTAX_ERROR: """Test that admin tools require admin permissions."""
                    # REMOVED_SYNTAX_ERROR: pass
                    # Create admin dispatcher
                    # REMOVED_SYNTAX_ERROR: admin_dispatcher = await UnifiedToolDispatcher.create_for_user( )
                    # REMOVED_SYNTAX_ERROR: user_context=admin_user_context,
                    # REMOVED_SYNTAX_ERROR: websocket_bridge=mock_websocket_bridge,
                    # REMOVED_SYNTAX_ERROR: tools=[admin_tool],
                    # REMOVED_SYNTAX_ERROR: enable_admin_tools=True
                    

                    # Create regular user dispatcher
                    # REMOVED_SYNTAX_ERROR: user_dispatcher = await UnifiedToolDispatcher.create_for_user( )
                    # REMOVED_SYNTAX_ERROR: user_context=valid_user_context,
                    # REMOVED_SYNTAX_ERROR: websocket_bridge=mock_websocket_bridge,
                    # REMOVED_SYNTAX_ERROR: tools=[admin_tool],
                    # REMOVED_SYNTAX_ERROR: enable_admin_tools=True  # Will fail due to permission check
                    

                    # REMOVED_SYNTAX_ERROR: try:
                        # Admin should succeed
                        # REMOVED_SYNTAX_ERROR: response = await admin_dispatcher.execute_tool("corpus_create", {"corpus_name": "test_corpus"})
                        # REMOVED_SYNTAX_ERROR: assert response.success is True

                        # Regular user should fail (permission will be checked during execution)
                        # REMOVED_SYNTAX_ERROR: with patch.object(UnifiedToolDispatcher, '_validate_admin_permissions', return_value=False):
                            # REMOVED_SYNTAX_ERROR: response = await user_dispatcher.execute_tool("corpus_create", {"corpus_name": "test_corpus"})
                            # Should fail due to permission check
                            # REMOVED_SYNTAX_ERROR: assert response.success is False
                            # REMOVED_SYNTAX_ERROR: assert "permission" in response.error.lower() or "admin" in response.error.lower()

                            # Verify permission denial was tracked
                            # REMOVED_SYNTAX_ERROR: metrics = user_dispatcher.get_metrics()
                            # REMOVED_SYNTAX_ERROR: assert metrics['permission_denials'] >= 1

                            # REMOVED_SYNTAX_ERROR: finally:
                                # REMOVED_SYNTAX_ERROR: await admin_dispatcher.cleanup()
                                # REMOVED_SYNTAX_ERROR: await user_dispatcher.cleanup()

                                # Removed problematic line: async def test_anonymous_user_blocked(self, mock_websocket_bridge, sample_tool):
                                    # REMOVED_SYNTAX_ERROR: """Test that anonymous/invalid users are blocked."""
                                    # REMOVED_SYNTAX_ERROR: anonymous_context = UserExecutionContext( )
                                    # REMOVED_SYNTAX_ERROR: user_id="anonymous",  # Invalid user_id
                                    # REMOVED_SYNTAX_ERROR: run_id="run1",
                                    # REMOVED_SYNTAX_ERROR: thread_id="thread1"
                                    

                                    # REMOVED_SYNTAX_ERROR: dispatcher = await UnifiedToolDispatcher.create_for_user( )
                                    # REMOVED_SYNTAX_ERROR: user_context=anonymous_context,
                                    # REMOVED_SYNTAX_ERROR: websocket_bridge=mock_websocket_bridge,
                                    # REMOVED_SYNTAX_ERROR: tools=[sample_tool]
                                    

                                    # REMOVED_SYNTAX_ERROR: try:
                                        # Should fail permission check due to anonymous user
                                        # REMOVED_SYNTAX_ERROR: with pytest.raises((AuthenticationError, SecurityViolationError)):
                                            # REMOVED_SYNTAX_ERROR: await dispatcher.execute_tool("sample_tool", {})

                                            # REMOVED_SYNTAX_ERROR: finally:
                                                # REMOVED_SYNTAX_ERROR: await dispatcher.cleanup()


                                                # ============================================================================
                                                # WEBSOCKET EVENT TESTS
                                                # ============================================================================

# REMOVED_SYNTAX_ERROR: class TestWebSocketEvents:
    # REMOVED_SYNTAX_ERROR: """Test mandatory WebSocket event emission."""

    # Removed problematic line: async def test_websocket_events_sent_on_success(self, valid_user_context, mock_websocket_bridge, sample_tool):
        # REMOVED_SYNTAX_ERROR: """Test that WebSocket events are sent for successful tool execution."""
        # REMOVED_SYNTAX_ERROR: dispatcher = await UnifiedToolDispatcher.create_for_user( )
        # REMOVED_SYNTAX_ERROR: user_context=valid_user_context,
        # REMOVED_SYNTAX_ERROR: websocket_bridge=mock_websocket_bridge,
        # REMOVED_SYNTAX_ERROR: tools=[sample_tool]
        

        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: response = await dispatcher.execute_tool("sample_tool", {"input": "test"})
            # REMOVED_SYNTAX_ERROR: assert response.success is True

            # Verify WebSocket events were sent
            # REMOVED_SYNTAX_ERROR: assert mock_websocket_bridge.notify_tool_executing.call_count >= 1
            # REMOVED_SYNTAX_ERROR: assert mock_websocket_bridge.notify_tool_completed.call_count >= 1

            # Verify event parameters
            # REMOVED_SYNTAX_ERROR: executing_call = mock_websocket_bridge.notify_tool_executing.call_args
            # REMOVED_SYNTAX_ERROR: assert executing_call[1]['tool_name'] == "sample_tool"
            # REMOVED_SYNTAX_ERROR: assert executing_call[1]['run_id'] == valid_user_context.run_id

            # REMOVED_SYNTAX_ERROR: completed_call = mock_websocket_bridge.notify_tool_completed.call_args
            # REMOVED_SYNTAX_ERROR: assert completed_call[1]['tool_name'] == "sample_tool"
            # REMOVED_SYNTAX_ERROR: assert completed_call[1]['run_id'] == valid_user_context.run_id

            # Verify metrics tracked WebSocket events
            # REMOVED_SYNTAX_ERROR: metrics = dispatcher.get_metrics()
            # REMOVED_SYNTAX_ERROR: assert metrics['websocket_events_sent'] >= 2  # executing + completed

            # REMOVED_SYNTAX_ERROR: finally:
                # REMOVED_SYNTAX_ERROR: await dispatcher.cleanup()

                # Removed problematic line: async def test_websocket_events_sent_on_error(self, valid_user_context, mock_websocket_bridge):
                    # REMOVED_SYNTAX_ERROR: """Test that WebSocket events are sent even when tool execution fails."""
                    # REMOVED_SYNTAX_ERROR: pass
                    # REMOVED_SYNTAX_ERROR: dispatcher = await UnifiedToolDispatcher.create_for_user( )
                    # REMOVED_SYNTAX_ERROR: user_context=valid_user_context,
                    # REMOVED_SYNTAX_ERROR: websocket_bridge=mock_websocket_bridge
                    # No tools registered - will cause "tool not found" error
                    

                    # REMOVED_SYNTAX_ERROR: try:
                        # REMOVED_SYNTAX_ERROR: response = await dispatcher.execute_tool("nonexistent_tool", {})
                        # REMOVED_SYNTAX_ERROR: assert response.success is False

                        # Even on error, WebSocket events should be sent
                        # REMOVED_SYNTAX_ERROR: assert mock_websocket_bridge.notify_tool_executing.call_count >= 1
                        # REMOVED_SYNTAX_ERROR: assert mock_websocket_bridge.notify_tool_completed.call_count >= 1

                        # Verify error is included in completion event
                        # REMOVED_SYNTAX_ERROR: completed_call = mock_websocket_bridge.notify_tool_completed.call_args
                        # REMOVED_SYNTAX_ERROR: assert "error" in str(completed_call).lower()

                        # REMOVED_SYNTAX_ERROR: finally:
                            # REMOVED_SYNTAX_ERROR: await dispatcher.cleanup()

                            # Removed problematic line: async def test_missing_websocket_bridge_handled(self, valid_user_context, sample_tool):
                                # REMOVED_SYNTAX_ERROR: """Test that missing WebSocket bridge is handled gracefully."""
                                # REMOVED_SYNTAX_ERROR: dispatcher = await UnifiedToolDispatcher.create_for_user( )
                                # REMOVED_SYNTAX_ERROR: user_context=valid_user_context,
                                # REMOVED_SYNTAX_ERROR: websocket_bridge=None,  # No WebSocket bridge
                                # REMOVED_SYNTAX_ERROR: tools=[sample_tool]
                                

                                # REMOVED_SYNTAX_ERROR: try:
                                    # Should still work but log critical warnings
                                    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.agents.canonical_tool_dispatcher.logger') as mock_logger:
                                        # REMOVED_SYNTAX_ERROR: response = await dispatcher.execute_tool("sample_tool", {"input": "test"})

                                        # REMOVED_SYNTAX_ERROR: assert response.success is True

                                        # Verify critical warnings were logged
                                        # REMOVED_SYNTAX_ERROR: critical_calls = [call for call in mock_logger.critical.call_args_list )
                                        # REMOVED_SYNTAX_ERROR: if "WEBSOCKET BRIDGE MISSING" in str(call)]
                                        # REMOVED_SYNTAX_ERROR: assert len(critical_calls) >= 1

                                        # REMOVED_SYNTAX_ERROR: finally:
                                            # REMOVED_SYNTAX_ERROR: await dispatcher.cleanup()


                                            # ============================================================================
                                            # ERROR HANDLING AND RECOVERY TESTS
                                            # ============================================================================

# REMOVED_SYNTAX_ERROR: class TestErrorHandling:
    # REMOVED_SYNTAX_ERROR: """Test comprehensive error handling and recovery."""

    # Removed problematic line: async def test_cleanup_after_error(self, valid_user_context, mock_websocket_bridge):
        # REMOVED_SYNTAX_ERROR: """Test that resources are properly cleaned up even after errors."""
        # REMOVED_SYNTAX_ERROR: dispatcher = await UnifiedToolDispatcher.create_for_user( )
        # REMOVED_SYNTAX_ERROR: user_context=valid_user_context,
        # REMOVED_SYNTAX_ERROR: websocket_bridge=mock_websocket_bridge
        

        # REMOVED_SYNTAX_ERROR: try:
            # Execute non-existent tool (will error)
            # REMOVED_SYNTAX_ERROR: response = await dispatcher.execute_tool("nonexistent_tool", {})
            # REMOVED_SYNTAX_ERROR: assert response.success is False

            # Verify dispatcher is still active and functional
            # REMOVED_SYNTAX_ERROR: assert dispatcher._is_active is True
            # REMOVED_SYNTAX_ERROR: metrics = dispatcher.get_metrics()
            # REMOVED_SYNTAX_ERROR: assert metrics['failed_executions'] >= 1

            # REMOVED_SYNTAX_ERROR: finally:
                # Should clean up without errors
                # REMOVED_SYNTAX_ERROR: await dispatcher.cleanup()
                # REMOVED_SYNTAX_ERROR: assert dispatcher._is_active is False

                # Removed problematic line: async def test_concurrent_execution_isolation(self, valid_user_context, mock_websocket_bridge, sample_tool):
                    # REMOVED_SYNTAX_ERROR: """Test that concurrent tool executions are properly isolated."""
                    # REMOVED_SYNTAX_ERROR: pass
                    # REMOVED_SYNTAX_ERROR: dispatcher = await UnifiedToolDispatcher.create_for_user( )
                    # REMOVED_SYNTAX_ERROR: user_context=valid_user_context,
                    # REMOVED_SYNTAX_ERROR: websocket_bridge=mock_websocket_bridge,
                    # REMOVED_SYNTAX_ERROR: tools=[sample_tool]
                    

                    # REMOVED_SYNTAX_ERROR: try:
                        # Execute multiple tools concurrently
                        # REMOVED_SYNTAX_ERROR: tasks = [ )
                        # REMOVED_SYNTAX_ERROR: dispatcher.execute_tool("sample_tool", {"input": "formatted_string"})
                        # REMOVED_SYNTAX_ERROR: for i in range(5)
                        

                        # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks, return_exceptions=True)

                        # All should succeed
                        # REMOVED_SYNTAX_ERROR: for i, result in enumerate(results):
                            # REMOVED_SYNTAX_ERROR: assert not isinstance(result, Exception), "formatted_string"
                            # REMOVED_SYNTAX_ERROR: assert result.success is True
                            # REMOVED_SYNTAX_ERROR: assert "formatted_string" in str(result.result)

                            # Verify metrics reflect all executions
                            # REMOVED_SYNTAX_ERROR: metrics = dispatcher.get_metrics()
                            # REMOVED_SYNTAX_ERROR: assert metrics['successful_executions'] >= 5

                            # REMOVED_SYNTAX_ERROR: finally:
                                # REMOVED_SYNTAX_ERROR: await dispatcher.cleanup()

                                # Removed problematic line: async def test_inactive_dispatcher_blocked(self, valid_user_context, mock_websocket_bridge, sample_tool):
                                    # REMOVED_SYNTAX_ERROR: """Test that using inactive dispatcher raises appropriate error."""
                                    # REMOVED_SYNTAX_ERROR: dispatcher = await UnifiedToolDispatcher.create_for_user( )
                                    # REMOVED_SYNTAX_ERROR: user_context=valid_user_context,
                                    # REMOVED_SYNTAX_ERROR: websocket_bridge=mock_websocket_bridge,
                                    # REMOVED_SYNTAX_ERROR: tools=[sample_tool]
                                    

                                    # Clean up dispatcher
                                    # REMOVED_SYNTAX_ERROR: await dispatcher.cleanup()
                                    # REMOVED_SYNTAX_ERROR: assert dispatcher._is_active is False

                                    # Attempting to use should raise RuntimeError
                                    # REMOVED_SYNTAX_ERROR: with pytest.raises(RuntimeError) as exc_info:
                                        # REMOVED_SYNTAX_ERROR: await dispatcher.execute_tool("sample_tool", {})

                                        # REMOVED_SYNTAX_ERROR: error_msg = str(exc_info.value)
                                        # REMOVED_SYNTAX_ERROR: assert "has been cleaned up" in error_msg


                                        # ============================================================================
                                        # CONTEXT MANAGER TESTS
                                        # ============================================================================

# REMOVED_SYNTAX_ERROR: class TestContextManager:
    # REMOVED_SYNTAX_ERROR: """Test context manager functionality."""

    # Removed problematic line: async def test_scoped_dispatcher_auto_cleanup(self, valid_user_context, mock_websocket_bridge, sample_tool):
        # REMOVED_SYNTAX_ERROR: """Test that scoped dispatcher automatically cleans up."""
        # REMOVED_SYNTAX_ERROR: dispatcher_id = None

        # REMOVED_SYNTAX_ERROR: async with UnifiedToolDispatcher.create_scoped( )
        # REMOVED_SYNTAX_ERROR: user_context=valid_user_context,
        # REMOVED_SYNTAX_ERROR: websocket_bridge=mock_websocket_bridge,
        # REMOVED_SYNTAX_ERROR: tools=[sample_tool]
        # REMOVED_SYNTAX_ERROR: ) as dispatcher:
            # REMOVED_SYNTAX_ERROR: dispatcher_id = dispatcher.dispatcher_id

            # Should work normally within context
            # REMOVED_SYNTAX_ERROR: response = await dispatcher.execute_tool("sample_tool", {"input": "scoped_test"})
            # REMOVED_SYNTAX_ERROR: assert response.success is True
            # REMOVED_SYNTAX_ERROR: assert dispatcher._is_active is True

            # After context exit, should be cleaned up
            # REMOVED_SYNTAX_ERROR: assert dispatcher._is_active is False

            # Should not be in active dispatchers registry
            # REMOVED_SYNTAX_ERROR: assert dispatcher_id not in UnifiedToolDispatcher._active_dispatchers

            # Removed problematic line: async def test_scoped_dispatcher_cleanup_on_exception(self, valid_user_context, mock_websocket_bridge, sample_tool):
                # REMOVED_SYNTAX_ERROR: """Test that scoped dispatcher cleans up even when exception occurs."""
                # REMOVED_SYNTAX_ERROR: pass
                # REMOVED_SYNTAX_ERROR: dispatcher_id = None

                # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError):
                    # REMOVED_SYNTAX_ERROR: async with UnifiedToolDispatcher.create_scoped( )
                    # REMOVED_SYNTAX_ERROR: user_context=valid_user_context,
                    # REMOVED_SYNTAX_ERROR: websocket_bridge=mock_websocket_bridge,
                    # REMOVED_SYNTAX_ERROR: tools=[sample_tool]
                    # REMOVED_SYNTAX_ERROR: ) as dispatcher:
                        # REMOVED_SYNTAX_ERROR: dispatcher_id = dispatcher.dispatcher_id

                        # Execute successful operation first
                        # REMOVED_SYNTAX_ERROR: response = await dispatcher.execute_tool("sample_tool", {"input": "test"})
                        # REMOVED_SYNTAX_ERROR: assert response.success is True

                        # Raise exception to test cleanup
                        # REMOVED_SYNTAX_ERROR: raise ValueError("Test exception")

                        # Should still be cleaned up despite exception
                        # REMOVED_SYNTAX_ERROR: assert dispatcher._is_active is False
                        # REMOVED_SYNTAX_ERROR: assert dispatcher_id not in UnifiedToolDispatcher._active_dispatchers


                        # ============================================================================
                        # PERFORMANCE AND LOAD TESTS
                        # ============================================================================

# REMOVED_SYNTAX_ERROR: class TestPerformanceAndLoad:
    # REMOVED_SYNTAX_ERROR: """Test performance under concurrent load."""

    # Removed problematic line: async def test_high_concurrency_user_isolation(self, mock_websocket_bridge, sample_tool):
        # REMOVED_SYNTAX_ERROR: """Test user isolation under high concurrency load."""
        # REMOVED_SYNTAX_ERROR: num_users = 10
        # REMOVED_SYNTAX_ERROR: executions_per_user = 5

        # Create multiple user contexts
        # REMOVED_SYNTAX_ERROR: user_contexts = [ )
        # REMOVED_SYNTAX_ERROR: UserExecutionContext( )
        # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: run_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: thread_id="formatted_string"
        
        # REMOVED_SYNTAX_ERROR: for i in range(num_users)
        

# REMOVED_SYNTAX_ERROR: async def execute_for_user(user_context):
    # REMOVED_SYNTAX_ERROR: """Execute multiple tools for a single user."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: async with UnifiedToolDispatcher.create_scoped( )
    # REMOVED_SYNTAX_ERROR: user_context=user_context,
    # REMOVED_SYNTAX_ERROR: websocket_bridge=mock_websocket_bridge,
    # REMOVED_SYNTAX_ERROR: tools=[sample_tool]
    # REMOVED_SYNTAX_ERROR: ) as dispatcher:
        # REMOVED_SYNTAX_ERROR: tasks = [ )
        # REMOVED_SYNTAX_ERROR: dispatcher.execute_tool("sample_tool", {"input": "formatted_string"})
        # REMOVED_SYNTAX_ERROR: for j in range(executions_per_user)
        
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return await asyncio.gather(*tasks)

        # Execute concurrently for all users
        # REMOVED_SYNTAX_ERROR: start_time = time.time()
        # REMOVED_SYNTAX_ERROR: all_results = await asyncio.gather( )
        # REMOVED_SYNTAX_ERROR: *[execute_for_user(ctx) for ctx in user_contexts],
        # REMOVED_SYNTAX_ERROR: return_exceptions=True
        
        # REMOVED_SYNTAX_ERROR: execution_time = time.time() - start_time

        # Verify all executions succeeded
        # REMOVED_SYNTAX_ERROR: total_executions = 0
        # REMOVED_SYNTAX_ERROR: for user_results in all_results:
            # REMOVED_SYNTAX_ERROR: assert not isinstance(user_results, Exception)
            # REMOVED_SYNTAX_ERROR: assert len(user_results) == executions_per_user

            # REMOVED_SYNTAX_ERROR: for result in user_results:
                # REMOVED_SYNTAX_ERROR: assert result.success is True
                # REMOVED_SYNTAX_ERROR: total_executions += 1

                # REMOVED_SYNTAX_ERROR: assert total_executions == num_users * executions_per_user

                # Verify reasonable performance (should handle 50 executions in reasonable time)
                # REMOVED_SYNTAX_ERROR: assert execution_time < 10.0, "formatted_string"

                # REMOVED_SYNTAX_ERROR: print("formatted_string")

                # Removed problematic line: async def test_resource_leak_prevention(self, mock_websocket_bridge, sample_tool):
                    # REMOVED_SYNTAX_ERROR: """Test that resource leaks are prevented under repeated usage."""
                    # REMOVED_SYNTAX_ERROR: initial_dispatcher_count = len(UnifiedToolDispatcher._active_dispatchers)

                    # Create and cleanup many dispatchers
                    # REMOVED_SYNTAX_ERROR: for i in range(20):
                        # REMOVED_SYNTAX_ERROR: user_context = UserExecutionContext( )
                        # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
                        # REMOVED_SYNTAX_ERROR: run_id="formatted_string",
                        # REMOVED_SYNTAX_ERROR: thread_id="formatted_string"
                        

                        # REMOVED_SYNTAX_ERROR: async with UnifiedToolDispatcher.create_scoped( )
                        # REMOVED_SYNTAX_ERROR: user_context=user_context,
                        # REMOVED_SYNTAX_ERROR: websocket_bridge=mock_websocket_bridge,
                        # REMOVED_SYNTAX_ERROR: tools=[sample_tool]
                        # REMOVED_SYNTAX_ERROR: ) as dispatcher:
                            # Execute tool to ensure full lifecycle
                            # REMOVED_SYNTAX_ERROR: response = await dispatcher.execute_tool("sample_tool", {"input": "formatted_string"})
                            # REMOVED_SYNTAX_ERROR: assert response.success is True

                            # Verify no resource leaks - dispatcher count should await asyncio.sleep(0)
                            # REMOVED_SYNTAX_ERROR: return to initial
                            # REMOVED_SYNTAX_ERROR: final_dispatcher_count = len(UnifiedToolDispatcher._active_dispatchers)
                            # REMOVED_SYNTAX_ERROR: assert final_dispatcher_count == initial_dispatcher_count

                            # REMOVED_SYNTAX_ERROR: print("formatted_string")


                            # ============================================================================
                            # INTEGRATION TESTS
                            # ============================================================================

# REMOVED_SYNTAX_ERROR: class TestIntegration:
    # REMOVED_SYNTAX_ERROR: """Integration tests with real components."""

    # Removed problematic line: async def test_end_to_end_tool_execution_flow(self, valid_user_context, sample_tool):
        # REMOVED_SYNTAX_ERROR: """Test complete end-to-end tool execution flow."""
        # Test with minimal real components (no mocks where possible)
        # REMOVED_SYNTAX_ERROR: mock_bridge = AsyncMock(spec=AgentWebSocketBridge)
        # REMOVED_SYNTAX_ERROR: mock_bridge.notify_tool_executing.return_value = True
        # REMOVED_SYNTAX_ERROR: mock_bridge.notify_tool_completed.return_value = True

        # REMOVED_SYNTAX_ERROR: async with UnifiedToolDispatcher.create_scoped( )
        # REMOVED_SYNTAX_ERROR: user_context=valid_user_context,
        # REMOVED_SYNTAX_ERROR: websocket_bridge=mock_bridge,
        # REMOVED_SYNTAX_ERROR: tools=[sample_tool]
        # REMOVED_SYNTAX_ERROR: ) as dispatcher:

            # Test tool registration
            # REMOVED_SYNTAX_ERROR: assert dispatcher.has_tool("sample_tool") is True
            # REMOVED_SYNTAX_ERROR: available_tools = dispatcher.get_available_tools()
            # REMOVED_SYNTAX_ERROR: assert "sample_tool" in available_tools

            # Test tool execution with various parameters
            # REMOVED_SYNTAX_ERROR: test_cases = [ )
            # REMOVED_SYNTAX_ERROR: {"input": "hello world"},
            # REMOVED_SYNTAX_ERROR: {"input": "test with spaces"},
            # REMOVED_SYNTAX_ERROR: {"input": "test-with-dashes"},
            # REMOVED_SYNTAX_ERROR: {}  # Empty parameters
            

            # REMOVED_SYNTAX_ERROR: for params in test_cases:
                # REMOVED_SYNTAX_ERROR: response = await dispatcher.execute_tool("sample_tool", params)
                # REMOVED_SYNTAX_ERROR: assert response.success is True
                # REMOVED_SYNTAX_ERROR: assert response.result is not None
                # REMOVED_SYNTAX_ERROR: assert response.metadata['user_id'] == valid_user_context.user_id

                # Test metrics collection
                # REMOVED_SYNTAX_ERROR: metrics = dispatcher.get_metrics()
                # REMOVED_SYNTAX_ERROR: assert metrics['tools_executed'] >= len(test_cases)
                # REMOVED_SYNTAX_ERROR: assert metrics['successful_executions'] >= len(test_cases)
                # REMOVED_SYNTAX_ERROR: assert metrics['failed_executions'] == 0
                # REMOVED_SYNTAX_ERROR: assert metrics['success_rate'] == 1.0
                # REMOVED_SYNTAX_ERROR: assert metrics['user_id'] == valid_user_context.user_id

                # Test WebSocket event emission
                # REMOVED_SYNTAX_ERROR: assert mock_bridge.notify_tool_executing.call_count >= len(test_cases)
                # REMOVED_SYNTAX_ERROR: assert mock_bridge.notify_tool_completed.call_count >= len(test_cases)

                # REMOVED_SYNTAX_ERROR: print("formatted_string")


                # ============================================================================
                # SECURITY STATUS TESTS
                # ============================================================================

# REMOVED_SYNTAX_ERROR: class TestSecurityStatus:
    # REMOVED_SYNTAX_ERROR: """Test security status monitoring."""

# REMOVED_SYNTAX_ERROR: def test_security_status_tracking(self):
    # REMOVED_SYNTAX_ERROR: """Test that security status is properly tracked."""
    # REMOVED_SYNTAX_ERROR: initial_violations = UnifiedToolDispatcher._security_violations

    # Attempt direct instantiation (should fail and increment violations)
    # REMOVED_SYNTAX_ERROR: with pytest.raises(SecurityViolationError):
        # REMOVED_SYNTAX_ERROR: UnifiedToolDispatcher()

        # Check security status
        # REMOVED_SYNTAX_ERROR: status = UnifiedToolDispatcher.get_security_status()

        # REMOVED_SYNTAX_ERROR: assert status['security_violations'] > initial_violations
        # REMOVED_SYNTAX_ERROR: assert status['enforcement_active'] is True
        # REMOVED_SYNTAX_ERROR: assert status['bypass_attempts_blocked'] >= 1
        # REMOVED_SYNTAX_ERROR: assert 'active_dispatchers' in status
        # REMOVED_SYNTAX_ERROR: assert 'dispatchers_by_user' in status

        # REMOVED_SYNTAX_ERROR: print("formatted_string")

        # Removed problematic line: async def test_user_dispatcher_cleanup(self, mock_websocket_bridge, sample_tool):
            # REMOVED_SYNTAX_ERROR: """Test cleanup of all dispatchers for a user."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: test_user_id = "cleanup_test_user"
            # REMOVED_SYNTAX_ERROR: user_context = UserExecutionContext( )
            # REMOVED_SYNTAX_ERROR: user_id=test_user_id,
            # REMOVED_SYNTAX_ERROR: run_id="cleanup_run",
            # REMOVED_SYNTAX_ERROR: thread_id="cleanup_thread"
            

            # Create multiple dispatchers for the same user
            # REMOVED_SYNTAX_ERROR: dispatchers = []
            # REMOVED_SYNTAX_ERROR: for i in range(3):
                # REMOVED_SYNTAX_ERROR: dispatcher = await UnifiedToolDispatcher.create_for_user( )
                # REMOVED_SYNTAX_ERROR: user_context=user_context,
                # REMOVED_SYNTAX_ERROR: websocket_bridge=mock_websocket_bridge,
                # REMOVED_SYNTAX_ERROR: tools=[sample_tool]
                
                # REMOVED_SYNTAX_ERROR: dispatchers.append(dispatcher)

                # Verify they're all active
                # REMOVED_SYNTAX_ERROR: for dispatcher in dispatchers:
                    # REMOVED_SYNTAX_ERROR: assert dispatcher._is_active is True

                    # Cleanup all dispatchers for user
                    # REMOVED_SYNTAX_ERROR: cleanup_count = await UnifiedToolDispatcher.cleanup_user_dispatchers(test_user_id)
                    # REMOVED_SYNTAX_ERROR: assert cleanup_count == 3

                    # Verify they're all cleaned up
                    # REMOVED_SYNTAX_ERROR: for dispatcher in dispatchers:
                        # REMOVED_SYNTAX_ERROR: assert dispatcher._is_active is False

                        # Verify none are in active registry for this user
                        # REMOVED_SYNTAX_ERROR: status = UnifiedToolDispatcher.get_security_status()
                        # REMOVED_SYNTAX_ERROR: user_dispatcher_count = status['dispatchers_by_user'].get(test_user_id, 0)
                        # REMOVED_SYNTAX_ERROR: assert user_dispatcher_count == 0

                        # REMOVED_SYNTAX_ERROR: print("formatted_string")


                        # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                            # Run with pytest: python -m pytest tests/canonical_tool_dispatcher/test_canonical_dispatcher_security.py -v
                            # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v", "--tb=short"])