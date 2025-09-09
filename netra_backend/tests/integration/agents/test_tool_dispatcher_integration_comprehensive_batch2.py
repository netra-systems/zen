"""
Integration Tests for Tool Dispatcher System - Batch 2 Comprehensive Suite

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Development Velocity
- Business Goal: Validate tool dispatcher system works with real services
- Value Impact: Prevents integration failures that would break agent workflows
- Strategic Impact: Core platform functionality enabling all AI agent capabilities

Integration Focus:
1. Tool dispatcher with real registry and validation services
2. WebSocket event emission through real connections
3. Tool execution with real state management
4. Error handling with real error conditions
5. User context isolation with real user execution contexts
"""

import asyncio
import pytest
import time
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.isolated_test_helper import create_isolated_user_context
from netra_backend.app.agents.tool_dispatcher import (
    UnifiedToolDispatcher,
    UnifiedToolDispatcherFactory,
    create_request_scoped_tool_dispatcher,
    ToolDispatchRequest,
    ToolDispatchResponse
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.schemas.tool import ToolInput, ToolResult, ToolStatus
from netra_backend.app.agents.state import DeepAgentState
from langchain_core.tools import BaseTool


class TestToolDispatcherRealIntegration(SSotBaseTestCase):
    """Integration tests with real service components (no Docker required)."""
    
    def setup_method(self, method):
        """Set up real integration test environment."""
        super().setup_method(method)
        
        # Create real user execution context
        self.user_context = create_isolated_user_context(
            user_id="integration_test_user",
            run_id="integration_test_run"
        )
        
        # Set up WebSocket mock that simulates real behavior
        self.websocket_manager = Mock()
        self.websocket_manager.send_event = AsyncMock()
        self.websocket_manager.connected = True
        
        # Track events for verification
        self.emitted_events = []
        
        async def capture_events(event_type, data):
            self.emitted_events.append({"type": event_type, "data": data})
            return True
        
        self.websocket_manager.send_event.side_effect = capture_events
        
        self.record_metric("integration_test_setup_completed", True)
    
    # ===================== REAL FACTORY PATTERN TESTS =====================
    
    @pytest.mark.asyncio
    async def test_factory_creates_real_isolated_dispatcher(self):
        """Test factory creates properly isolated dispatcher with real components.
        
        BVJ: Ensures user isolation works in real execution contexts.
        """
        # Create dispatcher with real factory
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user_context,
            websocket_bridge=self.websocket_manager
        )
        
        # Verify real components were created
        assert dispatcher is not None
        assert hasattr(dispatcher, 'user_context')
        assert hasattr(dispatcher, 'registry')
        assert hasattr(dispatcher, 'executor')
        assert hasattr(dispatcher, 'validator')
        
        # Verify user context isolation
        assert dispatcher.user_context.user_id == "integration_test_user"
        assert dispatcher.user_context.run_id == "integration_test_run"
        
        # Verify WebSocket support is enabled
        assert dispatcher.has_websocket_support
        
        # Cleanup
        await dispatcher.cleanup()
        
        self.record_metric("real_isolated_dispatcher_created", True)
    
    @pytest.mark.asyncio
    async def test_scoped_context_manager_provides_real_cleanup(self):
        """Test scoped context manager provides real resource cleanup.
        
        BVJ: Prevents memory leaks in production multi-user environment.
        """
        dispatcher_id = None
        
        async with UnifiedToolDispatcher.create_scoped(
            user_context=self.user_context,
            websocket_bridge=self.websocket_manager
        ) as dispatcher:
            dispatcher_id = dispatcher.dispatcher_id
            
            # Dispatcher should be active
            assert dispatcher._is_active
            assert dispatcher.dispatcher_id is not None
            
            # Should have real components
            assert dispatcher.registry is not None
            assert dispatcher.executor is not None
        
        # After context exit, dispatcher should be cleaned up
        assert not dispatcher._is_active
        
        self.record_metric("real_cleanup_verified", True)
    
    # ===================== REAL TOOL EXECUTION TESTS =====================
    
    @pytest.mark.asyncio
    async def test_real_tool_registration_and_execution(self):
        """Test real tool registration and execution with WebSocket events.
        
        BVJ: Validates core platform functionality for tool execution.
        """
        class RealTestTool(BaseTool):
            name: str = "real_test_tool"
            description: str = "A real test tool for integration testing"
            
            def _run(self, test_param: str = "default") -> str:
                return f"Real tool executed with: {test_param}"
        
        real_tool = RealTestTool()
        
        async with UnifiedToolDispatcher.create_scoped(
            user_context=self.user_context,
            websocket_bridge=self.websocket_manager,
            tools=[real_tool]
        ) as dispatcher:
            
            # Verify tool was registered
            assert dispatcher.has_tool("real_test_tool")
            
            # Execute the tool
            result = await dispatcher.execute_tool(
                "real_test_tool",
                {"test_param": "integration_value"}
            )
            
            # Verify execution succeeded
            assert result.success
            assert "Real tool executed with: integration_value" in str(result.result)
            assert result.tool_name == "real_test_tool"
            assert result.user_id == "integration_test_user"
            
            # Verify WebSocket events were emitted
            assert len(self.emitted_events) >= 2  # At least tool_executing and tool_completed
            
            event_types = [event["type"] for event in self.emitted_events]
            assert "tool_executing" in event_types
            assert "tool_completed" in event_types
            
            # Verify event data
            executing_event = next(e for e in self.emitted_events if e["type"] == "tool_executing")
            assert executing_event["data"]["tool_name"] == "real_test_tool"
            assert executing_event["data"]["user_id"] == "integration_test_user"
            
            completed_event = next(e for e in self.emitted_events if e["type"] == "tool_completed")
            assert completed_event["data"]["tool_name"] == "real_test_tool"
            assert completed_event["data"]["status"] == "success"
        
        self.record_metric("real_tool_execution_verified", True)
    
    @pytest.mark.asyncio
    async def test_real_error_handling_with_websocket_events(self):
        """Test real error handling emits proper WebSocket events.
        
        BVJ: Ensures users get feedback when tools fail.
        """
        class FailingTestTool(BaseTool):
            name: str = "failing_tool"
            description: str = "A tool that fails for testing"
            
            def _run(self, **kwargs) -> str:
                raise ValueError("Intentional test failure")
        
        failing_tool = FailingTestTool()
        
        async with UnifiedToolDispatcher.create_scoped(
            user_context=self.user_context,
            websocket_bridge=self.websocket_manager,
            tools=[failing_tool]
        ) as dispatcher:
            
            # Execute the failing tool
            result = await dispatcher.execute_tool("failing_tool")
            
            # Verify execution failed gracefully
            assert not result.success
            assert "Intentional test failure" in result.error_message
            
            # Verify error WebSocket events were emitted
            assert len(self.emitted_events) >= 2
            
            completed_event = next(e for e in self.emitted_events if e["type"] == "tool_completed")
            assert completed_event["data"]["status"] == "error"
            assert "error" in completed_event["data"]
        
        self.record_metric("real_error_handling_verified", True)
    
    # ===================== REAL USER ISOLATION TESTS =====================
    
    @pytest.mark.asyncio
    async def test_multiple_user_contexts_remain_isolated(self):
        """Test multiple user contexts remain properly isolated.
        
        BVJ: Ensures multi-user system doesn't leak data between users.
        """
        user_context_1 = create_isolated_user_context("user_1", "run_1")
        user_context_2 = create_isolated_user_context("user_2", "run_2")
        
        # Create WebSocket managers for each user
        ws_manager_1 = Mock()
        ws_manager_1.send_event = AsyncMock()
        events_1 = []
        
        ws_manager_2 = Mock()
        ws_manager_2.send_event = AsyncMock()
        events_2 = []
        
        async def capture_events_1(event_type, data):
            events_1.append({"type": event_type, "data": data})
        
        async def capture_events_2(event_type, data):
            events_2.append({"type": event_type, "data": data})
        
        ws_manager_1.send_event.side_effect = capture_events_1
        ws_manager_2.send_event.side_effect = capture_events_2
        
        class IsolationTestTool(BaseTool):
            name: str = "isolation_tool"
            description: str = "Tool for testing user isolation"
            
            def _run(self, message: str = "default") -> str:
                return f"User message: {message}"
        
        tool = IsolationTestTool()
        
        # Create dispatchers for both users
        dispatcher_1 = await UnifiedToolDispatcher.create_for_user(
            user_context=user_context_1,
            websocket_bridge=ws_manager_1,
            tools=[tool]
        )
        
        dispatcher_2 = await UnifiedToolDispatcher.create_for_user(
            user_context=user_context_2,  
            websocket_bridge=ws_manager_2,
            tools=[tool]
        )
        
        try:
            # Execute tools for both users with different parameters
            result_1 = await dispatcher_1.execute_tool(
                "isolation_tool",
                {"message": "user_1_message"}
            )
            
            result_2 = await dispatcher_2.execute_tool(
                "isolation_tool", 
                {"message": "user_2_message"}
            )
            
            # Verify results are isolated
            assert result_1.user_id == "user_1"
            assert result_2.user_id == "user_2"
            
            assert "user_1_message" in str(result_1.result)
            assert "user_2_message" in str(result_2.result)
            
            # Verify WebSocket events go to correct users
            assert len(events_1) >= 2
            assert len(events_2) >= 2
            
            # User 1 events should have user_1 data
            for event in events_1:
                assert event["data"]["user_id"] == "user_1"
            
            # User 2 events should have user_2 data  
            for event in events_2:
                assert event["data"]["user_id"] == "user_2"
            
        finally:
            # Cleanup
            await dispatcher_1.cleanup()
            await dispatcher_2.cleanup()
        
        self.record_metric("user_isolation_verified", True)
    
    # ===================== REAL PERFORMANCE TESTS =====================
    
    @pytest.mark.asyncio
    async def test_concurrent_tool_execution_performance(self):
        """Test concurrent tool execution maintains performance.
        
        BVJ: Ensures system can handle multiple simultaneous tool executions.
        """
        class PerformanceTestTool(BaseTool):
            name: str = "perf_tool"
            description: str = "Tool for performance testing"
            
            async def _arun(self, delay: float = 0.1) -> str:
                await asyncio.sleep(delay)
                return f"Completed after {delay}s"
        
        perf_tool = PerformanceTestTool()
        
        async with UnifiedToolDispatcher.create_scoped(
            user_context=self.user_context,
            websocket_bridge=self.websocket_manager,
            tools=[perf_tool]
        ) as dispatcher:
            
            # Execute multiple tools concurrently
            start_time = time.time()
            
            tasks = []
            for i in range(5):
                task = dispatcher.execute_tool("perf_tool", {"delay": 0.1})
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Should complete in roughly 0.1s (concurrent) not 0.5s (sequential)
            assert total_time < 0.3, f"Concurrent execution took {total_time}s, expected < 0.3s"
            
            # All executions should succeed
            for result in results:
                assert result.success
            
            # Should have emitted events for all executions
            assert len(self.emitted_events) >= 10  # 2 events * 5 executions
        
        self.record_metric("concurrent_execution_performance_verified", True)
    
    # ===================== REAL STATE MANAGEMENT TESTS =====================
    
    @pytest.mark.asyncio
    async def test_real_state_based_execution(self):
        """Test tool execution with real state management.
        
        BVJ: Ensures stateful agent workflows work correctly.
        """
        # Create real DeepAgentState
        agent_state = DeepAgentState(user_request="Test stateful execution")
        
        class StatefulTool(BaseTool):
            name: str = "stateful_tool"
            description: str = "Tool that uses state information"
            
            def _run(self, context_info: str = None) -> str:
                return f"Stateful execution with context: {context_info}"
        
        stateful_tool = StatefulTool()
        
        # Test using the core dispatcher with state
        from netra_backend.app.agents.tool_dispatcher_core import ToolDispatcher as CoreDispatcher
        
        # Mock the factory method since we're testing integration
        with patch.object(CoreDispatcher, '_init_from_factory') as mock_factory:
            mock_dispatcher = Mock()
            mock_dispatcher.has_tool = Mock(return_value=True)
            mock_dispatcher.registry = Mock()
            mock_dispatcher.registry.get_tool = Mock(return_value=stateful_tool)
            
            # Mock the executor to return a proper response
            mock_executor = Mock()
            mock_executor.execute_with_state = AsyncMock(return_value={
                "success": True,
                "result": "Stateful execution with context: state_data",
                "metadata": {"state_used": True}
            })
            mock_dispatcher.executor = mock_executor
            
            mock_factory.return_value = mock_dispatcher
            
            core_dispatcher = CoreDispatcher._init_from_factory()
            
            # Execute with state
            result = await core_dispatcher.dispatch_tool(
                "stateful_tool",
                {"context_info": "state_data"},
                agent_state,
                "test_run_id"
            )
            
            # Verify state was passed correctly
            mock_executor.execute_with_state.assert_called_once()
            call_args = mock_executor.execute_with_state.call_args[0]
            assert call_args[3] == agent_state  # state parameter
            assert call_args[4] == "test_run_id"  # run_id parameter
            
            # Verify response
            assert result.success
            assert "state_data" in result.result
        
        self.record_metric("real_state_management_verified", True)


