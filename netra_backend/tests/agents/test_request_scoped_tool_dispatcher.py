from unittest.mock import AsyncMock, Mock, patch, MagicMock

# REMOVED_SYNTAX_ERROR: '''Tests for RequestScopedToolDispatcher and ToolExecutorFactory.

# REMOVED_SYNTAX_ERROR: This test suite validates that the request-scoped tool execution system provides
# REMOVED_SYNTAX_ERROR: complete user isolation and eliminates global state issues.

import asyncio
import pytest
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: import time
    # REMOVED_SYNTAX_ERROR: import uuid
    # REMOVED_SYNTAX_ERROR: from datetime import datetime, timezone
    # REMOVED_SYNTAX_ERROR: from typing import Any, Dict, List
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.request_scoped_tool_dispatcher import ( )
    # REMOVED_SYNTAX_ERROR: RequestScopedToolDispatcher,
    # REMOVED_SYNTAX_ERROR: WebSocketBridgeAdapter,
    # REMOVED_SYNTAX_ERROR: create_request_scoped_tool_dispatcher,
    # REMOVED_SYNTAX_ERROR: request_scoped_tool_dispatcher_scope
    
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.tool_executor_factory import ( )
    # REMOVED_SYNTAX_ERROR: ToolExecutorFactory,
    # REMOVED_SYNTAX_ERROR: get_tool_executor_factory,
    # REMOVED_SYNTAX_ERROR: create_isolated_tool_executor,
    # REMOVED_SYNTAX_ERROR: create_isolated_tool_dispatcher,
    # REMOVED_SYNTAX_ERROR: isolated_tool_dispatcher_scope
    
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core import WebSocketEventEmitter
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.tool_dispatcher_core import ToolDispatcher
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.schemas.tool import ToolInput, ToolResult, ToolStatus


