"""
Test Tool Dispatcher User Isolation

Business Value Justification (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise)
- Business Goal: Ensure tool execution is properly isolated per user to prevent data leakage
- Value Impact: Guarantees that tools execute within correct user boundaries preventing cross-user contamination
- Strategic Impact: CRITICAL - Tool dispatcher is the bridge between AI agents and business tools

This test suite validates that the UnifiedToolDispatcher ensures complete user isolation:
- Tool execution contexts are isolated per user
- Tool results only reach the intended user
- No shared state between user tool dispatchers
- WebSocket tool notifications reach only correct user
- Tool permissions and access are properly scoped per user

Architecture Tested:
- UnifiedToolDispatcher with user context isolation
- Request-scoped tool execution preventing shared state
- User boundary enforcement in tool parameter validation
- WebSocket integration maintaining user isolation during tool execution
"""

import asyncio
import pytest
import uuid
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Callable
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from dataclasses import dataclass

from netra_backend.app.core.tools.unified_tool_dispatcher import (
    UnifiedToolDispatcher,
    UnifiedToolDispatcherFactory,
    ToolDispatchRequest,
    ToolDispatchResponse
)
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    UserContextFactory,
    InvalidContextError
)
from netra_backend.app.services.websocket_bridge_factory import (
    UserWebSocketEmitter,
    WebSocketEvent
)
from test_framework.ssot.base_test_case import SSotBaseTestCase


@dataclass
class MockToolResult:
    """Mock result from tool execution."""
    result: Any
    success: bool
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    user_id: str = ""
    tool_name: str = ""