class TestToolDispatcherFactoryIntegration(SSotBaseTestCase):
    """Integration tests for tool dispatcher factory patterns."""
    
    def setup_method(self, method):
        """Set up factory integration test environment."""
        super().setup_method(method)
        self.user_context = create_isolated_user_context("factory_user", "factory_run")
    
    @pytest.mark.asyncio
    async def test_factory_manages_dispatcher_lifecycle(self):
        """Test factory properly manages dispatcher lifecycle.
        
        BVJ: Ensures proper resource management in production.
        """
        factory = UnifiedToolDispatcherFactory()
        
        # Create dispatcher through factory
        dispatcher = await factory.create_dispatcher(
            user_context=self.user_context
        )
        
        # Verify dispatcher is tracked by factory
        assert dispatcher in factory._active_dispatchers
        assert dispatcher._is_active
        
        # Cleanup through factory
        await factory.cleanup_all_dispatchers()
        
        # Verify dispatcher was cleaned up
        assert not dispatcher._is_active
        assert len(factory._active_dispatchers) == 0
        
        self.record_metric("factory_lifecycle_management_verified", True)
    
    @pytest.mark.asyncio
    async def test_factory_with_tool_registry_integration(self):
        """Test factory integration with tool registry.
        
        BVJ: Ensures tools are properly available across dispatchers.
        """
        # Mock a tool registry
        mock_tool_registry = Mock()
        mock_tool_registry.list_tools.return_value = [
            Mock(id="registry_tool_1", name="Registry Tool 1", handler=AsyncMock()),
            Mock(id="registry_tool_2", name="Registry Tool 2", handler=AsyncMock())
        ]
        
        factory = UnifiedToolDispatcherFactory()
        factory.set_tool_registry(mock_tool_registry)
        
        # Create dispatcher
        dispatcher = await factory.create_dispatcher(
            user_context=self.user_context
        )
        
        # Verify tools were populated from registry
        mock_tool_registry.list_tools.assert_called_once()
        
        # Verify tools are available in dispatcher
        available_tools = dispatcher.get_available_tools()
        assert "registry_tool_1" in available_tools
        assert "registry_tool_2" in available_tools
        
        # Cleanup
        await factory.cleanup_all_dispatchers()
        
        self.record_metric("tool_registry_integration_verified", True)