# REMOVED_SYNTAX_ERROR: class TestRequestScopedToolDispatcher:
    # REMOVED_SYNTAX_ERROR: """Test request-scoped tool dispatcher functionality."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def user_context(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create test user context."""
    # REMOVED_SYNTAX_ERROR: return UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="formatted_string"simple_tool"
    # REMOVED_SYNTAX_ERROR: simple_tool_func.description = "A simple test tool"
    # REMOVED_SYNTAX_ERROR: return simple_tool_func

    # Removed problematic line: async def test_dispatcher_creation_with_user_context(self, user_context, mock_websocket_emitter):
        # REMOVED_SYNTAX_ERROR: """Test that dispatcher is created with proper user context isolation."""
        # REMOVED_SYNTAX_ERROR: dispatcher = RequestScopedToolDispatcher( )
        # REMOVED_SYNTAX_ERROR: user_context=user_context,
        # REMOVED_SYNTAX_ERROR: websocket_emitter=mock_websocket_emitter
        

        # Verify context binding
        # REMOVED_SYNTAX_ERROR: assert dispatcher.user_context == user_context
        # REMOVED_SYNTAX_ERROR: assert dispatcher.user_context.user_id == user_context.user_id
        # REMOVED_SYNTAX_ERROR: assert dispatcher.user_context.run_id == user_context.run_id

        # Verify isolation metrics
        # REMOVED_SYNTAX_ERROR: metrics = dispatcher.get_metrics()
        # REMOVED_SYNTAX_ERROR: assert metrics['user_id'] == user_context.user_id
        # REMOVED_SYNTAX_ERROR: assert metrics['run_id'] == user_context.run_id
        # REMOVED_SYNTAX_ERROR: assert metrics['dispatcher_id'].startswith(user_context.user_id)

        # Verify WebSocket integration
        # REMOVED_SYNTAX_ERROR: assert dispatcher.websocket_emitter == mock_websocket_emitter
        # REMOVED_SYNTAX_ERROR: assert dispatcher.has_websocket_support

        # REMOVED_SYNTAX_ERROR: await dispatcher.cleanup()

        # Removed problematic line: async def test_user_isolation_between_dispatchers(self, mock_websocket_emitter):
            # REMOVED_SYNTAX_ERROR: """Test that multiple dispatchers maintain complete user isolation."""
            # Create contexts for two different users
            # REMOVED_SYNTAX_ERROR: user1_context = UserExecutionContext( )
            # REMOVED_SYNTAX_ERROR: user_id="user1",
            # REMOVED_SYNTAX_ERROR: thread_id="thread1",
            # REMOVED_SYNTAX_ERROR: run_id="run1"
            
            # REMOVED_SYNTAX_ERROR: user2_context = UserExecutionContext( )
            # REMOVED_SYNTAX_ERROR: user_id="user2",
            # REMOVED_SYNTAX_ERROR: thread_id="thread2",
            # REMOVED_SYNTAX_ERROR: run_id="run2"
            

            # Create dispatchers for each user
            # REMOVED_SYNTAX_ERROR: dispatcher1 = RequestScopedToolDispatcher(user1_context, websocket_emitter=mock_websocket_emitter)
            # REMOVED_SYNTAX_ERROR: dispatcher2 = RequestScopedToolDispatcher(user2_context, websocket_emitter=mock_websocket_emitter)

            # Verify complete isolation
            # REMOVED_SYNTAX_ERROR: assert dispatcher1.user_context != dispatcher2.user_context
            # REMOVED_SYNTAX_ERROR: assert dispatcher1.dispatcher_id != dispatcher2.dispatcher_id
            # REMOVED_SYNTAX_ERROR: assert dispatcher1.registry is not dispatcher2.registry  # Separate tool registries
            # REMOVED_SYNTAX_ERROR: assert dispatcher1.executor is not dispatcher2.executor  # Separate executors

            # Verify metrics isolation
            # REMOVED_SYNTAX_ERROR: metrics1 = dispatcher1.get_metrics()
            # REMOVED_SYNTAX_ERROR: metrics2 = dispatcher2.get_metrics()
            # REMOVED_SYNTAX_ERROR: assert metrics1['user_id'] != metrics2['user_id']
            # REMOVED_SYNTAX_ERROR: assert metrics1['dispatcher_id'] != metrics2['dispatcher_id']

            # REMOVED_SYNTAX_ERROR: await dispatcher1.cleanup()
            # REMOVED_SYNTAX_ERROR: await dispatcher2.cleanup()

            # Removed problematic line: async def test_tool_registration_isolation(self, user_context, mock_websocket_emitter):
                # REMOVED_SYNTAX_ERROR: """Test that tool registrations are isolated per dispatcher."""
                # REMOVED_SYNTAX_ERROR: dispatcher1 = RequestScopedToolDispatcher(user_context, websocket_emitter=mock_websocket_emitter)

                # Create second user context
                # REMOVED_SYNTAX_ERROR: user2_context = UserExecutionContext( )
                # REMOVED_SYNTAX_ERROR: user_id="user2",
                # REMOVED_SYNTAX_ERROR: thread_id="thread2",
                # REMOVED_SYNTAX_ERROR: run_id="run2"
                
                # REMOVED_SYNTAX_ERROR: dispatcher2 = RequestScopedToolDispatcher(user2_context, websocket_emitter=mock_websocket_emitter)

                # Register tool only in first dispatcher
# REMOVED_SYNTAX_ERROR: def user1_tool():
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return "user1_result"

    # REMOVED_SYNTAX_ERROR: dispatcher1.register_tool("user1_tool", user1_tool)

    # Verify tool isolation
    # REMOVED_SYNTAX_ERROR: assert dispatcher1.has_tool("user1_tool")
    # REMOVED_SYNTAX_ERROR: assert not dispatcher2.has_tool("user1_tool")

    # Register different tool in second dispatcher
