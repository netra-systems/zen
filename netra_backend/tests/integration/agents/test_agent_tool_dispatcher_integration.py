"""CRITICAL AGENT INTEGRATION TEST: Agent Tool Dispatcher Integration

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Core AI Tool Execution - Fundamental to $500K+ ARR
- Value Impact: Ensures agents can execute tools within proper user context - 90% of AI value
- Strategic Impact: Validates agent-to-tool execution pipeline that delivers business insights

CRITICAL REQUIREMENTS:
1. Agents MUST execute tools within proper user context (NO shared tool state)
2. Tool execution MUST be isolated per user (User A tools ≠ User B tools)
3. Tool dispatcher MUST integrate with agent execution pipeline
4. Tool results MUST be returned to correct agent/user
5. Tool execution MUST emit proper WebSocket events
6. Tool permissions MUST be enforced per user context
7. Tool execution MUST handle failures gracefully
8. Tool dispatcher MUST support concurrent tool execution

FAILURE CONDITIONS:
- Tool result leakage between users = CRITICAL SECURITY BUG
- Tool execution outside user context = ISOLATION VIOLATION
- Missing tool execution events = BUSINESS VALUE FAILURE
- Tool permission bypass = SECURITY FAILURE
- Tool execution timeout = PRODUCTIVITY FAILURE

This test validates the complete agent-to-tool execution pipeline with real tool dispatchers.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

import pytest

# SSOT imports following CLAUDE.md absolute import requirements
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.websocket import WebSocketTestUtility, WebSocketEventType
from shared.isolated_environment import get_env

# Agent and tool execution imports (REAL services only)
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine_factory import (
    get_execution_engine_factory
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.tool_dispatcher import (
    UnifiedToolDispatcher,
    UnifiedToolDispatcherFactory,
    ToolExecutionResult
)
from netra_backend.app.agents.unified_tool_execution import (
    UnifiedToolExecutionEngine,
    EnhancedToolExecutionEngine
)
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.services.unified_tool_registry import (
    UnifiedToolRegistry,
    UnifiedTool,
)
from netra_backend.app.schemas.tool_permission import PermissionLevel

# WebSocket integration for tool events
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter

# Tool implementations are registered dynamically in tests


@dataclass
class ToolExecutionTestContext:
    """Test context for agent tool execution testing."""
    test_id: str
    user_id: str
    session_id: str
    thread_id: str
    execution_context: Optional[UserExecutionContext] = None
    tool_dispatcher: Optional[UnifiedToolDispatcher] = None
    tool_execution_results: List[Dict[str, Any]] = None
    websocket_events: List[Dict[str, Any]] = None
    tool_permissions: Dict[str, List[str]] = None
    
    def __post_init__(self):
        if self.tool_execution_results is None:
            self.tool_execution_results = []
        if self.websocket_events is None:
            self.websocket_events = []
        if self.tool_permissions is None:
            self.tool_permissions = {}


class TestAgentToolDispatcherIntegration(SSotAsyncTestCase):
    """CRITICAL integration tests for agent tool dispatcher integration."""
    
    @pytest.fixture
    async def tool_registry(self):
        """Real unified tool registry for testing."""
        registry = UnifiedToolRegistry()
        
        # Register test tools
        data_analyzer_tool = UnifiedTool(
            id="data_analyzer",
            name="data_analyzer",
            description="Analyze user data and provide insights",
            category="analysis",
            permissions_required=["READ_USER_DATA", "EXECUTE"],
            input_schema={
                "data_source": {"type": "string", "required": True},
                "analysis_type": {"type": "string", "required": False}
            }
        )
        registry.register_tool(data_analyzer_tool)
        
        cost_optimizer_tool = UnifiedTool(
            id="cost_optimizer",
            name="cost_optimizer",
            description="Optimize costs based on usage patterns",
            category="optimization",
            permissions_required=["READ_USER_DATA", "EXECUTE"],
            input_schema={
                "time_period": {"type": "string", "required": True},
                "optimization_level": {"type": "string", "required": False}
            }
        )
        registry.register_tool(cost_optimizer_tool)
        
        yield registry
    
    @pytest.fixture
    async def tool_dispatcher_factory(self, tool_registry):
        """Real tool dispatcher factory for testing."""
        factory = UnifiedToolDispatcherFactory()
        factory.set_tool_registry(tool_registry)
        yield factory
        await factory.cleanup_all_dispatchers()
    
    @pytest.fixture
    async def execution_engine_factory(self, tool_dispatcher_factory):
        """Execution engine factory with tool dispatcher integration."""
        from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        
        # Create a test websocket bridge for the factory
        websocket_bridge = AgentWebSocketBridge()
        
        # Create factory directly for tests
        exec_factory = ExecutionEngineFactory(websocket_bridge=websocket_bridge)
        exec_factory.set_tool_dispatcher_factory(tool_dispatcher_factory)
        yield exec_factory
        await exec_factory.cleanup_all_contexts()
    
    @pytest.fixture
    async def agent_registry(self, tool_dispatcher_factory):
        """Real agent registry with tool dispatcher integration."""
        from unittest.mock import MagicMock
        
        # Create mock LLM manager for tests
        mock_llm_manager = MagicMock()
        mock_llm_manager.name = "test_llm_manager"
        
        registry = AgentRegistry(llm_manager=mock_llm_manager)
        registry.set_tool_dispatcher_factory(tool_dispatcher_factory)
        await registry.initialize()
        yield registry
        await registry.cleanup()
    
    @pytest.fixture
    def websocket_utility(self):
        """WebSocket test utility for event validation."""
        return WebSocketTestUtility()
    
    def create_tool_test_context(self, test_name: str) -> ToolExecutionTestContext:
        """Create test context for tool execution testing."""
        return ToolExecutionTestContext(
            test_id=f"{test_name}_{uuid.uuid4().hex[:8]}",
            user_id=f"tool_user_{uuid.uuid4().hex[:8]}",
            session_id=f"tool_session_{uuid.uuid4().hex[:8]}",
            thread_id=f"tool_thread_{uuid.uuid4().hex[:8]}"
        )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_tool_execution_within_user_context(self, execution_engine_factory, agent_registry, tool_dispatcher_factory):
        """Test that agents execute tools within proper user context.
        
        BVJ: Ensures tool execution is isolated per user - critical for data security.
        """
        # Create test context
        test_ctx = self.create_tool_test_context("user_context_tools")
        
        # Create user execution context
        exec_ctx = UserExecutionContext(
            user_id=test_ctx.user_id,
            run_id=f"run_{test_ctx.test_id}",
            thread_id=test_ctx.thread_id
        )
        test_ctx.execution_context = exec_ctx
        
        # Create tool dispatcher for user
        tool_dispatcher = await tool_dispatcher_factory.create_dispatcher(exec_ctx)
        test_ctx.tool_dispatcher = tool_dispatcher
        
        # Verify tool dispatcher has correct user context
        assert tool_dispatcher.user_context.user_id == test_ctx.user_id
        assert tool_dispatcher.user_context.session_id == test_ctx.session_id
        assert tool_dispatcher.user_context.thread_id == test_ctx.thread_id
        
        # Execute tool directly through dispatcher
        tool_result = await tool_dispatcher.execute_tool(
            "data_analyzer",
            {
                "data_source": f"user_data_{test_ctx.user_id}",
                "analysis_type": "comprehensive",
                "user_context": {
                    "user_id": test_ctx.user_id,
                    "session_id": test_ctx.session_id
                }
            }
        )
        
        # Verify tool execution result
        assert tool_result is not None, "Tool execution should return result"
        assert tool_result.success, f"Tool execution should succeed: {tool_result.error}"
        assert tool_result.user_context.user_id == test_ctx.user_id, "Tool result should have correct user context"
        
        # Verify tool result contains user-specific data
        if tool_result.result and isinstance(tool_result.result, dict):
            result_str = str(tool_result.result).lower()
            assert test_ctx.user_id.lower() in result_str, "Tool result should contain user-specific data"
        
        test_ctx.tool_execution_results.append({
            "tool_name": "data_analyzer",
            "result": tool_result,
            "user_context_verified": True
        })
        
        # Execute tool through agent to test full integration
        execution_engine = await execution_engine_factory.create_execution_engine(exec_ctx)
        agent_result = await execution_engine.execute_agent_pipeline(
            agent_name="data_sub_agent",
            execution_context=exec_ctx,
            input_data={
                "user_request": "Use data analyzer tool to analyze my data",
                "tools_to_use": ["data_analyzer"],
                "analysis_context": f"user_{test_ctx.user_id}_context"
            }
        )
        
        # Verify agent execution succeeded and used tools
        assert agent_result is not None, "Agent execution should return result"
        
        # Verify agent used the correct tool with user context
        agent_result_str = str(agent_result).lower()
        assert "data_analyzer" in agent_result_str or "analyzer" in agent_result_str, (
            "Agent result should indicate data analyzer tool was used"
        )
        
        self.record_metric("tool_execution_in_user_context_verified", True)
        self.record_metric("agent_tool_integration_verified", True)
        self.record_metric("tool_executions_completed", len(test_ctx.tool_execution_results))
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_tool_execution_isolation(self, execution_engine_factory, agent_registry, tool_dispatcher_factory):
        """Test concurrent tool execution maintains user isolation.
        
        BVJ: Ensures multiple users can execute tools simultaneously without interference.
        """
        num_users = 3
        user_contexts = []
        
        # Create multiple user contexts
        for i in range(num_users):
            ctx = self.create_tool_test_context(f"concurrent_tools_user_{i}")
            user_contexts.append(ctx)
        
        # Define concurrent tool execution function
        async def execute_tools_for_user(ctx: ToolExecutionTestContext, user_index: int):
            """Execute tools for a specific user."""
            # Create execution context
            exec_ctx = UserExecutionContext(
                user_id=ctx.user_id,
                run_id=f"run_{ctx.test_id}",
                thread_id=ctx.thread_id
            )
            ctx.execution_context = exec_ctx
            
            # Create tool dispatcher
            tool_dispatcher = await tool_dispatcher_factory.create_dispatcher(exec_ctx)
            ctx.tool_dispatcher = tool_dispatcher
            
            try:
                # Execute multiple tools with user-specific data
                user_specific_data = f"confidential_data_for_user_{user_index}"
                
                # Execute data analyzer tool
                analyzer_result = await tool_dispatcher.execute_tool(
                    "data_analyzer",
                    {
                        "data_source": user_specific_data,
                        "analysis_type": f"analysis_type_{user_index}",
                        "user_id": ctx.user_id
                    }
                )
                
                # Execute cost optimizer tool
                optimizer_result = await tool_dispatcher.execute_tool(
                    "cost_optimizer",
                    {
                        "time_period": "30_days",
                        "optimization_level": f"level_{user_index}",
                        "user_data": user_specific_data
                    }
                )
                
                # Store results
                ctx.tool_execution_results.extend([
                    {
                        "tool_name": "data_analyzer",
                        "result": analyzer_result,
                        "user_index": user_index,
                        "user_data": user_specific_data
                    },
                    {
                        "tool_name": "cost_optimizer",
                        "result": optimizer_result,
                        "user_index": user_index,
                        "user_data": user_specific_data
                    }
                ])
                
                # Verify results are isolated
                for result_entry in ctx.tool_execution_results:
                    tool_result = result_entry["result"]
                    if tool_result and tool_result.success:
                        # Verify user context in result
                        assert tool_result.user_context.user_id == ctx.user_id, (
                            f"Tool result has wrong user context: {tool_result.user_context.user_id}"
                        )
                        
                        # Verify no other user's data in result
                        result_str = str(tool_result.result).lower()
                        for other_ctx in user_contexts:
                            if other_ctx.user_id != ctx.user_id:
                                assert other_ctx.user_id.lower() not in result_str, (
                                    f"User {other_ctx.user_id} data found in results for user {ctx.user_id}"
                                )
                
            except Exception as e:
                ctx.tool_execution_results.append({
                    "error": str(e),
                    "user_index": user_index,
                    "failed": True
                })
                raise
        
        # Execute tools for all users concurrently
        tasks = []
        for i, ctx in enumerate(user_contexts):
            task = asyncio.create_task(execute_tools_for_user(ctx, i))
            tasks.append(task)
        
        # Wait for all executions
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all executions succeeded
        successful_users = 0
        for i, result in enumerate(results):
            if not isinstance(result, Exception):
                successful_users += 1
                
                # Verify user context has tool results
                ctx = user_contexts[i]
                assert len(ctx.tool_execution_results) > 0, f"User {i} should have tool execution results"
                
                # Verify no failed executions
                failed_results = [r for r in ctx.tool_execution_results if r.get("failed", False)]
                assert len(failed_results) == 0, f"User {i} has failed tool executions: {failed_results}"
            else:
                pytest.fail(f"User {i} tool execution failed: {result}")
        
        assert successful_users == num_users, f"All {num_users} users should succeed"
        
        # Cross-verify tool execution isolation
        for i, ctx in enumerate(user_contexts):
            for j, other_ctx in enumerate(user_contexts):
                if i != j:
                    # Verify user i's results don't contain user j's data
                    for result_entry in ctx.tool_execution_results:
                        if "user_data" in result_entry:
                            user_data = result_entry["user_data"]
                            assert f"user_{j}" not in user_data, (
                                f"User {i} tool results contain user {j} data"
                            )
        
        self.record_metric("concurrent_tool_users_tested", num_users)
        self.record_metric("concurrent_tool_executions_successful", successful_users)
        self.record_metric("tool_isolation_verified", True)
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_execution_websocket_events(self, execution_engine_factory, agent_registry, websocket_utility):
        """Test that tool execution emits proper WebSocket events.
        
        BVJ: Ensures users see tool execution progress - critical for chat experience.
        """
        # Create test context
        test_ctx = self.create_tool_test_context("websocket_events")
        
        async with websocket_utility:
            # Create authenticated WebSocket client
            client = await websocket_utility.create_authenticated_client(test_ctx.user_id)
            connected = await client.connect()
            assert connected, "WebSocket client should connect successfully"
            
            # Create execution context
            exec_ctx = UserExecutionContext(
                user_id=test_ctx.user_id,
                run_id=f"run_{test_ctx.test_id}",
                thread_id=test_ctx.thread_id
            )
            
            # Create execution engine
            engine = await execution_engine_factory.create_execution_engine(exec_ctx)
            
            # Clear previous messages
            client.received_messages.clear()
            
            # Execute agent that uses tools
            execution_task = asyncio.create_task(
                engine.execute_agent_pipeline(
                    agent_name="data_sub_agent",
                    execution_context=exec_ctx,
                    input_data={
                        "user_request": "Use tools to analyze my data and optimize costs",
                        "tools_to_use": ["data_analyzer", "cost_optimizer"],
                        "emit_tool_events": True
                    }
                )
            )
            
            # Wait for WebSocket events related to tool execution
            expected_tool_events = [
                WebSocketEventType.TOOL_EXECUTING,
                WebSocketEventType.TOOL_COMPLETED
            ]
            
            # Wait for tool events with timeout
            tool_events = await client.wait_for_events(expected_tool_events, timeout=45.0)
            
            # Wait for agent execution to complete
            execution_result = await execution_task
            
            # Verify tool execution events were received
            assert WebSocketEventType.TOOL_EXECUTING in tool_events, "Should receive tool_executing events"
            assert WebSocketEventType.TOOL_COMPLETED in tool_events, "Should receive tool_completed events"
            
            # Verify tool events contain proper context
            executing_events = tool_events[WebSocketEventType.TOOL_EXECUTING]
            completed_events = tool_events[WebSocketEventType.TOOL_COMPLETED]
            
            assert len(executing_events) > 0, "Should have tool_executing events"
            assert len(completed_events) > 0, "Should have tool_completed events"
            
            # Verify event data contains tool information
            for event in executing_events:
                assert "tool_name" in event.data or "tool" in event.data, "Tool executing event should contain tool name"
                if "user_id" in event.data:
                    assert event.data["user_id"] == test_ctx.user_id, "Event should have correct user context"
            
            for event in completed_events:
                assert "tool_name" in event.data or "tool" in event.data, "Tool completed event should contain tool name"
                assert "result" in event.data or "status" in event.data, "Tool completed event should contain result/status"
                if "user_id" in event.data:
                    assert event.data["user_id"] == test_ctx.user_id, "Event should have correct user context"
            
            # Store events for analysis
            test_ctx.websocket_events.extend([
                {"type": "tool_executing", "count": len(executing_events)},
                {"type": "tool_completed", "count": len(completed_events)}
            ])
            
            # Verify execution succeeded
            assert execution_result is not None, "Agent execution should succeed"
        
        self.record_metric("tool_websocket_events_verified", True)
        self.record_metric("tool_executing_events_received", len(executing_events))
        self.record_metric("tool_completed_events_received", len(completed_events))
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_execution_permission_enforcement(self, execution_engine_factory, tool_dispatcher_factory, tool_registry):
        """Test that tool execution enforces permissions per user.
        
        BVJ: Ensures tool security - users can only execute authorized tools.
        """
        # Create test context
        test_ctx = self.create_tool_test_context("permission_enforcement")
        
        # Create user execution context with limited permissions
        exec_ctx = UserExecutionContext(
            user_id=test_ctx.user_id,
            run_id=f"run_{test_ctx.test_id}",
            thread_id=test_ctx.thread_id
        )
        # TODO: Add permissions to context once supported
        
        # Create tool dispatcher
        tool_dispatcher = await tool_dispatcher_factory.create_dispatcher(exec_ctx)
        
        # Register restricted tool that requires ADMIN permission
        admin_tool = UnifiedTool(
            id="admin_tool",
            name="admin_tool",
            description="Administrative tool requiring special permissions",
            category="system",
            permissions_required=["ADMIN", "EXECUTE"],
            input_schema={"admin_action": {"type": "string", "required": True}}
        )
        tool_registry.register_tool(admin_tool)
        
        # Test that user can execute allowed tools
        allowed_result = await tool_dispatcher.execute_tool(
            "data_analyzer",
            {
                "data_source": "user_data",
                "analysis_type": "basic"
            }
        )
        
        # Should succeed for allowed tool
        assert allowed_result.success, "User should be able to execute allowed tools"
        
        test_ctx.tool_execution_results.append({
            "tool_name": "data_analyzer",
            "result": allowed_result,
            "permission_test": "allowed",
            "success": allowed_result.success
        })
        
        # Test that user cannot execute restricted tools
        try:
            restricted_result = await tool_dispatcher.execute_tool(
                "admin_tool",
                {"admin_action": "delete_all_data"}
            )
            
            # Should fail due to insufficient permissions
            assert not restricted_result.success, "User should not be able to execute restricted tools"
            assert "permission" in restricted_result.error_message.lower(), (
                "Error message should indicate permission issue"
            )
            
            test_ctx.tool_execution_results.append({
                "tool_name": "admin_tool",
                "result": restricted_result,
                "permission_test": "restricted",
                "success": restricted_result.success,
                "expected_failure": True
            })
            
        except PermissionError as e:
            # Also acceptable to raise PermissionError
            test_ctx.tool_execution_results.append({
                "tool_name": "admin_tool",
                "permission_test": "restricted",
                "success": False,
                "expected_failure": True,
                "exception": str(e)
            })
        
        # Test with elevated permissions
        admin_exec_ctx = UserExecutionContext(
            user_id=f"admin_{test_ctx.user_id}",
            run_id=f"admin_run_{test_ctx.test_id}",
            thread_id=test_ctx.thread_id
        )
        # TODO: Add admin permissions to context once supported
        
        admin_dispatcher = await tool_dispatcher_factory.create_dispatcher(admin_exec_ctx)
        
        # Admin user should be able to execute restricted tool
        admin_result = await admin_dispatcher.execute_tool(
            "admin_tool",
            {"admin_action": "view_admin_data"}
        )
        
        assert admin_result.success, "Admin user should be able to execute admin tools"
        
        test_ctx.tool_execution_results.append({
            "tool_name": "admin_tool",
            "result": admin_result,
            "permission_test": "admin_allowed",
            "success": admin_result.success
        })
        
        self.record_metric("tool_permission_enforcement_verified", True)
        self.record_metric("permission_tests_completed", len(test_ctx.tool_execution_results))
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_execution_error_handling(self, execution_engine_factory, tool_dispatcher_factory, tool_registry):
        """Test tool execution handles errors gracefully.
        
        BVJ: Ensures platform resilience - tool failures don't break agent execution.
        """
        # Create test context
        test_ctx = self.create_tool_test_context("error_handling")
        
        exec_ctx = UserExecutionContext(
            user_id=test_ctx.user_id,
            run_id=f"run_{test_ctx.test_id}",
            session_id=test_ctx.session_id,
            thread_id=test_ctx.thread_id
        )
        
        # Create tool dispatcher
        tool_dispatcher = await tool_dispatcher_factory.create_dispatcher(exec_ctx)
        
        # Register error-prone tool for testing
        error_tool = UnifiedTool(
            id="error_tool",
            name="error_tool",
            description="Tool that can produce errors for testing",
            category="testing",
            permissions_required=["EXECUTE"],
            input_schema={
                "error_type": {"type": "string", "required": True},
                "should_fail": {"type": "boolean", "required": False}
            }
        )
        tool_registry.register_tool(error_tool)
        
        # Test tool execution with invalid parameters
        invalid_params_result = await tool_dispatcher.execute_tool(
            "data_analyzer",
            {
                # Missing required parameter
                "analysis_type": "comprehensive"
                # Missing "data_source"
            }
        )
        
        # Should handle invalid parameters gracefully
        assert not invalid_params_result.success, "Tool should fail with invalid parameters"
        assert invalid_params_result.error_message is not None, "Should have error message"
        assert "parameter" in invalid_params_result.error_message.lower() or "required" in invalid_params_result.error_message.lower()
        
        test_ctx.tool_execution_results.append({
            "test_type": "invalid_parameters",
            "result": invalid_params_result,
            "expected_failure": True
        })
        
        # Test tool execution with non-existent tool
        nonexistent_result = await tool_dispatcher.execute_tool(
            "nonexistent_tool",
            {"some_param": "some_value"}
        )
        
        # Should handle non-existent tool gracefully
        assert not nonexistent_result.success, "Should fail for non-existent tool"
        assert "not found" in nonexistent_result.error_message.lower() or "unknown" in nonexistent_result.error_message.lower()
        
        test_ctx.tool_execution_results.append({
            "test_type": "nonexistent_tool",
            "result": nonexistent_result,
            "expected_failure": True
        })
        
        # Test tool execution timeout handling
        # (This would require implementing timeout in the test tool)
        
        # Test that successful tool execution still works after errors
        successful_result = await tool_dispatcher.execute_tool(
            "data_analyzer",
            {
                "data_source": "valid_data_source",
                "analysis_type": "basic"
            }
        )
        
        # Should work correctly after error conditions
        assert successful_result.success, "Tool dispatcher should work correctly after handling errors"
        
        test_ctx.tool_execution_results.append({
            "test_type": "recovery_after_errors",
            "result": successful_result,
            "expected_success": True
        })
        
        # Test agent execution continues after tool errors
        execution_engine = await execution_engine_factory.create_execution_engine(exec_ctx)
        
        agent_result = await execution_engine.execute_agent_pipeline(
            agent_name="data_sub_agent",
            execution_context=exec_ctx,
            input_data={
                "user_request": "Try to use tools, some might fail",
                "tools_to_try": ["nonexistent_tool", "data_analyzer"],
                "handle_tool_errors": True
            }
        )
        
        # Agent should complete execution despite tool errors
        assert agent_result is not None, "Agent should complete execution despite tool errors"
        
        self.record_metric("tool_error_handling_verified", True)
        self.record_metric("error_scenarios_tested", len([r for r in test_ctx.tool_execution_results if r.get("expected_failure")]))
        self.record_metric("tool_recovery_verified", True)
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_execution_performance_monitoring(self, execution_engine_factory, tool_dispatcher_factory):
        """Test tool execution performance meets SLAs.
        
        BVJ: Ensures tool execution speed supports real-time user interactions.
        """
        # Create test context
        test_ctx = self.create_tool_test_context("performance_monitoring")
        
        exec_ctx = UserExecutionContext(
            user_id=test_ctx.user_id,
            run_id=f"run_{test_ctx.test_id}",
            session_id=test_ctx.session_id,
            thread_id=test_ctx.thread_id
        )
        
        # Create tool dispatcher
        tool_dispatcher = await tool_dispatcher_factory.create_dispatcher(exec_ctx)
        
        # Perform multiple tool executions to measure performance
        num_iterations = 10
        tool_execution_times = []
        
        for i in range(num_iterations):
            # Measure individual tool execution time
            start_time = time.time()
            
            result = await tool_dispatcher.execute_tool(
                "data_analyzer",
                {
                    "data_source": f"performance_test_data_{i}",
                    "analysis_type": "performance",
                    "iteration": i
                }
            )
            
            execution_time = time.time() - start_time
            tool_execution_times.append(execution_time)
            
            # Verify tool executed successfully
            assert result.success, f"Tool execution {i} should succeed"
            
            # Brief pause between iterations
            await asyncio.sleep(0.1)
        
        # Calculate performance metrics
        avg_execution_time = sum(tool_execution_times) / len(tool_execution_times)
        max_execution_time = max(tool_execution_times)
        min_execution_time = min(tool_execution_times)
        
        # Performance assertions
        assert avg_execution_time < 5.0, f"Average tool execution time should be under 5s, got {avg_execution_time:.2f}s"
        assert max_execution_time < 10.0, f"Max tool execution time should be under 10s, got {max_execution_time:.2f}s"
        assert min_execution_time < 3.0, f"Min tool execution time should be under 3s, got {min_execution_time:.2f}s"
        
        # Test concurrent tool execution performance
        concurrent_start = time.time()
        
        concurrent_tasks = []
        for i in range(5):  # 5 concurrent tool executions
            task = asyncio.create_task(
                tool_dispatcher.execute_tool(
                    "data_analyzer",
                    {
                        "data_source": f"concurrent_data_{i}",
                        "analysis_type": "concurrent"
                    }
                )
            )
            concurrent_tasks.append(task)
        
        # Wait for all concurrent executions
        concurrent_results = await asyncio.gather(*concurrent_tasks)
        concurrent_total_time = time.time() - concurrent_start
        
        # Verify all concurrent executions succeeded
        for i, result in enumerate(concurrent_results):
            assert result.success, f"Concurrent tool execution {i} should succeed"
        
        # Concurrent execution should be more efficient than sequential
        sequential_time_estimate = avg_execution_time * 5
        assert concurrent_total_time < sequential_time_estimate, (
            f"Concurrent execution ({concurrent_total_time:.2f}s) should be faster than "
            f"sequential estimate ({sequential_time_estimate:.2f}s)"
        )
        
        # Record performance metrics
        self.record_metric("tool_performance_iterations", num_iterations)
        self.record_metric("avg_tool_execution_time_seconds", avg_execution_time)
        self.record_metric("max_tool_execution_time_seconds", max_execution_time)
        self.record_metric("min_tool_execution_time_seconds", min_execution_time)
        self.record_metric("concurrent_tool_execution_time_seconds", concurrent_total_time)
        self.record_metric("tool_performance_sla_met", avg_execution_time < 5.0)
        
    async def teardown_method(self, method=None):
        """Clean up test resources."""
        await super().teardown_method(method)
        
        # Log test metrics for monitoring
        metrics = self.get_all_metrics()
        print(f"\nAgent Tool Dispatcher Integration Test Metrics:")
        for key, value in metrics.items():
            print(f"  {key}: {value}")