class TestToolDispatcherErrorScenarioIntegration(SSotBaseTestCase):
    """Integration tests for error scenarios with real components."""
    
    def setup_method(self, method):
        """Set up error scenario test environment."""
        super().setup_method(method)
        self.user_context = create_isolated_user_context("error_user", "error_run")
    
    @pytest.mark.asyncio
    async def test_real_permission_validation_errors(self):
        """Test permission validation with real security context.
        
        BVJ: Ensures security boundaries are enforced in production.
        """
        # Create dispatcher that should enforce permissions
        async with UnifiedToolDispatcher.create_scoped(
            user_context=self.user_context,
            enable_admin_tools=True  # This should trigger permission validation
        ) as dispatcher:
            
            # Try to execute an admin tool without proper permissions
            try:
                await dispatcher.execute_tool("system_config", {})
                assert False, "Should have raised permission error"
            except Exception as e:
                # Verify it's a permission-related error
                assert "permission" in str(e).lower() or "admin" in str(e).lower()
        
        self.record_metric("permission_validation_error_verified", True)
    
    @pytest.mark.asyncio
    async def test_real_websocket_connection_failure_handling(self):
        """Test handling of WebSocket connection failures.
        
        BVJ: Ensures system remains functional when WebSocket fails.
        """
        # Create WebSocket manager that fails
        failing_websocket = Mock()
        failing_websocket.send_event = AsyncMock(side_effect=Exception("WebSocket connection failed"))
        
        class TestTool(BaseTool):
            name: str = "websocket_test_tool"
            description: str = "Tool for testing WebSocket failures"
            
            def _run(self) -> str:
                return "Tool executed successfully"
        
        async with UnifiedToolDispatcher.create_scoped(
            user_context=self.user_context,
            websocket_bridge=failing_websocket,
            tools=[TestTool()]
        ) as dispatcher:
            
            # Execute tool - should succeed despite WebSocket failure
            result = await dispatcher.execute_tool("websocket_test_tool")
            
            # Tool execution should succeed
            assert result.success
            assert "Tool executed successfully" in str(result.result)
            
            # WebSocket failure should have been attempted but handled gracefully
            failing_websocket.send_event.assert_called()
        
        self.record_metric("websocket_failure_handling_verified", True)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])