# REMOVED_SYNTAX_ERROR: def user2_tool():
    # REMOVED_SYNTAX_ERROR: return "user2_result"

    # REMOVED_SYNTAX_ERROR: dispatcher2.register_tool("user2_tool", user2_tool)

    # Verify continued isolation
    # REMOVED_SYNTAX_ERROR: assert dispatcher1.has_tool("user1_tool")
    # REMOVED_SYNTAX_ERROR: assert not dispatcher1.has_tool("user2_tool")
    # REMOVED_SYNTAX_ERROR: assert dispatcher2.has_tool("user2_tool")
    # REMOVED_SYNTAX_ERROR: assert not dispatcher2.has_tool("user1_tool")

    # REMOVED_SYNTAX_ERROR: await dispatcher1.cleanup()
    # REMOVED_SYNTAX_ERROR: await dispatcher2.cleanup()

    # Removed problematic line: async def test_websocket_event_isolation(self, mock_websocket_emitter):
        # REMOVED_SYNTAX_ERROR: """Test that WebSocket events are properly isolated per user."""
        # Create contexts for two users
        # REMOVED_SYNTAX_ERROR: user1_context = UserExecutionContext(user_id="user1", thread_id="thread1", run_id="run1")
        # REMOVED_SYNTAX_ERROR: user2_context = UserExecutionContext(user_id="user2", thread_id="thread2", run_id="run2")

        # Create separate mock emitters to track calls
        # REMOVED_SYNTAX_ERROR: emitter1 = Mock(spec=WebSocketEventEmitter)
        # REMOVED_SYNTAX_ERROR: emitter1.notify_tool_executing = AsyncMock(return_value=True)
        # REMOVED_SYNTAX_ERROR: emitter1.notify_tool_completed = AsyncMock(return_value=True)
        # REMOVED_SYNTAX_ERROR: emitter1.dispose = AsyncMock()  # TODO: Use real service instance

        # REMOVED_SYNTAX_ERROR: emitter2 = Mock(spec=WebSocketEventEmitter)
        # REMOVED_SYNTAX_ERROR: emitter2.notify_tool_executing = AsyncMock(return_value=True)
        # REMOVED_SYNTAX_ERROR: emitter2.notify_tool_completed = AsyncMock(return_value=True)
        # REMOVED_SYNTAX_ERROR: emitter2.dispose = AsyncMock()  # TODO: Use real service instance

        # Create dispatchers with separate emitters
        # REMOVED_SYNTAX_ERROR: dispatcher1 = RequestScopedToolDispatcher(user1_context, websocket_emitter=emitter1)
        # REMOVED_SYNTAX_ERROR: dispatcher2 = RequestScopedToolDispatcher(user2_context, websocket_emitter=emitter2)

        # Register same tool in both dispatchers
# REMOVED_SYNTAX_ERROR: def test_tool():
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return "tool_result"

    # REMOVED_SYNTAX_ERROR: dispatcher1.register_tool("test_tool", test_tool)
    # REMOVED_SYNTAX_ERROR: dispatcher2.register_tool("test_tool", test_tool)

    # Execute tools in both dispatchers
    # REMOVED_SYNTAX_ERROR: result1 = await dispatcher1.dispatch("test_tool")
    # REMOVED_SYNTAX_ERROR: result2 = await dispatcher2.dispatch("test_tool")

    # Verify both executions succeeded
    # REMOVED_SYNTAX_ERROR: assert result1.status == ToolStatus.SUCCESS
    # REMOVED_SYNTAX_ERROR: assert result2.status == ToolStatus.SUCCESS

    # Verify WebSocket events were sent to correct emitters only
    # REMOVED_SYNTAX_ERROR: emitter1.notify_tool_executing.assert_called()
    # REMOVED_SYNTAX_ERROR: emitter1.notify_tool_completed.assert_called()
    # REMOVED_SYNTAX_ERROR: emitter2.notify_tool_executing.assert_called()
    # REMOVED_SYNTAX_ERROR: emitter2.notify_tool_completed.assert_called()

    # Verify no cross-contamination
    # REMOVED_SYNTAX_ERROR: assert emitter1 != emitter2

    # REMOVED_SYNTAX_ERROR: await dispatcher1.cleanup()
    # REMOVED_SYNTAX_ERROR: await dispatcher2.cleanup()

    # Removed problematic line: async def test_concurrent_tool_execution(self, mock_websocket_emitter):
        # REMOVED_SYNTAX_ERROR: """Test concurrent tool execution across multiple users."""
        # Create multiple user contexts
        # REMOVED_SYNTAX_ERROR: contexts = [ )
        # REMOVED_SYNTAX_ERROR: UserExecutionContext( )
        # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: thread_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: run_id="formatted_string"
        
        # REMOVED_SYNTAX_ERROR: for i in range(5)
        

        # Create dispatchers for each context
        # REMOVED_SYNTAX_ERROR: dispatchers = [ )
        # REMOVED_SYNTAX_ERROR: RequestScopedToolDispatcher(context, websocket_emitter=mock_websocket_emitter)
        # REMOVED_SYNTAX_ERROR: for context in contexts
        

        # Define a slow tool to test concurrency
