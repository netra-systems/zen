"""Tests for RequestScopedToolDispatcher and ToolExecutorFactory.

This test suite validates that the request-scoped tool execution system provides
complete user isolation and eliminates global state issues.

Test Categories:
- User isolation validation
- WebSocket event routing
- Concurrent user handling
- Resource cleanup
- Performance monitoring
- Error handling and recovery
"""

import asyncio
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import Mock, AsyncMock, patch

from netra_backend.app.agents.request_scoped_tool_dispatcher import (
    RequestScopedToolDispatcher,
    WebSocketBridgeAdapter,
    create_request_scoped_tool_dispatcher,
    request_scoped_tool_dispatcher_scope
)
from netra_backend.app.agents.tool_executor_factory import (
    ToolExecutorFactory,
    get_tool_executor_factory,
    create_isolated_tool_executor,
    create_isolated_tool_dispatcher,
    isolated_tool_dispatcher_scope
)
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core import WebSocketEventEmitter
from netra_backend.app.agents.tool_dispatcher_core import ToolDispatcher
from netra_backend.app.schemas.tool import ToolInput, ToolResult, ToolStatus


class TestRequestScopedToolDispatcher:
    """Test request-scoped tool dispatcher functionality."""
    
    @pytest.fixture
    def user_context(self):
        """Create test user context."""
        return UserExecutionContext(
            user_id=f"test_user_{uuid.uuid4().hex[:8]}",
            thread_id=f"test_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"test_run_{uuid.uuid4().hex[:8]}"
        )
    
    @pytest.fixture
    def mock_websocket_emitter(self):
        """Create mock WebSocket emitter."""
        emitter = Mock(spec=WebSocketEventEmitter)
        emitter.notify_tool_executing = AsyncMock(return_value=True)
        emitter.notify_tool_completed = AsyncMock(return_value=True)
        emitter.dispose = AsyncMock()
        emitter.get_context = Mock()
        return emitter
    
    @pytest.fixture
    def simple_tool(self):
        """Create a simple test tool."""
        def simple_tool_func(*args, **kwargs):
            return {"result": "test_success", "args": args, "kwargs": kwargs}
        
        simple_tool_func.name = "simple_tool"
        simple_tool_func.description = "A simple test tool"
        return simple_tool_func
    
    async def test_dispatcher_creation_with_user_context(self, user_context, mock_websocket_emitter):
        """Test that dispatcher is created with proper user context isolation."""
        dispatcher = RequestScopedToolDispatcher(
            user_context=user_context,
            websocket_emitter=mock_websocket_emitter
        )
        
        # Verify context binding
        assert dispatcher.user_context == user_context
        assert dispatcher.user_context.user_id == user_context.user_id
        assert dispatcher.user_context.run_id == user_context.run_id
        
        # Verify isolation metrics
        metrics = dispatcher.get_metrics()
        assert metrics['user_id'] == user_context.user_id
        assert metrics['run_id'] == user_context.run_id
        assert metrics['dispatcher_id'].startswith(user_context.user_id)
        
        # Verify WebSocket integration
        assert dispatcher.websocket_emitter == mock_websocket_emitter
        assert dispatcher.has_websocket_support
        
        await dispatcher.cleanup()
    
    async def test_user_isolation_between_dispatchers(self, mock_websocket_emitter):
        """Test that multiple dispatchers maintain complete user isolation."""
        # Create contexts for two different users
        user1_context = UserExecutionContext(
            user_id="user1",
            thread_id="thread1", 
            run_id="run1"
        )
        user2_context = UserExecutionContext(
            user_id="user2",
            thread_id="thread2",
            run_id="run2"
        )
        
        # Create dispatchers for each user
        dispatcher1 = RequestScopedToolDispatcher(user1_context, websocket_emitter=mock_websocket_emitter)
        dispatcher2 = RequestScopedToolDispatcher(user2_context, websocket_emitter=mock_websocket_emitter)
        
        # Verify complete isolation
        assert dispatcher1.user_context != dispatcher2.user_context
        assert dispatcher1.dispatcher_id != dispatcher2.dispatcher_id
        assert dispatcher1.registry is not dispatcher2.registry  # Separate tool registries
        assert dispatcher1.executor is not dispatcher2.executor  # Separate executors
        
        # Verify metrics isolation
        metrics1 = dispatcher1.get_metrics()
        metrics2 = dispatcher2.get_metrics()
        assert metrics1['user_id'] != metrics2['user_id']
        assert metrics1['dispatcher_id'] != metrics2['dispatcher_id']
        
        await dispatcher1.cleanup()
        await dispatcher2.cleanup()
    
    async def test_tool_registration_isolation(self, user_context, mock_websocket_emitter):
        """Test that tool registrations are isolated per dispatcher."""
        dispatcher1 = RequestScopedToolDispatcher(user_context, websocket_emitter=mock_websocket_emitter)
        
        # Create second user context
        user2_context = UserExecutionContext(
            user_id="user2",
            thread_id="thread2", 
            run_id="run2"
        )
        dispatcher2 = RequestScopedToolDispatcher(user2_context, websocket_emitter=mock_websocket_emitter)
        
        # Register tool only in first dispatcher
        def user1_tool():
            return "user1_result"
        
        dispatcher1.register_tool("user1_tool", user1_tool)
        
        # Verify tool isolation
        assert dispatcher1.has_tool("user1_tool")
        assert not dispatcher2.has_tool("user1_tool")
        
        # Register different tool in second dispatcher
        def user2_tool():
            return "user2_result"
        
        dispatcher2.register_tool("user2_tool", user2_tool)
        
        # Verify continued isolation
        assert dispatcher1.has_tool("user1_tool")
        assert not dispatcher1.has_tool("user2_tool")
        assert dispatcher2.has_tool("user2_tool")
        assert not dispatcher2.has_tool("user1_tool")
        
        await dispatcher1.cleanup()
        await dispatcher2.cleanup()
    
    async def test_websocket_event_isolation(self, mock_websocket_emitter):
        """Test that WebSocket events are properly isolated per user."""
        # Create contexts for two users
        user1_context = UserExecutionContext(user_id="user1", thread_id="thread1", run_id="run1")
        user2_context = UserExecutionContext(user_id="user2", thread_id="thread2", run_id="run2")
        
        # Create separate mock emitters to track calls
        emitter1 = Mock(spec=WebSocketEventEmitter)
        emitter1.notify_tool_executing = AsyncMock(return_value=True)
        emitter1.notify_tool_completed = AsyncMock(return_value=True)
        emitter1.dispose = AsyncMock()
        
        emitter2 = Mock(spec=WebSocketEventEmitter)
        emitter2.notify_tool_executing = AsyncMock(return_value=True)
        emitter2.notify_tool_completed = AsyncMock(return_value=True)
        emitter2.dispose = AsyncMock()
        
        # Create dispatchers with separate emitters
        dispatcher1 = RequestScopedToolDispatcher(user1_context, websocket_emitter=emitter1)
        dispatcher2 = RequestScopedToolDispatcher(user2_context, websocket_emitter=emitter2)
        
        # Register same tool in both dispatchers
        def test_tool():
            return "tool_result"
        
        dispatcher1.register_tool("test_tool", test_tool)
        dispatcher2.register_tool("test_tool", test_tool)
        
        # Execute tools in both dispatchers
        result1 = await dispatcher1.dispatch("test_tool")
        result2 = await dispatcher2.dispatch("test_tool")
        
        # Verify both executions succeeded
        assert result1.status == ToolStatus.SUCCESS
        assert result2.status == ToolStatus.SUCCESS
        
        # Verify WebSocket events were sent to correct emitters only
        emitter1.notify_tool_executing.assert_called()
        emitter1.notify_tool_completed.assert_called()
        emitter2.notify_tool_executing.assert_called() 
        emitter2.notify_tool_completed.assert_called()
        
        # Verify no cross-contamination
        assert emitter1 != emitter2
        
        await dispatcher1.cleanup()
        await dispatcher2.cleanup()
    
    async def test_concurrent_tool_execution(self, mock_websocket_emitter):
        """Test concurrent tool execution across multiple users."""
        # Create multiple user contexts
        contexts = [
            UserExecutionContext(
                user_id=f"user_{i}",
                thread_id=f"thread_{i}",
                run_id=f"run_{i}"
            )
            for i in range(5)
        ]
        
        # Create dispatchers for each context
        dispatchers = [
            RequestScopedToolDispatcher(context, websocket_emitter=mock_websocket_emitter)
            for context in contexts
        ]
        
        # Define a slow tool to test concurrency
        async def slow_tool(delay: float = 0.1):
            await asyncio.sleep(delay)
            return {"user_id": "from_tool", "timestamp": time.time()}
        
        # Register tool in all dispatchers
        for i, dispatcher in enumerate(dispatchers):
            dispatcher.register_tool("slow_tool", slow_tool)
        
        # Execute tools concurrently
        start_time = time.time()
        tasks = []
        for dispatcher in dispatchers:
            task = asyncio.create_task(dispatcher.dispatch("slow_tool", delay=0.2))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Verify all executions succeeded
        assert len(results) == 5
        for result in results:
            assert result.status == ToolStatus.SUCCESS
        
        # Verify concurrent execution (should be faster than sequential)
        assert total_time < 0.8  # Should be much faster than 5 * 0.2 = 1.0 seconds
        
        # Verify metrics are properly tracked per dispatcher
        for dispatcher in dispatchers:
            metrics = dispatcher.get_metrics()
            assert metrics['tools_executed'] == 1
            assert metrics['successful_executions'] == 1
            assert metrics['failed_executions'] == 0
        
        # Cleanup all dispatchers
        await asyncio.gather(*[dispatcher.cleanup() for dispatcher in dispatchers])
    
    async def test_run_id_validation_security(self, user_context, mock_websocket_emitter):
        """Test that run_id validation prevents cross-user access."""
        dispatcher = RequestScopedToolDispatcher(user_context, websocket_emitter=mock_websocket_emitter)
        
        def test_tool():
            return "secure_result"
        
        dispatcher.register_tool("test_tool", test_tool)
        
        # Valid run_id should work
        state = Mock()
        result = await dispatcher.dispatch_tool("test_tool", {}, state, user_context.run_id)
        assert result["success"] is True
        
        # Invalid run_id should fail
        invalid_result = await dispatcher.dispatch_tool("test_tool", {}, state, "wrong_run_id")
        assert invalid_result["success"] is False
        assert "not found" in invalid_result["error"]
        
        await dispatcher.cleanup()
    
    async def test_resource_cleanup(self, user_context, mock_websocket_emitter):
        """Test proper resource cleanup when dispatcher is disposed."""
        dispatcher = RequestScopedToolDispatcher(user_context, websocket_emitter=mock_websocket_emitter)
        
        # Register some tools to create state
        dispatcher.register_tool("tool1", lambda: "result1")
        dispatcher.register_tool("tool2", lambda: "result2")
        
        # Verify initial state
        assert dispatcher.is_active()
        assert len(dispatcher.tools) == 2
        metrics = dispatcher.get_metrics()
        assert len(metrics) > 0
        
        # Cleanup dispatcher
        await dispatcher.cleanup()
        
        # Verify cleanup
        assert not dispatcher.is_active()
        assert len(dispatcher.tools) == 0  # Tools registry cleared
        
        # Verify WebSocket emitter was disposed
        mock_websocket_emitter.dispose.assert_called_once()
        
        # Verify disposed dispatcher cannot be used
        with pytest.raises(RuntimeError, match="has been disposed"):
            dispatcher.has_tool("tool1")
        
        with pytest.raises(RuntimeError, match="has been disposed"):
            await dispatcher.dispatch("tool1")
    
    async def test_context_manager_usage(self, user_context):
        """Test using dispatcher as async context manager."""
        tool_executed = False
        
        def test_tool():
            nonlocal tool_executed
            tool_executed = True
            return "context_result"
        
        # Test context manager with automatic cleanup
        async with request_scoped_tool_dispatcher_scope(user_context) as dispatcher:
            dispatcher.register_tool("test_tool", test_tool)
            result = await dispatcher.dispatch("test_tool")
            assert result.status == ToolStatus.SUCCESS
            assert tool_executed
            assert dispatcher.is_active()
        
        # Verify cleanup happened automatically
        assert not dispatcher.is_active()
    
    async def test_metrics_tracking(self, user_context, mock_websocket_emitter):
        """Test comprehensive metrics tracking."""
        dispatcher = RequestScopedToolDispatcher(user_context, websocket_emitter=mock_websocket_emitter)
        
        # Register tools
        def success_tool():
            return "success"
        
        def failure_tool():
            raise ValueError("Tool failure")
        
        dispatcher.register_tool("success_tool", success_tool)
        dispatcher.register_tool("failure_tool", failure_tool)
        
        # Execute tools
        await dispatcher.dispatch("success_tool")
        await dispatcher.dispatch("success_tool")  # Execute twice
        await dispatcher.dispatch("failure_tool")  # This should fail
        
        # Check metrics
        metrics = dispatcher.get_metrics()
        assert metrics['tools_executed'] == 3
        assert metrics['successful_executions'] == 2
        assert metrics['failed_executions'] == 1
        assert metrics['success_rate'] == 2/3
        assert metrics['total_execution_time_ms'] > 0
        assert metrics['last_execution_time'] is not None
        
        await dispatcher.cleanup()