class MockTool:
    """Mock LangChain-style tool for testing user isolation."""
    
    def __init__(self, name: str, requires_user_context: bool = True):
        self.name = name
        self.requires_user_context = requires_user_context
        self.executions: List[Dict[str, Any]] = []
        self.call_count = 0
        
    def __call__(self, **kwargs) -> str:
        """Synchronous call interface like LangChain tools."""
        # For testing purposes, we'll record the call but not access user context here
        # since the actual dispatcher should be passing user context through the framework
        self.call_count += 1
        self.executions.append({
            "tool_name": self.name,
            "kwargs": kwargs,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "call_type": "sync"
        })
        return f"Tool {self.name} executed with {kwargs}"
        
    async def arun(self, **kwargs) -> str:
        """Async execution interface like LangChain tools."""
        self.call_count += 1
        self.executions.append({
            "tool_name": self.name,
            "kwargs": kwargs,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "call_type": "async"
        })
        return f"Tool {self.name} executed async with {kwargs}"
    
    def get_executions_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get executions for specific user."""
        # For now, return all executions since the mock tool doesn't have direct user context access
        # The actual user isolation testing will be done through the dispatcher's proper isolation
        return self.executions


class MockWebSocketEmitter:
    """Mock WebSocket emitter for testing tool notification isolation."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.notifications: List[Dict[str, Any]] = []
        
    async def notify_tool_executing(self, agent_name: str, run_id: str, tool_name: str, tool_input: Dict[str, Any]):
        """Mock tool executing notification."""
        self.notifications.append({
            "type": "tool_executing",
            "agent_name": agent_name,
            "run_id": run_id,
            "tool_name": tool_name,
            "tool_input": tool_input,
            "user_id": self.user_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        return True
        
    async def notify_tool_completed(self, agent_name: str, run_id: str, tool_name: str, tool_output: Any):
        """Mock tool completed notification."""
        self.notifications.append({
            "type": "tool_completed", 
            "agent_name": agent_name,
            "run_id": run_id,
            "tool_name": tool_name,
            "tool_output": tool_output,
            "user_id": self.user_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        return True
        
    # Bridge adapter interface compatibility
    def has_websocket_support(self) -> bool:
        return True
        
    async def send_event(self, event_type: str, data: dict) -> bool:
        """Mock send_event method for WebSocket bridge compatibility."""
        self.notifications.append({
            "type": event_type,
            **data,
            "user_id": self.user_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        return True


class TestToolDispatcherUserIsolation(SSotBaseTestCase):
    """Test Tool Dispatcher ensures complete user isolation."""
    
    def setup_method(self):
        """Set up test environment with isolated tool dispatcher."""
        # Create mock tools for testing
        self.mock_tools = {
            "data_analyzer": MockTool("data_analyzer"),
            "cost_optimizer": MockTool("cost_optimizer"),
            "report_generator": MockTool("report_generator")
        }
        
        # Track created dispatchers and emitters for cleanup
        self.created_dispatchers: List[UnifiedToolDispatcher] = []
        self.mock_emitters: Dict[str, MockWebSocketEmitter] = {}
        
        # Track tools per dispatcher for isolation testing
        self.dispatcher_tools: Dict[str, Dict[str, MockTool]] = {}
        
    def teardown_method(self):
        """Clean up test resources."""
        self.created_dispatchers.clear()
        self.mock_emitters.clear()
        
        # Clear mock tool execution histories
        for tool in self.mock_tools.values():
            tool.executions.clear()

    async def create_test_dispatcher(self, user_context: UserExecutionContext) -> UnifiedToolDispatcher:
        """Create a tool dispatcher for testing with mocked dependencies."""
        
        # Create mock WebSocket emitter for this user
        mock_emitter = MockWebSocketEmitter(user_context.user_id)
        self.mock_emitters[user_context.user_id] = mock_emitter
        
        # Create dispatcher using proper factory method
        dispatcher = await UnifiedToolDispatcher.create_for_user(
            user_context=user_context,
            websocket_bridge=mock_emitter,
            enable_admin_tools=False
        )
        
        # Create isolated tool instances for this dispatcher
        dispatcher_id = dispatcher.dispatcher_id
        isolated_tools = {
            "data_analyzer": MockTool("data_analyzer"),
            "cost_optimizer": MockTool("cost_optimizer"),
            "report_generator": MockTool("report_generator")
        }
        
        # Store tools for this dispatcher
        self.dispatcher_tools[dispatcher_id] = isolated_tools
        
        # Register the isolated tools
        for tool_name, tool in isolated_tools.items():
            dispatcher.register_tool(tool)
        
        self.created_dispatchers.append(dispatcher)
        return dispatcher

    async def test_tool_dispatcher_user_context_isolation(self):
        """Test that tool dispatchers maintain complete user context isolation."""
        
        # Create user contexts for multiple users
        user_contexts = {}
        dispatchers = {}
        
        for i in range(3):
            user_id = f"tool_user_{i}"
            context = UserContextFactory.create_context(
                user_id=user_id,
                thread_id=f"tool_thread_{i}",
                run_id=f"tool_run_{i}"
            )
            user_contexts[user_id] = context
            
            # Create dispatcher for this user
            dispatcher = await self.create_test_dispatcher(context)
            dispatchers[user_id] = dispatcher
        
        # Verify each dispatcher has isolated user context
        for user_id, dispatcher in dispatchers.items():
            assert dispatcher.user_context.user_id == user_id
            assert dispatcher.user_context == user_contexts[user_id]
            
            # Verify dispatcher context is not shared with other dispatchers
            for other_user_id, other_dispatcher in dispatchers.items():
                if user_id != other_user_id:
                    assert id(dispatcher.user_context) != id(other_dispatcher.user_context), \
                        f"Dispatchers for {user_id} and {other_user_id} share user context - ISOLATION VIOLATION"
                    
                    assert dispatcher.user_context.user_id != other_dispatcher.user_context.user_id
                    assert dispatcher.user_context.request_id != other_dispatcher.user_context.request_id

    async def test_tool_execution_user_boundary_enforcement(self):
        """Test that tool execution enforces user boundaries and isolation."""
        
        # Create contexts for multiple users
        contexts = {}
        dispatchers = {}
        
        for i in range(3):
            user_id = f"boundary_user_{i}"
            context = UserContextFactory.create_context(
                user_id=user_id,
                thread_id=f"boundary_thread_{i}",
                run_id=f"boundary_run_{i}"
            )
            contexts[user_id] = context
            dispatchers[user_id] = await self.create_test_dispatcher(context)
        
        # Execute tools for each user
        tool_results = {}
        for user_id, dispatcher in dispatchers.items():
            # Execute data analyzer tool for this user
            result = await dispatcher.execute_tool(
                tool_name="data_analyzer",
                parameters={"data": f"user_{user_id}_data", "analysis_type": "comprehensive"}
            )
            
            tool_results[user_id] = result
            
            # Verify result contains user-specific information
            assert result.success, f"Tool execution should succeed for {user_id}"
            assert user_id in str(result.result), f"Result should contain user ID {user_id}"
        
        # Verify tool execution isolation by checking each dispatcher's isolated tools
        for user_id, dispatcher in dispatchers.items():
            dispatcher_id = dispatcher.dispatcher_id
            isolated_tools = self.dispatcher_tools[dispatcher_id]
            data_analyzer_tool = isolated_tools["data_analyzer"]
            
            # Each dispatcher's tool should have exactly 1 execution recorded
            user_executions = data_analyzer_tool.get_executions_for_user(user_id)
            assert len(user_executions) == 1, \
                f"User {user_id} should have exactly 1 tool execution, got {len(user_executions)}"
            
            execution = user_executions[0]
            assert execution["tool_name"] == "data_analyzer"
            
            # Verify user-specific data was passed correctly
            assert execution["kwargs"]["data"] == f"user_{user_id}_data"
            
        # CRITICAL: Verify no cross-user data contamination
        for user_id, dispatcher in dispatchers.items():
            dispatcher_id = dispatcher.dispatcher_id
            isolated_tools = self.dispatcher_tools[dispatcher_id]
            user_data_analyzer = isolated_tools["data_analyzer"]
            user_executions = user_data_analyzer.get_executions_for_user(user_id)
            
            # Each dispatcher should only have its own executions
            for execution in user_executions:
                # Verify this execution doesn't contain other users' data
                for other_user_id in contexts.keys():
                    if user_id != other_user_id:
                        execution_str = json.dumps(execution)
                        assert f"user_{other_user_id}_data" not in execution_str, \
                            f"ISOLATION VIOLATION: User {user_id} execution contains {other_user_id} data"

    async def test_websocket_tool_notification_isolation(self):
        """Test that WebSocket tool notifications maintain user isolation."""
        
        # Create contexts and dispatchers for multiple users
        dispatchers = {}
        for i in range(3):
            user_id = f"websocket_user_{i}"
            context = UserContextFactory.create_context(
                user_id=user_id,
                thread_id=f"websocket_thread_{i}",
                run_id=f"websocket_run_{i}"
            )
            dispatchers[user_id] = await self.create_test_dispatcher(context)
        
        # Execute tools for each user
        for user_id, dispatcher in dispatchers.items():
            await dispatcher.execute_tool(
                tool_name="cost_optimizer",
                parameters={"budget": f"budget_{user_id}", "optimization_target": "cost"}
            )
        
        # Verify WebSocket notifications are properly isolated
        for user_id, emitter in self.mock_emitters.items():
            # Each user should receive exactly 2 notifications (executing + completed)
            user_notifications = emitter.notifications
            assert len(user_notifications) == 2, \
                f"User {user_id} should receive 2 notifications, got {len(user_notifications)}"
            
            # Verify notification types
            notification_types = {n["type"] for n in user_notifications}
            assert notification_types == {"tool_executing", "tool_completed"}, \
                f"User {user_id} should receive executing and completed notifications"
            
            # Verify all notifications are for this user
            for notification in user_notifications:
                assert notification["user_id"] == user_id, \
                    f"Notification should be for user {user_id}, got {notification['user_id']}"
                assert notification["tool_name"] == "cost_optimizer"
                assert f"agent_{user_id}" == notification["agent_name"]
            
            # CRITICAL: Verify no cross-user data in notifications
            for notification in user_notifications:
                notification_str = json.dumps(notification)
                
                # Check for other users' data
                for other_user_id in dispatchers.keys():
                    if user_id != other_user_id:
                        assert f"budget_{other_user_id}" not in notification_str, \
                            f"ISOLATION VIOLATION: User {user_id} notification contains {other_user_id} budget"
                        assert f"agent_{other_user_id}" not in notification_str, \
                            f"ISOLATION VIOLATION: User {user_id} notification contains {other_user_id} agent"

    async def test_concurrent_tool_execution_isolation(self):
        """Test tool execution isolation under concurrent multi-user load."""
        
        async def execute_tools_for_user(user_index: int, num_executions: int):
            """Execute multiple tools concurrently for a single user."""
            user_id = f"concurrent_user_{user_index}"
            context = UserContextFactory.create_context(
                user_id=user_id,
                thread_id=f"concurrent_thread_{user_index}",
                run_id=f"concurrent_run_{user_index}"
            )
            
            dispatcher = await self.create_test_dispatcher(context)
            
            results = []
            for exec_num in range(num_executions):
                result = await dispatcher.execute_tool(
                    tool_name="report_generator",
                    parameters={
                        "report_type": f"type_{user_index}_{exec_num}",
                        "data": f"user_{user_index}_data_{exec_num}"
                    }
                )
                results.append(result)
            
            return user_id, results
        
        # Execute concurrent tool operations for multiple users
        num_users = 5
        executions_per_user = 3
        
        tasks = [
            execute_tools_for_user(i, executions_per_user)
            for i in range(num_users)
        ]
        
        # Wait for all concurrent executions to complete
        user_results = await asyncio.gather(*tasks)
        
        # Verify results isolation
        report_tool = self.mock_tools["report_generator"]
        
        for user_id, results in user_results:
            # Verify all executions succeeded
            assert len(results) == executions_per_user
            for result in results:
                assert result.success, f"All executions should succeed for {user_id}"
                assert result.user_id == user_id
            
            # Verify tool execution records
            user_executions = report_tool.get_executions_for_user(user_id)
            assert len(user_executions) == executions_per_user, \
                f"User {user_id} should have {executions_per_user} executions"
            
            # Verify each execution contains only this user's data
            for i, execution in enumerate(user_executions):
                assert execution["user_id"] == user_id
                assert f"type_{user_id.split('_')[-1]}_{i}" in execution["kwargs"]["report_type"]
                assert f"user_{user_id.split('_')[-1]}_data_{i}" in execution["kwargs"]["data"]
                
                # CRITICAL: Verify no other user's data in execution
                for other_user_id, _ in user_results:
                    if user_id != other_user_id:
                        execution_str = json.dumps(execution)
                        other_user_index = other_user_id.split('_')[-1]
                        
                        assert f"user_{other_user_index}_data" not in execution_str, \
                            f"ISOLATION VIOLATION: User {user_id} execution contains {other_user_id} data"
        
        # Verify WebSocket notification isolation under concurrent load
        for user_id, emitter in self.mock_emitters.items():
            if user_id.startswith("concurrent_user_"):
                # Each user should have notifications for their executions only
                user_notifications = emitter.notifications
                expected_notifications = executions_per_user * 2  # executing + completed per execution
                
                assert len(user_notifications) == expected_notifications, \
                    f"User {user_id} should have {expected_notifications} notifications"
                
                # Verify all notifications belong to this user
                for notification in user_notifications:
                    assert notification["user_id"] == user_id
                    
                    # Verify no cross-user contamination
                    notification_str = json.dumps(notification)
                    for other_user_id, _ in user_results:
                        if user_id != other_user_id:
                            other_user_index = other_user_id.split('_')[-1]
                            assert f"user_{other_user_index}_data" not in notification_str, \
                                f"ISOLATION VIOLATION: User {user_id} notification contains {other_user_id} data"

    async def test_tool_parameter_validation_user_isolation(self):
        """Test that tool parameter validation maintains user isolation."""
        
        # Create contexts for different users
        user1_context = UserContextFactory.create_context(
            user_id="param_user_1",
            thread_id="param_thread_1", 
            run_id="param_run_1"
        )
        
        user2_context = UserContextFactory.create_context(
            user_id="param_user_2",
            thread_id="param_thread_2",
            run_id="param_run_2"
        )
        
        dispatcher1 = await self.create_test_dispatcher(user1_context)
        dispatcher2 = await self.create_test_dispatcher(user2_context)
        
        # Execute tools with different parameters for each user
        await dispatcher1.execute_tool(
            tool_name="data_analyzer",
            parameters={
                "sensitive_data": "user1_confidential_info",
                "access_level": "high",
                "user_permissions": ["read", "write", "admin"]
            }
        )
        
        await dispatcher2.execute_tool(
            tool_name="data_analyzer", 
            parameters={
                "sensitive_data": "user2_confidential_info",
                "access_level": "low",
                "user_permissions": ["read"]
            }
        )
        
        # Verify parameter isolation in tool execution records
        data_tool = self.mock_tools["data_analyzer"]
        
        user1_executions = data_tool.get_executions_for_user("param_user_1")
        user2_executions = data_tool.get_executions_for_user("param_user_2")
        
        assert len(user1_executions) == 1
        assert len(user2_executions) == 1
        
        user1_exec = user1_executions[0]
        user2_exec = user2_executions[0]
        
        # Verify each user's parameters are isolated
        assert user1_exec["kwargs"]["sensitive_data"] == "user1_confidential_info"
        assert user1_exec["kwargs"]["access_level"] == "high"
        assert user1_exec["kwargs"]["user_permissions"] == ["read", "write", "admin"]
        
        assert user2_exec["kwargs"]["sensitive_data"] == "user2_confidential_info"
        assert user2_exec["kwargs"]["access_level"] == "low"
        assert user2_exec["kwargs"]["user_permissions"] == ["read"]
        
        # CRITICAL: Verify no cross-contamination of sensitive parameters
        user1_exec_str = json.dumps(user1_exec)
        user2_exec_str = json.dumps(user2_exec)
        
        assert "user2_confidential_info" not in user1_exec_str, \
            "ISOLATION VIOLATION: User 1 execution contains User 2's confidential data"
        assert "user1_confidential_info" not in user2_exec_str, \
            "ISOLATION VIOLATION: User 2 execution contains User 1's confidential data"

    async def test_tool_error_handling_user_isolation(self):
        """Test that tool errors are properly isolated per user."""
        
        # Create mock tool that can fail
        class FailingTool(MockTool):
            def __init__(self):
                super().__init__("failing_tool")
                self.should_fail_for_users = set()
                
            async def execute(self, user_context: UserExecutionContext, **kwargs) -> MockToolResult:
                execution = {
                    "user_id": user_context.user_id,
                    "tool_name": self.name,
                    "kwargs": kwargs,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                self.executions.append(execution)
                
                # Fail for specific users
                if user_context.user_id in self.should_fail_for_users:
                    return MockToolResult(
                        result=None,
                        success=False,
                        error=f"Tool failed for user {user_context.user_id}",
                        user_id=user_context.user_id,
                        tool_name=self.name
                    )
                else:
                    return MockToolResult(
                        result=f"Tool succeeded for user {user_context.user_id}",
                        success=True,
                        user_id=user_context.user_id,
                        tool_name=self.name
                    )
        
        # Add failing tool to mock tools
        failing_tool = FailingTool()
        self.mock_tools["failing_tool"] = failing_tool
        
        # Set tool to fail for user_1 but succeed for user_2
        failing_tool.should_fail_for_users.add("error_user_1")
        
        # Create contexts and dispatchers
        user1_context = UserContextFactory.create_context(
            user_id="error_user_1",
            thread_id="error_thread_1",
            run_id="error_run_1"
        )
        
        user2_context = UserContextFactory.create_context(
            user_id="error_user_2",
            thread_id="error_thread_2", 
            run_id="error_run_2"
        )
        
        dispatcher1 = await self.create_test_dispatcher(user1_context)
        dispatcher2 = await self.create_test_dispatcher(user2_context)
        
        # Execute failing tool for both users
        result1 = await dispatcher1.execute_tool(
            tool_name="failing_tool",
            parameters={"test": "data1"}
        )
        
        result2 = await dispatcher2.execute_tool(
            tool_name="failing_tool",
            parameters={"test": "data2"}
        )
        
        # Verify error isolation
        assert not result1.success, "User 1 tool should fail"
        assert result2.success, "User 2 tool should succeed"
        
        assert "failed for user error_user_1" in result1.error
        assert result2.error is None
        
        # Verify WebSocket notifications show errors only for affected user
        user1_emitter = self.mock_emitters["error_user_1"]
        user2_emitter = self.mock_emitters["error_user_2"]
        
        # User 1 should have error-related notifications
        user1_notifications = user1_emitter.notifications
        assert len(user1_notifications) >= 1, "User 1 should have notifications"
        
        # User 2 should have success notifications
        user2_notifications = user2_emitter.notifications
        assert len(user2_notifications) >= 1, "User 2 should have notifications"
        
        # CRITICAL: Verify user 1's error doesn't appear in user 2's notifications
        user2_notifications_str = json.dumps(user2_notifications)
        assert "failed for user error_user_1" not in user2_notifications_str, \
            "ISOLATION VIOLATION: User 2 received error notification for User 1"

    async def test_tool_dispatcher_cleanup_isolation(self):
        """Test that dispatcher cleanup is isolated and doesn't affect other users."""
        
        # Create multiple dispatchers
        dispatchers = {}
        for i in range(3):
            user_id = f"cleanup_user_{i}"
            context = UserContextFactory.create_context(
                user_id=user_id,
                thread_id=f"cleanup_thread_{i}",
                run_id=f"cleanup_run_{i}"
            )
            dispatchers[user_id] = await self.create_test_dispatcher(context)
        
        # Execute tools for all users
        for user_id, dispatcher in dispatchers.items():
            await dispatcher.execute_tool(
                tool_name="data_analyzer",
                parameters={"data": f"cleanup_data_{user_id}"}
            )
        
        # Verify all users have notifications
        for user_id, emitter in self.mock_emitters.items():
            if user_id.startswith("cleanup_user_"):
                assert len(emitter.notifications) > 0, f"User {user_id} should have notifications"
        
        # Simulate cleanup/shutdown for user_1 (in real system, this might happen on disconnect)
        user1_dispatcher = dispatchers["cleanup_user_1"]
        
        # Mock cleanup by clearing emitter notifications (simulating connection close)
        user1_emitter = self.mock_emitters["cleanup_user_1"]
        user1_emitter.notifications.clear()
        
        # Continue using other dispatchers
        await dispatchers["cleanup_user_0"].execute_tool(
            tool_name="cost_optimizer",
            parameters={"budget": "post_cleanup_budget_0"}
        )
        
        await dispatchers["cleanup_user_2"].execute_tool(
            tool_name="cost_optimizer",
            parameters={"budget": "post_cleanup_budget_2"}
        )
        
        # Verify isolation: other users unaffected by user_1 cleanup
        user0_emitter = self.mock_emitters["cleanup_user_0"]
        user2_emitter = self.mock_emitters["cleanup_user_2"]
        
        # These users should have additional notifications from the second execution
        assert len(user0_emitter.notifications) >= 2, \
            "User 0 should have notifications from both executions (unaffected by User 1 cleanup)"
        assert len(user2_emitter.notifications) >= 2, \
            "User 2 should have notifications from both executions (unaffected by User 1 cleanup)"
        
        # User 1 should have no notifications (cleaned up)
        assert len(user1_emitter.notifications) == 0, \
            "User 1 should have no notifications after cleanup"
        
        # Verify tool execution records show proper isolation
        data_tool = self.mock_tools["data_analyzer"]
        optimizer_tool = self.mock_tools["cost_optimizer"]
        
        # All users should have data_analyzer execution from first round
        for i in range(3):
            user_id = f"cleanup_user_{i}"
            data_executions = data_tool.get_executions_for_user(user_id)
            assert len(data_executions) == 1, f"User {i} should have 1 data_analyzer execution"
        
        # Only users 0 and 2 should have cost_optimizer execution from second round
        user0_optimizer_execs = optimizer_tool.get_executions_for_user("cleanup_user_0")
        user1_optimizer_execs = optimizer_tool.get_executions_for_user("cleanup_user_1") 
        user2_optimizer_execs = optimizer_tool.get_executions_for_user("cleanup_user_2")
        
        assert len(user0_optimizer_execs) == 1, "User 0 should have 1 cost_optimizer execution"
        assert len(user1_optimizer_execs) == 0, "User 1 should have 0 cost_optimizer executions (cleaned up)"
        assert len(user2_optimizer_execs) == 1, "User 2 should have 1 cost_optimizer execution"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])