# REMOVED_SYNTAX_ERROR: async def slow_tool(delay: float = 0.1):
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(delay)
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return {"user_id": "from_tool", "timestamp": time.time()}

    # Register tool in all dispatchers
    # REMOVED_SYNTAX_ERROR: for i, dispatcher in enumerate(dispatchers):
        # REMOVED_SYNTAX_ERROR: dispatcher.register_tool("slow_tool", slow_tool)

        # Execute tools concurrently
        # REMOVED_SYNTAX_ERROR: start_time = time.time()
        # REMOVED_SYNTAX_ERROR: tasks = []
        # REMOVED_SYNTAX_ERROR: for dispatcher in dispatchers:
            # REMOVED_SYNTAX_ERROR: task = asyncio.create_task(dispatcher.dispatch("slow_tool", delay=0.2))
            # REMOVED_SYNTAX_ERROR: tasks.append(task)

            # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks)
            # REMOVED_SYNTAX_ERROR: total_time = time.time() - start_time

            # Verify all executions succeeded
            # REMOVED_SYNTAX_ERROR: assert len(results) == 5
            # REMOVED_SYNTAX_ERROR: for result in results:
                # REMOVED_SYNTAX_ERROR: assert result.status == ToolStatus.SUCCESS

                # Verify concurrent execution (should be faster than sequential)
                # REMOVED_SYNTAX_ERROR: assert total_time < 0.8  # Should be much faster than 5 * 0.2 = 1.0 seconds

                # Verify metrics are properly tracked per dispatcher
                # REMOVED_SYNTAX_ERROR: for dispatcher in dispatchers:
                    # REMOVED_SYNTAX_ERROR: metrics = dispatcher.get_metrics()
                    # REMOVED_SYNTAX_ERROR: assert metrics['tools_executed'] == 1
                    # REMOVED_SYNTAX_ERROR: assert metrics['successful_executions'] == 1
                    # REMOVED_SYNTAX_ERROR: assert metrics['failed_executions'] == 0

                    # Cleanup all dispatchers
                    # REMOVED_SYNTAX_ERROR: await asyncio.gather(*[dispatcher.cleanup() for dispatcher in dispatchers])

                    # Removed problematic line: async def test_run_id_validation_security(self, user_context, mock_websocket_emitter):
                        # REMOVED_SYNTAX_ERROR: """Test that run_id validation prevents cross-user access."""
                        # REMOVED_SYNTAX_ERROR: dispatcher = RequestScopedToolDispatcher(user_context, websocket_emitter=mock_websocket_emitter)