class TestWebSocketBridgeAdapter:
    """Test WebSocket bridge adapter functionality."""
    
    @pytest.fixture
    def user_context(self):
        """Create test user context."""
        return UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread", 
            run_id="test_run"
        )
    
    @pytest.fixture
    def mock_emitter(self):
        """Create mock WebSocket emitter."""
        emitter = Mock(spec=WebSocketEventEmitter)
        emitter.notify_tool_executing = AsyncMock(return_value=True)
        emitter.notify_tool_completed = AsyncMock(return_value=True)
        emitter.notify_agent_started = AsyncMock(return_value=True)
        emitter.notify_agent_thinking = AsyncMock(return_value=True)
        emitter.notify_agent_completed = AsyncMock(return_value=True)
        emitter.notify_agent_error = AsyncMock(return_value=True)
        return emitter
    
    async def test_adapter_method_delegation(self, user_context, mock_emitter):
        """Test that adapter properly delegates to WebSocketEventEmitter."""
        adapter = WebSocketBridgeAdapter(mock_emitter, user_context)
        
        # Test tool notifications
        result = await adapter.notify_tool_executing("run1", "agent1", "tool1", {"param": "value"})
        assert result is True
        mock_emitter.notify_tool_executing.assert_called_once_with("run1", "agent1", "tool1", {"param": "value"})
        
        result = await adapter.notify_tool_completed("run1", "agent1", "tool1", {"result": "success"}, 100.0)
        assert result is True
        mock_emitter.notify_tool_completed.assert_called_once_with("run1", "agent1", "tool1", {"result": "success"}, 100.0)
        
        # Test agent notifications
        result = await adapter.notify_agent_started("run1", "agent1", {"context": "data"})
        assert result is True
        mock_emitter.notify_agent_started.assert_called_once_with("run1", "agent1", {"context": "data"})
        
        result = await adapter.notify_agent_thinking("run1", "agent1", "thinking...", 1, 50.0)
        assert result is True
        mock_emitter.notify_agent_thinking.assert_called_once_with("run1", "agent1", "thinking...", 1, 50.0)


