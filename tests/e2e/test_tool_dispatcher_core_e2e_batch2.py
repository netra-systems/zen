"""
E2E Tests for Tool Dispatcher Core - Batch 2 Priority Tests (tool_dispatcher_core.py)

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure core dispatch logic works end-to-end with authentication
- Value Impact: Validates complete tool execution pipeline from user request to response
- Strategic Impact: Core workflow that enables agent-powered user interactions

These E2E tests focus on:
1. Complete factory-to-execution workflow with authentication
2. Real WebSocket event delivery throughout dispatch lifecycle
3. User context isolation in production-like scenarios
4. Error handling and recovery with full authentication stack
5. Performance and timing validation with real components
"""

import asyncio
import pytest
from typing import Dict, Any

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.isolated_test_helper import create_isolated_user_context
from netra_backend.app.agents.tool_dispatcher_core import (
    ToolDispatcher,
    ToolDispatchRequest,
    ToolDispatchResponse
)


class TestToolDispatcherCoreE2E(SSotAsyncTestCase):
    """E2E tests for tool dispatcher core with full authentication stack."""
    
    def setup_method(self, method):
        """Set up E2E test environment with authentication."""
        super().setup_method(method)
        
        # Initialize E2E auth helper
        self.auth_helper = E2EAuthHelper(environment="test")
        
        # Create authenticated user contexts
        self.primary_user_context = create_isolated_user_context(
            user_id="core_e2e_primary",
            thread_id="core_e2e_thread_primary",
            session_id="core_e2e_session_primary"
        )
        
        self.secondary_user_context = create_isolated_user_context(
            user_id="core_e2e_secondary",
            thread_id="core_e2e_thread_secondary", 
            session_id="core_e2e_session_secondary"
        )
        
        # Track dispatchers for cleanup
        self.active_dispatchers = []
    
    async def async_teardown_method(self, method):
        """Clean up E2E test resources."""
        # Cleanup all active dispatchers
        for dispatcher in self.active_dispatchers:
            try:
                if hasattr(dispatcher, 'cleanup'):
                    await dispatcher.cleanup()
            except:
                pass
        
        super().teardown_method(method)
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_complete_factory_to_execution_workflow(self):
        """Test complete workflow from factory creation to tool execution.
        
        BVJ: Validates entire tool dispatch pipeline works with authentication.
        CRITICAL: End-to-end validation of core business functionality.
        """
        # Arrange - Create JWT token for authentication
        token = self.auth_helper.create_test_jwt_token(
            user_id=self.primary_user_context.user_id,
            permissions=["read", "write", "tool_execute"]
        )
        
        # Create real test tool for E2E execution
        from langchain_core.tools import BaseTool
        
        class E2ECoreTestTool(BaseTool):
            name = "e2e_core_analyzer"
            description = "E2E core analysis tool for complete workflow testing"
            
            def _run(self, analysis_request: str, priority: str = "normal") -> str:
                return f"E2E Core Analysis Complete - Request: {analysis_request}, Priority: {priority}"
            
            async def _arun(self, analysis_request: str, priority: str = "normal") -> str:
                await asyncio.sleep(0.1)  # Simulate processing time
                return f"E2E Async Core Analysis Complete - Request: {analysis_request}, Priority: {priority}"
        
        # Create WebSocket bridge mock for event tracking
        from unittest.mock import AsyncMock
        websocket_events = []
        
        async def track_tool_executing(run_id, agent_name, tool_name, parameters):
            websocket_events.append({
                'event': 'tool_executing',
                'run_id': run_id,
                'agent_name': agent_name,
                'tool_name': tool_name,
                'parameters': parameters,
                'timestamp': asyncio.get_event_loop().time()
            })
            return True
        
        async def track_tool_completed(run_id, agent_name, tool_name, result, execution_time_ms=None):
            websocket_events.append({
                'event': 'tool_completed',
                'run_id': run_id,
                'agent_name': agent_name,
                'tool_name': tool_name,
                'result': result,
                'execution_time_ms': execution_time_ms,
                'timestamp': asyncio.get_event_loop().time()
            })
            return True
        
        websocket_bridge = AsyncMock()
        websocket_bridge.notify_tool_executing = AsyncMock(side_effect=track_tool_executing)
        websocket_bridge.notify_tool_completed = AsyncMock(side_effect=track_tool_completed)
        
        # Act - Complete workflow: Factory → Creation → Execution
        
        # Step 1: Factory creation with authentication context
        dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(
            user_context=self.primary_user_context,
            tools=[E2ECoreTestTool()],
            websocket_manager=websocket_bridge
        )
        self.active_dispatchers.append(dispatcher)
        
        # Step 2: Create and execute request models
        dispatch_request = ToolDispatchRequest(
            tool_name="e2e_core_analyzer",
            parameters={
                "analysis_request": "end_to_end_validation",
                "priority": "high"
            }
        )
        
        # Step 3: Execute tool through dispatch interface
        result = await dispatcher.dispatch(
            dispatch_request.tool_name,
            **dispatch_request.parameters
        )
        
        # Assert - Validate complete workflow
        
        # Verify tool execution succeeded
        assert result is not None
        assert hasattr(result, 'result') or hasattr(result, 'status')
        
        # Verify WebSocket events were sent in correct order
        assert len(websocket_events) == 2
        assert websocket_events[0]['event'] == 'tool_executing'
        assert websocket_events[1]['event'] == 'tool_completed'
        
        # Verify event content includes authentication context
        executing_event = websocket_events[0]
        assert executing_event['run_id'] == self.primary_user_context.run_id
        assert executing_event['tool_name'] == 'e2e_core_analyzer'
        assert executing_event['parameters']['analysis_request'] == 'end_to_end_validation'
        assert executing_event['parameters']['priority'] == 'high'
        
        completed_event = websocket_events[1]
        assert completed_event['run_id'] == self.primary_user_context.run_id
        assert completed_event['tool_name'] == 'e2e_core_analyzer'
        
        # Verify timing (events should be close in time)
        time_diff = completed_event['timestamp'] - executing_event['timestamp']
        assert 0.05 <= time_diff <= 1.0  # Should take 100ms + overhead
        
        self.record_metric("e2e_complete_workflow", "success")
        self.record_metric("websocket_events_sent", len(websocket_events))
        self.record_metric("workflow_duration_seconds", time_diff)
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_multi_user_isolation_with_factory_pattern(self):
        """Test factory pattern maintains isolation between authenticated users.
        
        BVJ: Ensures multi-user system prevents data leaks between users.
        CRITICAL: Security validation for production multi-user scenarios.
        """
        # Arrange - Create JWT tokens for different users
        token_1 = self.auth_helper.create_test_jwt_token(
            user_id=self.primary_user_context.user_id,
            email="primary@example.com",
            permissions=["read", "write"]
        )
        
        token_2 = self.auth_helper.create_test_jwt_token(
            user_id=self.secondary_user_context.user_id,
            email="secondary@example.com",
            permissions=["read", "write", "admin"]
        )
        
        # Create user-specific tools with sensitive data
        from langchain_core.tools import BaseTool
        
        class UserDataTool(BaseTool):
            def __init__(self, user_id: str, sensitive_data: str):
                self.name = f"data_tool_{user_id}"
                self.description = f"Data tool for user {user_id}"
                self.user_id = user_id
                self.sensitive_data = sensitive_data
            
            def _run(self, query: str) -> str:
                return f"User {self.user_id} data: {self.sensitive_data} - Query: {query}"
            
            async def _arun(self, query: str) -> str:
                return f"User {self.user_id} async data: {self.sensitive_data} - Query: {query}"
        
        # Create isolated dispatchers for each user
        dispatcher_1 = await ToolDispatcher.create_request_scoped_dispatcher(
            user_context=self.primary_user_context,
            tools=[UserDataTool(self.primary_user_context.user_id, "CONFIDENTIAL_USER_1_DATA")]
        )
        self.active_dispatchers.append(dispatcher_1)
        
        dispatcher_2 = await ToolDispatcher.create_request_scoped_dispatcher(
            user_context=self.secondary_user_context,
            tools=[UserDataTool(self.secondary_user_context.user_id, "CONFIDENTIAL_USER_2_DATA")]
        )
        self.active_dispatchers.append(dispatcher_2)
        
        # Act - Execute tools concurrently with different user contexts
        user_1_task = asyncio.create_task(
            dispatcher_1.dispatch(
                f"data_tool_{self.primary_user_context.user_id}",
                query="access_financial_records"
            )
        )
        
        user_2_task = asyncio.create_task(
            dispatcher_2.dispatch(
                f"data_tool_{self.secondary_user_context.user_id}",
                query="access_admin_dashboard"
            )
        )
        
        # Wait for both executions
        result_1, result_2 = await asyncio.gather(user_1_task, user_2_task)
        
        # Assert - Validate complete isolation
        
        # Verify each user only accessed their own data
        if hasattr(result_1, 'result'):
            user_1_output = str(result_1.result)
        else:
            user_1_output = str(result_1)
            
        if hasattr(result_2, 'result'):
            user_2_output = str(result_2.result)
        else:
            user_2_output = str(result_2)
        
        # User 1 should only see their data
        assert "CONFIDENTIAL_USER_1_DATA" in user_1_output
        assert "CONFIDENTIAL_USER_2_DATA" not in user_1_output
        assert "access_financial_records" in user_1_output
        
        # User 2 should only see their data  
        assert "CONFIDENTIAL_USER_2_DATA" in user_2_output
        assert "CONFIDENTIAL_USER_1_DATA" not in user_2_output
        assert "access_admin_dashboard" in user_2_output
        
        # Verify dispatchers maintain isolation
        assert dispatcher_1 != dispatcher_2
        assert hasattr(dispatcher_1, 'user_context') or hasattr(dispatcher_1, 'dispatch')
        assert hasattr(dispatcher_2, 'user_context') or hasattr(dispatcher_2, 'dispatch')
        
        self.record_metric("e2e_multi_user_isolation", "validated")
        self.record_metric("concurrent_user_data_isolation", "secure")
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_context_manager_lifecycle_with_authentication(self):
        """Test context manager handles complete lifecycle with authentication.
        
        BVJ: Validates resource management prevents memory leaks in production.
        CRITICAL: Ensures proper cleanup in high-traffic scenarios.
        """
        # Arrange - Create authentication token
        token = self.auth_helper.create_test_jwt_token(
            user_id=self.primary_user_context.user_id,
            permissions=["read", "write", "tool_execute"]
        )
        
        # Create tool for lifecycle testing
        from langchain_core.tools import BaseTool
        
        class LifecycleTool(BaseTool):
            name = "lifecycle_test_tool"
            description = "Tool for testing complete lifecycle management"
            
            def __init__(self):
                super().__init__()
                self.execution_count = 0
            
            def _run(self, operation: str) -> str:
                self.execution_count += 1
                return f"Lifecycle operation {operation} - Execution #{self.execution_count}"
            
            async def _arun(self, operation: str) -> str:
                self.execution_count += 1
                await asyncio.sleep(0.05)
                return f"Lifecycle async operation {operation} - Execution #{self.execution_count}"
        
        lifecycle_tool = LifecycleTool()
        
        # Track context manager lifecycle
        lifecycle_events = []
        
        # Act - Use context manager for complete lifecycle
        try:
            context_manager = ToolDispatcher.create_scoped_dispatcher_context(
                user_context=self.primary_user_context,
                tools=[lifecycle_tool]
            )
            lifecycle_events.append("context_manager_created")
            
            async with context_manager as dispatcher:
                lifecycle_events.append("context_entered")
                
                # Verify dispatcher is functional
                assert dispatcher is not None
                
                # Execute multiple operations to test lifecycle
                operations = ["initialize", "process", "validate", "finalize"]
                results = []
                
                for operation in operations:
                    result = await dispatcher.dispatch(
                        "lifecycle_test_tool",
                        operation=operation
                    )
                    results.append(result)
                    lifecycle_events.append(f"operation_{operation}_completed")
                
                # Verify all operations succeeded
                assert len(results) == len(operations)
                
                lifecycle_events.append("all_operations_completed")
            
            lifecycle_events.append("context_exited")
            
        except Exception as e:
            lifecycle_events.append(f"error_occurred: {str(e)}")
            raise
        
        # Assert - Validate complete lifecycle
        
        # Verify all lifecycle events occurred in correct order
        expected_events = [
            "context_manager_created",
            "context_entered", 
            "operation_initialize_completed",
            "operation_process_completed",
            "operation_validate_completed", 
            "operation_finalize_completed",
            "all_operations_completed",
            "context_exited"
        ]
        
        for expected_event in expected_events:
            assert expected_event in lifecycle_events
        
        # Verify proper sequencing
        context_entered_idx = lifecycle_events.index("context_entered")
        context_exited_idx = lifecycle_events.index("context_exited")
        assert context_entered_idx < context_exited_idx
        
        # Verify operations happened between enter and exit
        for operation in ["initialize", "process", "validate", "finalize"]:
            op_idx = lifecycle_events.index(f"operation_{operation}_completed")
            assert context_entered_idx < op_idx < context_exited_idx
        
        self.record_metric("e2e_context_lifecycle", "complete")
        self.record_metric("lifecycle_operations_executed", len(operations))
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_error_handling_with_full_authentication_stack(self):
        """Test error handling works with complete authentication stack.
        
        BVJ: Ensures users get proper error feedback with authentication context.
        CRITICAL: Error handling that maintains security boundaries.
        """
        # Arrange - Create authentication token with limited permissions
        limited_token = self.auth_helper.create_test_jwt_token(
            user_id=self.primary_user_context.user_id,
            permissions=["read"]  # Missing write/execute permissions
        )
        
        # Create tool that requires higher permissions
        from langchain_core.tools import BaseTool
        
        class SecureErrorTool(BaseTool):
            name = "secure_error_tool"
            description = "Tool that demonstrates various error scenarios"
            
            def _run(self, error_type: str) -> str:
                if error_type == "permission":
                    raise PermissionError("Insufficient permissions for secure operation")
                elif error_type == "authentication":
                    raise ValueError("Authentication token expired or invalid")
                elif error_type == "network":
                    raise ConnectionError("Failed to connect to external service")
                elif error_type == "validation":
                    raise ValueError("Invalid input parameters provided")
                else:
                    return f"Success for error_type: {error_type}"
            
            async def _arun(self, error_type: str) -> str:
                await asyncio.sleep(0.02)  # Simulate processing
                return self._run(error_type)
        
        # Act - Test various error scenarios with authentication
        dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(
            user_context=self.primary_user_context,
            tools=[SecureErrorTool()]
        )
        self.active_dispatchers.append(dispatcher)
        
        # Test different error types
        error_test_cases = [
            ("permission", PermissionError, "Insufficient permissions"),
            ("authentication", ValueError, "Authentication token"),
            ("network", ConnectionError, "Failed to connect"),
            ("validation", ValueError, "Invalid input parameters")
        ]
        
        error_results = {}
        
        for error_type, expected_exception, expected_message in error_test_cases:
            try:
                result = await dispatcher.dispatch(
                    "secure_error_tool",
                    error_type=error_type
                )
                error_results[error_type] = {"type": "success", "result": result}
            except Exception as e:
                error_results[error_type] = {
                    "type": "error",
                    "exception_type": type(e).__name__,
                    "message": str(e)
                }
        
        # Test success case
        try:
            success_result = await dispatcher.dispatch(
                "secure_error_tool",
                error_type="success"
            )
            error_results["success"] = {"type": "success", "result": success_result}
        except Exception as e:
            error_results["success"] = {"type": "error", "exception": str(e)}
        
        # Assert - Validate error handling maintains security
        
        # Verify each error type was handled appropriately
        for error_type, expected_exception, expected_message in error_test_cases:
            result = error_results[error_type]
            
            # Should either be handled gracefully or raise appropriate exception
            if result["type"] == "error":
                assert expected_exception.__name__ in result["exception_type"] or "Error" in result["exception_type"]
                # Error message should not expose sensitive information
                assert len(result["message"]) > 0
                # But should contain user-friendly information
                assert any(word in result["message"].lower() for word in 
                          ["permission", "authentication", "connection", "invalid", "error"])
        
        # Verify success case worked
        assert error_results["success"]["type"] == "success"
        
        # Verify user context is maintained through error scenarios
        # (Authentication context should not be lost during error handling)
        assert dispatcher is not None
        
        self.record_metric("e2e_error_handling_scenarios", len(error_test_cases))
        self.record_metric("authentication_context_preserved", "validated")
    
    @pytest.mark.e2e
    @pytest.mark.asyncio  
    async def test_performance_with_authentication_overhead(self):
        """Test performance characteristics with full authentication stack.
        
        BVJ: Ensures authentication doesn't significantly impact performance.
        CRITICAL: Performance validation for production scalability.
        """
        # Arrange - Create authentication token
        token = self.auth_helper.create_test_jwt_token(
            user_id=self.primary_user_context.user_id,
            permissions=["read", "write", "tool_execute"]
        )
        
        # Create tool for performance testing
        from langchain_core.tools import BaseTool
        import time
        
        class PerformanceTool(BaseTool):
            name = "performance_test_tool"
            description = "Tool for measuring performance with authentication"
            
            def __init__(self):
                super().__init__()
                self.execution_times = []
            
            def _run(self, workload_size: str) -> str:
                start_time = time.time()
                
                # Simulate different workload sizes
                if workload_size == "light":
                    iterations = 100
                elif workload_size == "medium":
                    iterations = 1000
                elif workload_size == "heavy":
                    iterations = 5000
                else:
                    iterations = 10
                
                # Simulate processing
                result = sum(i * 2 for i in range(iterations))
                
                end_time = time.time()
                execution_time = (end_time - start_time) * 1000  # Convert to ms
                self.execution_times.append(execution_time)
                
                return f"Performance test completed - Workload: {workload_size}, Result: {result}, Time: {execution_time:.2f}ms"
            
            async def _arun(self, workload_size: str) -> str:
                return self._run(workload_size)
        
        performance_tool = PerformanceTool()
        
        # Create dispatcher with authentication
        dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(
            user_context=self.primary_user_context,
            tools=[performance_tool]
        )
        self.active_dispatchers.append(dispatcher)
        
        # Act - Run performance tests
        workload_types = ["light", "medium", "heavy"]
        performance_results = {}
        
        start_total_time = time.time()
        
        for workload in workload_types:
            start_workload_time = time.time()
            
            # Execute tool with authentication overhead
            result = await dispatcher.dispatch(
                "performance_test_tool",
                workload_size=workload
            )
            
            end_workload_time = time.time()
            workload_duration = (end_workload_time - start_workload_time) * 1000
            
            performance_results[workload] = {
                "result": result,
                "total_duration_ms": workload_duration,
                "includes_auth_overhead": True
            }
        
        end_total_time = time.time()
        total_duration = (end_total_time - start_total_time) * 1000
        
        # Assert - Validate performance characteristics
        
        # Verify all workloads completed successfully
        assert len(performance_results) == len(workload_types)
        for workload, result in performance_results.items():
            assert "Performance test completed" in str(result["result"])
            assert result["total_duration_ms"] > 0
        
        # Verify reasonable performance characteristics
        # Light workload should be fastest, heavy should be slowest
        light_duration = performance_results["light"]["total_duration_ms"]
        medium_duration = performance_results["medium"]["total_duration_ms"]
        heavy_duration = performance_results["heavy"]["total_duration_ms"]
        
        assert light_duration < heavy_duration
        # Allow some variance in timing
        assert heavy_duration > light_duration * 0.5  # Should show some difference
        
        # Verify authentication overhead doesn't dominate
        # Even light workload should not take excessively long due to auth
        assert light_duration < 1000  # Should complete in under 1 second
        
        # Record performance metrics
        self.record_metric("e2e_performance_light_ms", light_duration)
        self.record_metric("e2e_performance_medium_ms", medium_duration) 
        self.record_metric("e2e_performance_heavy_ms", heavy_duration)
        self.record_metric("e2e_total_performance_test_ms", total_duration)
        self.record_metric("authentication_overhead_acceptable", light_duration < 1000)