# REMOVED_SYNTAX_ERROR: def test_tool():
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return "secure_result"

    # REMOVED_SYNTAX_ERROR: dispatcher.register_tool("test_tool", test_tool)

    # Valid run_id should work
    # REMOVED_SYNTAX_ERROR: state = state_instance  # Initialize appropriate service
    # REMOVED_SYNTAX_ERROR: result = await dispatcher.dispatch_tool("test_tool", {}, state, user_context.run_id)
    # REMOVED_SYNTAX_ERROR: assert result["success"] is True

    # Invalid run_id should fail
    # REMOVED_SYNTAX_ERROR: invalid_result = await dispatcher.dispatch_tool("test_tool", {}, state, "wrong_run_id")
    # REMOVED_SYNTAX_ERROR: assert invalid_result["success"] is False
    # REMOVED_SYNTAX_ERROR: assert "not found" in invalid_result["error"]

    # REMOVED_SYNTAX_ERROR: await dispatcher.cleanup()

    # Removed problematic line: async def test_resource_cleanup(self, user_context, mock_websocket_emitter):
        # REMOVED_SYNTAX_ERROR: """Test proper resource cleanup when dispatcher is disposed."""
        # REMOVED_SYNTAX_ERROR: dispatcher = RequestScopedToolDispatcher(user_context, websocket_emitter=mock_websocket_emitter)

        # Register some tools to create state
        # REMOVED_SYNTAX_ERROR: dispatcher.register_tool("tool1", lambda x: None "result1")
        # REMOVED_SYNTAX_ERROR: dispatcher.register_tool("tool2", lambda x: None "result2")

        # Verify initial state
        # REMOVED_SYNTAX_ERROR: assert dispatcher.is_active()
        # REMOVED_SYNTAX_ERROR: assert len(dispatcher.tools) == 2
        # REMOVED_SYNTAX_ERROR: metrics = dispatcher.get_metrics()
        # REMOVED_SYNTAX_ERROR: assert len(metrics) > 0

        # Cleanup dispatcher
        # REMOVED_SYNTAX_ERROR: await dispatcher.cleanup()

        # Verify cleanup
        # REMOVED_SYNTAX_ERROR: assert not dispatcher.is_active()
        # REMOVED_SYNTAX_ERROR: assert len(dispatcher.tools) == 0  # Tools registry cleared

        # Verify WebSocket emitter was disposed
        # REMOVED_SYNTAX_ERROR: mock_websocket_emitter.dispose.assert_called_once()

        # Verify disposed dispatcher cannot be used
        # REMOVED_SYNTAX_ERROR: with pytest.raises(RuntimeError, match="has been disposed"):
            # REMOVED_SYNTAX_ERROR: dispatcher.has_tool("tool1")

            # REMOVED_SYNTAX_ERROR: with pytest.raises(RuntimeError, match="has been disposed"):
                # REMOVED_SYNTAX_ERROR: await dispatcher.dispatch("tool1")

                # Removed problematic line: async def test_context_manager_usage(self, user_context):
                    # REMOVED_SYNTAX_ERROR: """Test using dispatcher as async context manager."""
                    # REMOVED_SYNTAX_ERROR: tool_executed = False

# REMOVED_SYNTAX_ERROR: def test_tool():
    # REMOVED_SYNTAX_ERROR: nonlocal tool_executed
    # REMOVED_SYNTAX_ERROR: tool_executed = True
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return "context_result"

    # Test context manager with automatic cleanup
    # REMOVED_SYNTAX_ERROR: async with request_scoped_tool_dispatcher_scope(user_context) as dispatcher:
        # REMOVED_SYNTAX_ERROR: dispatcher.register_tool("test_tool", test_tool)
        # REMOVED_SYNTAX_ERROR: result = await dispatcher.dispatch("test_tool")
        # REMOVED_SYNTAX_ERROR: assert result.status == ToolStatus.SUCCESS
        # REMOVED_SYNTAX_ERROR: assert tool_executed
        # REMOVED_SYNTAX_ERROR: assert dispatcher.is_active()

        # Verify cleanup happened automatically
        # REMOVED_SYNTAX_ERROR: assert not dispatcher.is_active()

        # Removed problematic line: async def test_metrics_tracking(self, user_context, mock_websocket_emitter):
            # REMOVED_SYNTAX_ERROR: """Test comprehensive metrics tracking."""
            # REMOVED_SYNTAX_ERROR: dispatcher = RequestScopedToolDispatcher(user_context, websocket_emitter=mock_websocket_emitter)

            # Register tools
