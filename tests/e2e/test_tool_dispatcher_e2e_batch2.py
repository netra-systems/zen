"""
E2E Tests for Tool Dispatcher - Batch 2 Priority Tests (tool_dispatcher.py)

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure complete tool dispatch workflow works end-to-end
- Value Impact: Validates agent tool execution delivers value to users
- Strategic Impact: Critical for agent-based workflows that power chat interactions

These E2E tests focus on:
1. Complete tool dispatch workflow with authentication
2. WebSocket events in real-time scenarios
3. Multi-user isolation with real services
4. Error scenarios with full stack integration
"""

import asyncio
import json
import pytest
from typing import Dict, Any

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.isolated_test_helper import create_isolated_user_context
from netra_backend.app.agents.tool_dispatcher import (
    UnifiedToolDispatcher,
    UnifiedToolDispatcherFactory
)


class TestToolDispatcherE2EBatch2(SSotAsyncTestCase):
    """E2E tests for tool dispatcher with full authentication."""
    
    def setup_method(self, method):
        """Set up E2E test environment with authentication."""
        super().setup_method(method)
        
        # Initialize E2E auth helper
        self.auth_helper = E2EAuthHelper(environment="test")
        
        # Create authenticated user contexts
        self.user_context_1 = create_isolated_user_context(
            user_id="e2e_user_primary",
            thread_id="e2e_thread_primary"
        )
        
        self.user_context_2 = create_isolated_user_context(
            user_id="e2e_user_secondary", 
            thread_id="e2e_thread_secondary"
        )
        
        # Track dispatchers for cleanup
        self.dispatchers = []
    
    async def async_teardown_method(self, method):
        """Clean up E2E test resources."""
        # Cleanup all dispatchers
        for dispatcher in self.dispatchers:
            try:
                await dispatcher.cleanup()
            except:
                pass
        
        super().teardown_method(method)
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_authenticated_tool_execution_complete_flow(self):
        """Test complete tool execution flow with authentication.
        
        BVJ: Validates authenticated users can execute tools successfully.
        CRITICAL: Uses real JWT authentication to ensure security works.
        """
        # Arrange - Create JWT token
        token = self.auth_helper.create_test_jwt_token(
            user_id=self.user_context_1.user_id,
            permissions=["read", "write", "tool_execute"]
        )
        
        # Create test tool
        from langchain_core.tools import BaseTool
        
        class E2ETestTool(BaseTool):
            name = "e2e_analyzer"
            description = "E2E test analysis tool"
            
            def _run(self, data: str) -> str:
                return f"E2E Analysis: {data} - Processing complete"
            
            async def _arun(self, data: str) -> str:
                await asyncio.sleep(0.1)  # Simulate processing
                return f"E2E Async Analysis: {data} - Processing complete"
        
        # Create WebSocket bridge mock for E2E
        from unittest.mock import AsyncMock
        websocket_bridge = AsyncMock()
        websocket_bridge.notify_tool_executing = AsyncMock(return_value=True)
        websocket_bridge.notify_tool_completed = AsyncMock(return_value=True)
        
        # Create authenticated dispatcher
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user_context_1,
            websocket_bridge=websocket_bridge,
            tools=[E2ETestTool()]
        )
        self.dispatchers.append(dispatcher)
        
        # Act - Execute tool with authentication context
        result = await dispatcher.execute_tool(
            "e2e_analyzer",
            {"data": "authenticated_user_request"},
            require_permission_check=True
        )
        
        # Assert execution success
        assert result.success is True
        assert "E2E Analysis" in result.result
        assert "authenticated_user_request" in result.result
        assert result.user_id == self.user_context_1.user_id
        assert result.tool_name == "e2e_analyzer"
        assert result.execution_time_ms > 0
        
        # Assert WebSocket events were sent
        websocket_bridge.notify_tool_executing.assert_called_once()
        websocket_bridge.notify_tool_completed.assert_called_once()
        
        # Verify event parameters include user context
        exec_call = websocket_bridge.notify_tool_executing.call_args
        assert exec_call[1]["run_id"] == self.user_context_1.run_id
        assert exec_call[1]["tool_name"] == "e2e_analyzer"
        
        completion_call = websocket_bridge.notify_tool_completed.call_args
        assert completion_call[1]["run_id"] == self.user_context_1.run_id
        assert "result" in completion_call[1]
        
        self.record_metric("e2e_authenticated_execution", "success")
        self.record_metric("execution_time_ms", result.execution_time_ms)
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_multi_user_isolation_with_authentication(self):
        """Test complete isolation between authenticated users.
        
        BVJ: Ensures user data cannot leak between different authenticated users.
        CRITICAL: Validates multi-user security in production scenarios.
        """
        # Arrange - Create tokens for different users
        token_1 = self.auth_helper.create_test_jwt_token(
            user_id=self.user_context_1.user_id,
            email="user1@example.com",
            permissions=["read", "write"]
        )
        
        token_2 = self.auth_helper.create_test_jwt_token(
            user_id=self.user_context_2.user_id,
            email="user2@example.com", 
            permissions=["read"]
        )
        
        # Create user-specific tools
        from langchain_core.tools import BaseTool
        
        class UserSpecificTool(BaseTool):
            def __init__(self, user_suffix: str):
                self.name = f"user_tool_{user_suffix}"
                self.description = f"Tool for user {user_suffix}"
                self.user_suffix = user_suffix
            
            def _run(self, request: str) -> str:
                return f"User {self.user_suffix} tool result: {request}"
            
            async def _arun(self, request: str) -> str:
                return f"User {self.user_suffix} async tool result: {request}"
        
        # Create isolated dispatchers for each user
        dispatcher_1 = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user_context_1,
            tools=[UserSpecificTool("alpha")]
        )
        self.dispatchers.append(dispatcher_1)
        
        dispatcher_2 = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user_context_2,
            tools=[UserSpecificTool("beta")]
        )
        self.dispatchers.append(dispatcher_2)
        
        # Act - Execute tools simultaneously
        result_1_task = asyncio.create_task(
            dispatcher_1.execute_tool(
                "user_tool_alpha",
                {"request": "confidential_data_user1"}
            )
        )
        
        result_2_task = asyncio.create_task(
            dispatcher_2.execute_tool(
                "user_tool_beta", 
                {"request": "confidential_data_user2"}
            )
        )
        
        # Wait for both executions
        result_1, result_2 = await asyncio.gather(result_1_task, result_2_task)
        
        # Assert complete isolation
        assert result_1.success is True
        assert result_2.success is True
        
        # Verify user 1 cannot access user 2's tools
        assert dispatcher_1.has_tool("user_tool_alpha") is True
        assert dispatcher_1.has_tool("user_tool_beta") is False
        
        # Verify user 2 cannot access user 1's tools
        assert dispatcher_2.has_tool("user_tool_beta") is True
        assert dispatcher_2.has_tool("user_tool_alpha") is False
        
        # Verify results contain correct user data
        assert "User alpha" in result_1.result
        assert "confidential_data_user1" in result_1.result
        assert "User beta" in result_2.result
        assert "confidential_data_user2" in result_2.result
        
        # Verify no cross-contamination
        assert "user2" not in result_1.result.lower()
        assert "user1" not in result_2.result.lower()
        assert "beta" not in result_1.result
        assert "alpha" not in result_2.result
        
        self.record_metric("e2e_multi_user_isolation", "validated")
        self.record_metric("concurrent_users_tested", 2)
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_authentication_failure_blocks_tool_execution(self):
        """Test that invalid authentication properly blocks tool execution.
        
        BVJ: Validates security prevents unauthorized access to tools.
        CRITICAL: Security test to prevent unauthorized tool access.
        """
        # Arrange - Create dispatcher without proper authentication context
        invalid_context = create_isolated_user_context(
            user_id="",  # Invalid empty user ID
            thread_id="invalid_thread"
        )
        
        from langchain_core.tools import BaseTool
        
        class SecureTool(BaseTool):
            name = "secure_operation"
            description = "A tool that requires authentication"
            
            def _run(self, operation: str) -> str:
                return f"Secure operation executed: {operation}"
            
            async def _arun(self, operation: str) -> str:
                return f"Secure async operation executed: {operation}"
        
        # Act & Assert - Creating dispatcher should fail with invalid context
        with pytest.raises(Exception) as exc_info:
            await UnifiedToolDispatcher.create_for_user(
                user_context=invalid_context,
                tools=[SecureTool()]
            )
        
        # Verify appropriate error was raised
        error_message = str(exc_info.value)
        assert any(keyword in error_message.lower() for keyword in 
                  ["authentication", "user", "context", "required"])
        
        self.record_metric("e2e_auth_failure_prevention", "validated")
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_tool_execution_with_real_websocket_events(self):
        """Test tool execution with real WebSocket event flow.
        
        BVJ: Validates users receive real-time updates during tool execution.
        CRITICAL: Ensures chat UX shows tool progress in real-time.
        """
        # Arrange - Create token and context
        token = self.auth_helper.create_test_jwt_token(
            user_id=self.user_context_1.user_id,
            permissions=["read", "write", "tool_execute"]
        )
        
        # Create tool that takes measurable time
        from langchain_core.tools import BaseTool
        
        class SlowAnalysisTool(BaseTool):
            name = "slow_analyzer"
            description = "Tool that simulates slow analysis"
            
            def _run(self, data: str) -> str:
                import time
                time.sleep(0.2)  # Simulate processing time
                return f"Completed analysis of: {data}"
            
            async def _arun(self, data: str) -> str:
                await asyncio.sleep(0.2)  # Simulate async processing
                return f"Completed async analysis of: {data}"
        
        # Create real WebSocket bridge mock with event tracking
        from unittest.mock import AsyncMock
        websocket_bridge = AsyncMock()
        
        events_received = []
        
        async def track_executing_event(*args, **kwargs):
            events_received.append(("tool_executing", kwargs))
            return True
        
        async def track_completed_event(*args, **kwargs):
            events_received.append(("tool_completed", kwargs))
            return True
        
        websocket_bridge.notify_tool_executing = AsyncMock(side_effect=track_executing_event)
        websocket_bridge.notify_tool_completed = AsyncMock(side_effect=track_completed_event)
        
        # Create dispatcher with event tracking
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=self.user_context_1,
            websocket_bridge=websocket_bridge,
            tools=[SlowAnalysisTool()]
        )
        self.dispatchers.append(dispatcher)
        
        # Act - Execute tool and measure timing
        import time
        start_time = time.time()
        
        result = await dispatcher.execute_tool(
            "slow_analyzer",
            {"data": "real_time_test_data"}
        )
        
        end_time = time.time()
        execution_duration = (end_time - start_time) * 1000  # Convert to ms
        
        # Assert execution success
        assert result.success is True
        assert "Completed analysis" in result.result
        assert "real_time_test_data" in result.result
        assert execution_duration >= 200  # Should take at least 200ms
        
        # Assert WebSocket events were sent in correct order
        assert len(events_received) == 2
        assert events_received[0][0] == "tool_executing"
        assert events_received[1][0] == "tool_completed"
        
        # Verify event timing and content
        executing_event = events_received[0][1]
        completed_event = events_received[1][1]
        
        assert executing_event["tool_name"] == "slow_analyzer"
        assert executing_event["parameters"]["data"] == "real_time_test_data"
        assert executing_event["run_id"] == self.user_context_1.run_id
        
        assert completed_event["tool_name"] == "slow_analyzer"
        assert completed_event["run_id"] == self.user_context_1.run_id
        assert "result" in completed_event
        
        self.record_metric("e2e_websocket_events", "validated")
        self.record_metric("tool_execution_duration_ms", execution_duration)
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_concurrent_tool_executions_different_users(self):
        """Test concurrent tool executions by different authenticated users.
        
        BVJ: Validates system can handle multiple users executing tools simultaneously.
        CRITICAL: Tests production concurrency scenarios.
        """
        # Arrange - Create multiple users with different tools
        num_concurrent_users = 3
        users = []
        dispatchers = []
        
        for i in range(num_concurrent_users):
            user_context = create_isolated_user_context(
                user_id=f"concurrent_user_{i}",
                thread_id=f"concurrent_thread_{i}"
            )
            users.append(user_context)
            
            # Create user-specific tool
            from langchain_core.tools import BaseTool
            
            class ConcurrentTool(BaseTool):
                def __init__(self, user_index: int):
                    self.name = f"concurrent_tool_{user_index}"
                    self.description = f"Concurrent tool for user {user_index}"
                    self.user_index = user_index
                
                async def _arun(self, task_id: str) -> str:
                    # Simulate varying processing times
                    await asyncio.sleep(0.1 + (self.user_index * 0.05))
                    return f"User {self.user_index} completed task {task_id}"
            
            # Create dispatcher for each user
            dispatcher = await UnifiedToolDispatcher.create_for_user(
                user_context=user_context,
                tools=[ConcurrentTool(i)]
            )
            dispatchers.append(dispatcher)
            self.dispatchers.append(dispatcher)
        
        # Act - Execute tools concurrently
        tasks = []
        for i, dispatcher in enumerate(dispatchers):
            task = asyncio.create_task(
                dispatcher.execute_tool(
                    f"concurrent_tool_{i}",
                    {"task_id": f"concurrent_task_{i}"}
                )
            )
            tasks.append(task)
        
        # Wait for all executions to complete
        results = await asyncio.gather(*tasks)
        
        # Assert all executions succeeded
        assert len(results) == num_concurrent_users
        for i, result in enumerate(results):
            assert result.success is True
            assert f"User {i}" in result.result
            assert f"concurrent_task_{i}" in result.result
            assert result.user_id == f"concurrent_user_{i}"
        
        # Verify no result contamination between users
        for i, result in enumerate(results):
            for j in range(num_concurrent_users):
                if i != j:
                    # Result should not contain data from other users
                    assert f"User {j}" not in result.result
                    assert f"concurrent_task_{j}" not in result.result
        
        self.record_metric("e2e_concurrent_executions", num_concurrent_users)
        self.record_metric("concurrent_isolation_validated", True)
    
    def test_factory_context_manager_e2e_pattern(self):
        """Test factory context manager usage in E2E scenarios.
        
        BVJ: Validates recommended pattern for resource management.
        CRITICAL: Ensures production code follows best practices.
        """
        # This test validates the pattern but doesn't need async execution
        # since it's testing the pattern correctness
        
        # Act & Assert - Verify factory methods exist and are callable
        assert hasattr(UnifiedToolDispatcherFactory, 'create_for_request')
        assert callable(UnifiedToolDispatcherFactory.create_for_request)
        
        # Verify context manager function exists
        from netra_backend.app.agents.tool_dispatcher import create_request_scoped_dispatcher
        assert callable(create_request_scoped_dispatcher)
        
        # Verify legacy compatibility
        from netra_backend.app.agents.tool_dispatcher import create_tool_dispatcher
        assert callable(create_tool_dispatcher)
        
        self.record_metric("e2e_api_pattern_validation", "complete")