class TestToolExecutorFactory:
    """Test tool executor factory functionality."""
    
    @pytest.fixture
    def user_context(self):
        """Create test user context."""
        return UserExecutionContext(
            user_id=f"factory_user_{uuid.uuid4().hex[:8]}",
            thread_id=f"factory_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"factory_run_{uuid.uuid4().hex[:8]}"
        )
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Create mock WebSocket manager."""
        manager = Mock()
        manager.send_to_thread = AsyncMock(return_value=True)
        return manager
    
    async def test_factory_creation(self, mock_websocket_manager):
        """Test factory creation and configuration."""
        factory = ToolExecutorFactory(websocket_manager=mock_websocket_manager)
        
        assert factory.websocket_manager == mock_websocket_manager
        assert factory.factory_id.startswith("factory_")
        
        # Test metrics
        metrics = factory.get_factory_metrics()
        assert metrics['executors_created'] == 0
        assert metrics['dispatchers_created'] == 0
        assert metrics['has_websocket_manager'] is True
    
    async def test_tool_executor_creation(self, user_context, mock_websocket_manager):
        """Test tool executor creation with proper isolation."""
        factory = ToolExecutorFactory(websocket_manager=mock_websocket_manager)
        
        # Create executor
        executor = await factory.create_tool_executor(user_context, mock_websocket_manager)
        
        # Verify executor creation
        assert executor is not None
        assert hasattr(executor, 'websocket_bridge')
        
        # Verify metrics updated
        metrics = factory.get_factory_metrics()
        assert metrics['executors_created'] == 1
        assert metrics['active_instances'] == 1
    
    async def test_request_scoped_dispatcher_creation(self, user_context, mock_websocket_manager):
        """Test request-scoped dispatcher creation."""
        factory = ToolExecutorFactory(websocket_manager=mock_websocket_manager)
        
        # Create dispatcher
        dispatcher = await factory.create_request_scoped_dispatcher(user_context, websocket_manager=mock_websocket_manager)
        
        # Verify dispatcher creation
        assert isinstance(dispatcher, RequestScopedToolDispatcher)
        assert dispatcher.user_context == user_context
        assert dispatcher.has_websocket_support
        
        # Verify metrics updated
        metrics = factory.get_factory_metrics()
        assert metrics['dispatchers_created'] == 1
        assert metrics['active_instances'] == 1
        
        await dispatcher.cleanup()
    
    async def test_scoped_creation_patterns(self, user_context, mock_websocket_manager):
        """Test scoped creation with automatic cleanup."""
        factory = ToolExecutorFactory(websocket_manager=mock_websocket_manager)
        
        # Test scoped executor creation
        async with factory.create_scoped_tool_executor(user_context, mock_websocket_manager) as executor:
            assert executor is not None
            metrics = factory.get_factory_metrics()
            assert metrics['active_instances'] == 1
        
        # Verify cleanup
        metrics = factory.get_factory_metrics()
        assert metrics['active_instances'] == 0
        
        # Test scoped dispatcher creation
        async with factory.create_scoped_dispatcher(user_context, websocket_manager=mock_websocket_manager) as dispatcher:
            assert isinstance(dispatcher, RequestScopedToolDispatcher)
            assert dispatcher.is_active()
            metrics = factory.get_factory_metrics()
            assert metrics['active_instances'] == 1
        
        # Verify cleanup
        assert not dispatcher.is_active()
        metrics = factory.get_factory_metrics()
        assert metrics['active_instances'] == 0
    
    async def test_factory_health_validation(self, user_context, mock_websocket_manager):
        """Test factory health validation."""
        factory = ToolExecutorFactory(websocket_manager=mock_websocket_manager)
        
        health_status = await factory.validate_factory_health()
        
        assert health_status['status'] in ['healthy', 'degraded', 'unhealthy']
        assert 'timestamp' in health_status
        assert 'factory_metrics' in health_status
        assert isinstance(health_status['issues'], list)
    
    async def test_global_factory_instance(self):
        """Test global factory instance management."""
        # Get global factory
        factory1 = get_tool_executor_factory()
        factory2 = get_tool_executor_factory()
        
        # Should be same instance
        assert factory1 is factory2
        assert factory1.factory_id == factory2.factory_id


class TestToolDispatcherCompatibility:
    """Test backward compatibility with existing ToolDispatcher."""
    
    @pytest.fixture
    def user_context(self):
        """Create test user context."""
        return UserExecutionContext(
            user_id="compat_user",
            thread_id="compat_thread",
            run_id="compat_run"
        )
    
    async def test_static_factory_methods(self, user_context):
        """Test static factory methods on ToolDispatcher."""
        # Test request-scoped dispatcher creation
        dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(user_context)
        
        assert isinstance(dispatcher, RequestScopedToolDispatcher)
        assert dispatcher.user_context == user_context
        
        await dispatcher.cleanup()
    
    async def test_scoped_context_creation(self, user_context):
        """Test scoped context manager creation."""
        async with ToolDispatcher.create_scoped_dispatcher_context(user_context) as dispatcher:
            assert isinstance(dispatcher, RequestScopedToolDispatcher)
            assert dispatcher.is_active()
        
        # Verify automatic cleanup
        assert not dispatcher.is_active()
    
    async def test_isolation_status_reporting(self):
        """Test isolation status reporting on legacy dispatcher."""
        # Create legacy dispatcher
        legacy_dispatcher = ToolDispatcher()
        
        # Check isolation status
        status = legacy_dispatcher.get_isolation_status()
        
        assert 'is_global_instance' in status
        assert 'warning_needed' in status
        assert status['recommended_migration'] == 'RequestScopedToolDispatcher'
    
    async def test_deprecation_warnings(self):
        """Test that deprecation warnings are emitted for global state usage."""
        legacy_dispatcher = ToolDispatcher()
        
        # Test that warnings are emitted
        with pytest.warns(UserWarning, match="uses global state"):
            await legacy_dispatcher.dispatch_with_isolation_warning("nonexistent_tool")


class TestConcurrentUserScenarios:
    """Test realistic concurrent user scenarios."""
    
    async def test_high_concurrency_user_isolation(self):
        """Test high concurrency scenarios with user isolation."""
        num_users = 20
        num_operations_per_user = 5
        
        # Create contexts for multiple users
        contexts = [
            UserExecutionContext(
                user_id=f"concurrent_user_{i}",
                thread_id=f"concurrent_thread_{i}",
                run_id=f"concurrent_run_{i}"
            )
            for i in range(num_users)
        ]
        
        # Define user-specific operations
        async def user_operations(user_context: UserExecutionContext):
            results = []
            async with request_scoped_tool_dispatcher_scope(user_context) as dispatcher:
                # Register user-specific tool
                def user_tool():
                    return {"user_id": user_context.user_id, "timestamp": time.time()}
                
                dispatcher.register_tool("user_tool", user_tool)
                
                # Execute multiple operations
                for op_num in range(num_operations_per_user):
                    result = await dispatcher.dispatch("user_tool")
                    results.append((user_context.user_id, result.payload.result if hasattr(result, 'payload') else result))
            
            return results
        
        # Execute all user operations concurrently
        start_time = time.time()
        tasks = [asyncio.create_task(user_operations(context)) for context in contexts]
        all_results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Verify results
        assert len(all_results) == num_users
        
        # Verify user isolation
        for i, user_results in enumerate(all_results):
            expected_user_id = f"concurrent_user_{i}"
            assert len(user_results) == num_operations_per_user
            
            for user_id, result_data in user_results:
                assert user_id == expected_user_id
                if isinstance(result_data, dict):
                    assert result_data.get('user_id') == expected_user_id
        
        # Performance assertion - should handle concurrency efficiently
        avg_time_per_user = total_time / num_users
        assert avg_time_per_user < 1.0  # Should be reasonably fast
        
        print(f"✅ Handled {num_users} concurrent users with {num_operations_per_user} ops each in {total_time:.2f}s")


if __name__ == "__main__":
    # Run specific test categories
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-k", "test_user_isolation or test_concurrent"
    ])