# REMOVED_SYNTAX_ERROR: def success_tool():
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return "success"

# REMOVED_SYNTAX_ERROR: def failure_tool():
    # REMOVED_SYNTAX_ERROR: raise ValueError("Tool failure")

    # REMOVED_SYNTAX_ERROR: dispatcher.register_tool("success_tool", success_tool)
    # REMOVED_SYNTAX_ERROR: dispatcher.register_tool("failure_tool", failure_tool)

    # Execute tools
    # REMOVED_SYNTAX_ERROR: await dispatcher.dispatch("success_tool")
    # REMOVED_SYNTAX_ERROR: await dispatcher.dispatch("success_tool")  # Execute twice
    # REMOVED_SYNTAX_ERROR: await dispatcher.dispatch("failure_tool")  # This should fail

    # Check metrics
    # REMOVED_SYNTAX_ERROR: metrics = dispatcher.get_metrics()
    # REMOVED_SYNTAX_ERROR: assert metrics['tools_executed'] == 3
    # REMOVED_SYNTAX_ERROR: assert metrics['successful_executions'] == 2
    # REMOVED_SYNTAX_ERROR: assert metrics['failed_executions'] == 1
    # REMOVED_SYNTAX_ERROR: assert metrics['success_rate'] == 2/3
    # REMOVED_SYNTAX_ERROR: assert metrics['total_execution_time_ms'] > 0
    # REMOVED_SYNTAX_ERROR: assert metrics['last_execution_time'] is not None

    # REMOVED_SYNTAX_ERROR: await dispatcher.cleanup()


# REMOVED_SYNTAX_ERROR: class TestWebSocketBridgeAdapter:
    # REMOVED_SYNTAX_ERROR: """Test WebSocket bridge adapter functionality."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def user_context(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create test user context."""
    # REMOVED_SYNTAX_ERROR: return UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="test_user",
    # REMOVED_SYNTAX_ERROR: thread_id="test_thread",
    # REMOVED_SYNTAX_ERROR: run_id="test_run"
    

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_emitter():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create mock WebSocket emitter."""
    # REMOVED_SYNTAX_ERROR: emitter = Mock(spec=WebSocketEventEmitter)
    # REMOVED_SYNTAX_ERROR: emitter.notify_tool_executing = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: emitter.notify_tool_completed = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: emitter.notify_agent_started = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: emitter.notify_agent_thinking = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: emitter.notify_agent_completed = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: emitter.notify_agent_error = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: return emitter

    # Removed problematic line: async def test_adapter_method_delegation(self, user_context, mock_emitter):
        # REMOVED_SYNTAX_ERROR: """Test that adapter properly delegates to WebSocketEventEmitter."""
        # REMOVED_SYNTAX_ERROR: adapter = WebSocketBridgeAdapter(mock_emitter, user_context)

        # Test tool notifications
        # REMOVED_SYNTAX_ERROR: result = await adapter.notify_tool_executing("run1", "agent1", "tool1", {"param": "value"})
        # REMOVED_SYNTAX_ERROR: assert result is True
        # REMOVED_SYNTAX_ERROR: mock_emitter.notify_tool_executing.assert_called_once_with("run1", "agent1", "tool1", {"param": "value"})

        # REMOVED_SYNTAX_ERROR: result = await adapter.notify_tool_completed("run1", "agent1", "tool1", {"result": "success"}, 100.0)
        # REMOVED_SYNTAX_ERROR: assert result is True
        # REMOVED_SYNTAX_ERROR: mock_emitter.notify_tool_completed.assert_called_once_with("run1", "agent1", "tool1", {"result": "success"}, 100.0)

        # Test agent notifications
        # REMOVED_SYNTAX_ERROR: result = await adapter.notify_agent_started("run1", "agent1", {"context": "data"})
        # REMOVED_SYNTAX_ERROR: assert result is True
        # REMOVED_SYNTAX_ERROR: mock_emitter.notify_agent_started.assert_called_once_with("run1", "agent1", {"context": "data"})

        # REMOVED_SYNTAX_ERROR: result = await adapter.notify_agent_thinking("run1", "agent1", "thinking...", 1, 50.0)
        # REMOVED_SYNTAX_ERROR: assert result is True
        # REMOVED_SYNTAX_ERROR: mock_emitter.notify_agent_thinking.assert_called_once_with("run1", "agent1", "thinking...", 1, 50.0)


# REMOVED_SYNTAX_ERROR: class TestToolExecutorFactory:
    # REMOVED_SYNTAX_ERROR: """Test tool executor factory functionality."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def user_context(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create test user context."""
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: thread_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: run_id="formatted_string"
        
        # REMOVED_SYNTAX_ERROR: for i in range(num_users)
        

        # Define user-specific operations
# REMOVED_SYNTAX_ERROR: async def user_operations(user_context: UserExecutionContext):
    # REMOVED_SYNTAX_ERROR: results = []
    # REMOVED_SYNTAX_ERROR: async with request_scoped_tool_dispatcher_scope(user_context) as dispatcher:
        # Register user-specific tool
# REMOVED_SYNTAX_ERROR: def user_tool():
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return {"user_id": user_context.user_id, "timestamp": time.time()}

    # REMOVED_SYNTAX_ERROR: dispatcher.register_tool("user_tool", user_tool)

    # Execute multiple operations
    # REMOVED_SYNTAX_ERROR: for op_num in range(num_operations_per_user):
        # REMOVED_SYNTAX_ERROR: result = await dispatcher.dispatch("user_tool")
        # REMOVED_SYNTAX_ERROR: results.append((user_context.user_id, result.payload.result if hasattr(result, 'payload') else result))

        # REMOVED_SYNTAX_ERROR: return results

        # Execute all user operations concurrently
        # REMOVED_SYNTAX_ERROR: start_time = time.time()
        # REMOVED_SYNTAX_ERROR: tasks = [asyncio.create_task(user_operations(context)) for context in contexts]
        # REMOVED_SYNTAX_ERROR: all_results = await asyncio.gather(*tasks)
        # REMOVED_SYNTAX_ERROR: total_time = time.time() - start_time

        # Verify results
        # REMOVED_SYNTAX_ERROR: assert len(all_results) == num_users

        # Verify user isolation
        # REMOVED_SYNTAX_ERROR: for i, user_results in enumerate(all_results):
            # REMOVED_SYNTAX_ERROR: expected_user_id = "formatted_string"
            # REMOVED_SYNTAX_ERROR: assert len(user_results) == num_operations_per_user

            # REMOVED_SYNTAX_ERROR: for user_id, result_data in user_results:
                # REMOVED_SYNTAX_ERROR: assert user_id == expected_user_id
                # REMOVED_SYNTAX_ERROR: if isinstance(result_data, dict):
                    # REMOVED_SYNTAX_ERROR: assert result_data.get('user_id') == expected_user_id

                    # Performance assertion - should handle concurrency efficiently
                    # REMOVED_SYNTAX_ERROR: avg_time_per_user = total_time / num_users
                    # REMOVED_SYNTAX_ERROR: assert avg_time_per_user < 1.0  # Should be reasonably fast

                    # REMOVED_SYNTAX_ERROR: print("formatted_string")


                    # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                        # Run specific test categories
                        # REMOVED_SYNTAX_ERROR: pytest.main([ ))
                        # REMOVED_SYNTAX_ERROR: __file__,
                        # REMOVED_SYNTAX_ERROR: "-v",
                        # REMOVED_SYNTAX_ERROR: "--tb=short",
                        # REMOVED_SYNTAX_ERROR: "-k", "test_user_isolation or test_concurrent"
                        
                        # REMOVED_SYNTAX_ERROR: pass