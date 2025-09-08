"""
Tool Dispatcher Core Unit Tests - Phase 2 Batch 1

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure tool dispatching system works reliably for chat value delivery
- Value Impact: Tool execution enables AI agents to deliver actionable insights to users
- Strategic Impact: Core platform functionality that drives user engagement and retention

CRITICAL: These tests validate the core dispatching logic that enables AI agents to execute 
tools and deliver business value to users through the chat interface.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta

from netra_backend.app.agents.tool_dispatcher_core import (
    ToolDispatcher,
    ToolDispatchRequest,
    ToolDispatchResponse
)
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.schemas.tool import ToolInput, ToolResult, ToolStatus
from langchain_core.tools import BaseTool
from test_framework.ssot.base_test_case import SSotBaseTestCase


class MockUserExecutionContext:
    """Mock user context for testing."""
    
    def __init__(self, user_id: str = "test-user-123"):
        self.user_id = user_id
        self.request_id = f"req-{int(datetime.now(timezone.utc).timestamp())}"
        self.session_id = f"session-{user_id}"
        self.metadata = {}


class MockWebSocketManager:
    """Mock WebSocket manager for testing."""
    
    def __init__(self):
        self.events_sent = []
        
    async def notify_tool_executing(self, tool_name: str, **kwargs):
        """Mock tool executing notification."""
        self.events_sent.append({"type": "tool_executing", "tool_name": tool_name, "kwargs": kwargs})
        
    async def notify_tool_completed(self, tool_name: str, result: Any, **kwargs):
        """Mock tool completed notification."""
        self.events_sent.append({"type": "tool_completed", "tool_name": tool_name, "result": result, "kwargs": kwargs})


class MockBaseTool(BaseTool):
    """Mock LangChain BaseTool for testing."""
    
    def __init__(self, name: str, should_fail: bool = False, execution_time: float = 0.1):
        self.name = name
        self.description = f"Mock tool {name} for testing"
        self.should_fail = should_fail
        self.execution_time = execution_time
        
    def _run(self, *args, **kwargs):
        """Sync version - not used in our async system."""
        return self._execute(*args, **kwargs)
        
    async def _arun(self, *args, **kwargs):
        """Async version - this is what gets called."""
        await asyncio.sleep(self.execution_time)
        return self._execute(*args, **kwargs)
        
    def _execute(self, *args, **kwargs):
        """Core execution logic."""
        if self.should_fail:
            raise Exception(f"Mock tool {self.name} execution failed")
        return {
            "success": True,
            "tool_name": self.name,
            "result": f"Tool {self.name} executed successfully",
            "parameters": kwargs,
            "execution_timestamp": datetime.now(timezone.utc).isoformat()
        }


class TestToolDispatcherCoreBasicFunctionality(SSotBaseTestCase):
    """Test basic tool dispatcher functionality."""
    
    @pytest.mark.unit
    async def test_factory_creates_request_scoped_dispatcher(self):
        """Test factory method creates proper request-scoped dispatcher."""
        user_context = MockUserExecutionContext()
        websocket_manager = MockWebSocketManager()
        test_tools = [MockBaseTool("test_tool_1"), MockBaseTool("test_tool_2")]
        
        # Test the factory method that bypasses direct instantiation
        dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(
            user_context=user_context,
            tools=test_tools,
            websocket_manager=websocket_manager
        )
        
        # Verify dispatcher is properly configured
        assert dispatcher is not None
        assert hasattr(dispatcher, 'registry')
        assert hasattr(dispatcher, 'executor')
        assert hasattr(dispatcher, 'validator')
        
        # Verify WebSocket support is available
        assert dispatcher.has_websocket_support is True
        
        # Test tool registration worked
        assert dispatcher.has_tool("test_tool_1") is True
        assert dispatcher.has_tool("test_tool_2") is True
    
    @pytest.mark.unit
    def test_direct_instantiation_prevented_for_isolation(self):
        """Test that direct instantiation is prevented to ensure user isolation."""
        # CRITICAL: This test ensures that users cannot accidentally create global state
        # by directly instantiating ToolDispatcher
        with pytest.raises(RuntimeError) as exc_info:
            ToolDispatcher(tools=[])
            
        error_message = str(exc_info.value)
        assert "Direct ToolDispatcher instantiation is no longer supported" in error_message
        assert "create_request_scoped_dispatcher" in error_message
        assert "user isolation" in error_message
    
    @pytest.mark.unit
    async def test_tool_registration_in_isolated_instance(self):
        """Test dynamic tool registration in request-scoped instance."""
        user_context = MockUserExecutionContext()
        websocket_manager = MockWebSocketManager()
        
        # Create dispatcher without initial tools
        dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(
            user_context=user_context,
            websocket_manager=websocket_manager
        )
        
        # Verify no tools initially
        assert len(dispatcher.tools) == 0
        
        # Register a tool dynamically
        test_tool = MockBaseTool("dynamic_tool")
        dispatcher.register_tool("dynamic_tool", test_tool, "Test dynamic tool")
        
        # Verify tool is registered and available
        assert dispatcher.has_tool("dynamic_tool") is True
        assert "dynamic_tool" in dispatcher.tools
    
    @pytest.mark.unit
    async def test_error_handling_for_missing_tools(self):
        """Test proper error handling when dispatching non-existent tools."""
        user_context = MockUserExecutionContext()
        websocket_manager = MockWebSocketManager()
        
        dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(
            user_context=user_context,
            websocket_manager=websocket_manager
        )
        
        # Attempt to dispatch non-existent tool
        result = await dispatcher.dispatch("non_existent_tool", param1="value1")
        
        # Verify error handling
        assert isinstance(result, ToolResult)
        assert result.status == ToolStatus.ERROR
        assert "Tool non_existent_tool not found" in result.message
        assert result.tool_input.tool_name == "non_existent_tool"
    
    @pytest.mark.unit
    async def test_websocket_bridge_management(self):
        """Test WebSocket bridge management for event delivery."""
        user_context = MockUserExecutionContext()
        websocket_manager1 = MockWebSocketManager()
        websocket_manager2 = MockWebSocketManager()
        
        # Create dispatcher with initial WebSocket manager
        dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(
            user_context=user_context,
            websocket_manager=websocket_manager1
        )
        
        # Verify initial WebSocket bridge is set
        assert dispatcher.has_websocket_support is True
        initial_bridge = dispatcher.get_websocket_bridge()
        assert initial_bridge is not None
        
        # Update WebSocket bridge to different manager
        dispatcher.set_websocket_bridge(websocket_manager2)
        
        # Verify bridge was updated
        updated_bridge = dispatcher.get_websocket_bridge()
        assert updated_bridge is not None
        # Note: The bridge wraps the manager, so we can't directly compare managers
        
        # Test setting bridge to None
        dispatcher.set_websocket_bridge(None)
        none_bridge = dispatcher.get_websocket_bridge()
        assert none_bridge is None
        assert dispatcher.has_websocket_support is False


class TestToolDispatcherCoreToolExecutionLifecycle(SSotBaseTestCase):
    """Test tool execution lifecycle management."""
    
    @pytest.mark.unit
    async def test_successful_tool_dispatch_basic_flow(self):
        """Test successful tool dispatch with basic parameters."""
        user_context = MockUserExecutionContext()
        websocket_manager = MockWebSocketManager()
        test_tool = MockBaseTool("success_tool")
        
        dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(
            user_context=user_context,
            tools=[test_tool],
            websocket_manager=websocket_manager
        )
        
        # Dispatch tool with parameters
        result = await dispatcher.dispatch("success_tool", param1="value1", param2=42)
        
        # Verify successful execution
        assert isinstance(result, ToolResult)
        assert result.status == ToolStatus.SUCCESS
        assert result.tool_input.tool_name == "success_tool"
        
        # Verify WebSocket events were sent
        assert len(websocket_manager.events_sent) >= 2  # At least executing and completed
        event_types = [event["type"] for event in websocket_manager.events_sent]
        assert "tool_executing" in event_types
        assert "tool_completed" in event_types
    
    @pytest.mark.unit
    async def test_tool_dispatch_with_state_and_run_id(self):
        """Test tool dispatch with agent state and run ID tracking."""
        user_context = MockUserExecutionContext()
        websocket_manager = MockWebSocketManager()
        test_tool = MockBaseTool("stateful_tool")
        
        dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(
            user_context=user_context,
            tools=[test_tool],
            websocket_manager=websocket_manager
        )
        
        # Create test state and run ID
        test_state = DeepAgentState(user_request="Test user request")
        run_id = "test-run-123"
        
        # Dispatch tool with state
        response = await dispatcher.dispatch_tool(
            tool_name="stateful_tool",
            parameters={"param": "value"},
            state=test_state,
            run_id=run_id
        )
        
        # Verify successful response
        assert isinstance(response, ToolDispatchResponse)
        assert response.success is True
        assert response.result is not None
        assert response.error is None
        
        # Verify metadata contains run information
        assert "run_id" in response.metadata or run_id in str(response.metadata)
    
    @pytest.mark.unit
    async def test_tool_execution_error_handling(self):
        """Test proper error handling during tool execution."""
        user_context = MockUserExecutionContext()
        websocket_manager = MockWebSocketManager()
        failing_tool = MockBaseTool("failing_tool", should_fail=True)
        
        dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(
            user_context=user_context,
            tools=[failing_tool],
            websocket_manager=websocket_manager
        )
        
        # Dispatch failing tool
        result = await dispatcher.dispatch("failing_tool", param="value")
        
        # Verify error is handled gracefully
        assert isinstance(result, ToolResult)
        assert result.status == ToolStatus.ERROR
        assert "execution failed" in result.message.lower()
        
        # Verify WebSocket events were still sent (important for user feedback)
        assert len(websocket_manager.events_sent) >= 1  # At least tool_executing
        event_types = [event["type"] for event in websocket_manager.events_sent]
        assert "tool_executing" in event_types
    
    @pytest.mark.unit
    async def test_multiple_tool_executions_in_sequence(self):
        """Test multiple sequential tool executions maintain isolation."""
        user_context = MockUserExecutionContext()
        websocket_manager = MockWebSocketManager()
        tools = [
            MockBaseTool("tool_1", execution_time=0.05),
            MockBaseTool("tool_2", execution_time=0.05),
            MockBaseTool("tool_3", execution_time=0.05)
        ]
        
        dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(
            user_context=user_context,
            tools=tools,
            websocket_manager=websocket_manager
        )
        
        # Execute tools in sequence
        results = []
        for i in range(1, 4):
            result = await dispatcher.dispatch(f"tool_{i}", execution_order=i)
            results.append(result)
        
        # Verify all executions succeeded
        for i, result in enumerate(results, 1):
            assert isinstance(result, ToolResult)
            assert result.status == ToolStatus.SUCCESS
            assert result.tool_input.tool_name == f"tool_{i}"
        
        # Verify all WebSocket events were sent (should be 6+ events: 3 executing + 3 completed)
        assert len(websocket_manager.events_sent) >= 6
        executing_events = [e for e in websocket_manager.events_sent if e["type"] == "tool_executing"]
        completed_events = [e for e in websocket_manager.events_sent if e["type"] == "tool_completed"]
        assert len(executing_events) == 3
        assert len(completed_events) == 3
    
    @pytest.mark.unit
    async def test_concurrent_tool_execution_safety(self):
        """Test that concurrent tool executions don't interfere with each other."""
        user_context = MockUserExecutionContext()
        websocket_manager = MockWebSocketManager()
        tools = [MockBaseTool(f"concurrent_tool_{i}", execution_time=0.1) for i in range(1, 4)]
        
        dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(
            user_context=user_context,
            tools=tools,
            websocket_manager=websocket_manager
        )
        
        # Start concurrent tool executions
        tasks = [
            dispatcher.dispatch(f"concurrent_tool_{i}", task_id=i)
            for i in range(1, 4)
        ]
        
        # Wait for all to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all succeeded
        for i, result in enumerate(results, 1):
            assert not isinstance(result, Exception), f"Task {i} failed: {result}"
            assert isinstance(result, ToolResult)
            assert result.status == ToolStatus.SUCCESS
            assert result.tool_input.tool_name == f"concurrent_tool_{i}"
        
        # Verify proper number of WebSocket events (6 total: 3 executing + 3 completed)
        assert len(websocket_manager.events_sent) >= 6


class TestToolDispatcherCoreStateAndValidation(SSotBaseTestCase):
    """Test state management and validation in tool dispatcher."""
    
    @pytest.mark.unit
    async def test_websocket_diagnostics_functionality(self):
        """Test WebSocket diagnostics for debugging silent failures."""
        user_context = MockUserExecutionContext()
        websocket_manager = MockWebSocketManager()
        
        dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(
            user_context=user_context,
            websocket_manager=websocket_manager
        )
        
        # Get diagnostics
        diagnosis = dispatcher.diagnose_websocket_wiring()
        
        # Verify diagnostic information
        assert isinstance(diagnosis, dict)
        assert "dispatcher_has_executor" in diagnosis
        assert "executor_type" in diagnosis
        assert "executor_has_websocket_bridge_attr" in diagnosis
        assert "websocket_bridge_is_none" in diagnosis
        assert "websocket_bridge_type" in diagnosis
        assert "has_websocket_support" in diagnosis
        assert "critical_issues" in diagnosis
        
        # Verify positive state
        assert diagnosis["dispatcher_has_executor"] is True
        assert diagnosis["executor_type"] is not None
        assert diagnosis["has_websocket_support"] is True
        assert len(diagnosis["critical_issues"]) == 0  # No issues with proper setup
    
    @pytest.mark.unit 
    async def test_websocket_diagnostics_detects_missing_bridge(self):
        """Test WebSocket diagnostics detects missing bridge configuration."""
        user_context = MockUserExecutionContext()
        
        # Create dispatcher without WebSocket manager
        dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(
            user_context=user_context,
            websocket_manager=None
        )
        
        # Get diagnostics
        diagnosis = dispatcher.diagnose_websocket_wiring()
        
        # Verify it detects the missing bridge
        assert diagnosis["websocket_bridge_is_none"] is True
        assert diagnosis["has_websocket_support"] is False
        assert len(diagnosis["critical_issues"]) > 0
        assert any("WebSocket bridge is None" in issue for issue in diagnosis["critical_issues"])
    
    @pytest.mark.unit
    async def test_scoped_dispatcher_context_manager(self):
        """Test scoped dispatcher context manager for automatic cleanup."""
        user_context = MockUserExecutionContext()
        websocket_manager = MockWebSocketManager()
        test_tool = MockBaseTool("context_tool")
        
        # Use context manager
        async with ToolDispatcher.create_scoped_dispatcher_context(
            user_context=user_context,
            tools=[test_tool],
            websocket_manager=websocket_manager
        ) as dispatcher:
            # Verify dispatcher is available
            assert dispatcher is not None
            assert dispatcher.has_tool("context_tool") is True
            
            # Execute tool within context
            result = await dispatcher.dispatch("context_tool", param="test")
            assert result.status == ToolStatus.SUCCESS
            
            # Verify WebSocket events
            assert len(websocket_manager.events_sent) >= 2
        
        # After context exit, dispatcher should still be valid for verification
        # (cleanup is handled internally but instance remains accessible for testing)
        diagnosis = dispatcher.diagnose_websocket_wiring()
        assert isinstance(diagnosis, dict)  # Basic verification it's still accessible
    
    @pytest.mark.unit
    async def test_tool_input_creation_and_validation(self):
        """Test tool input creation and validation logic."""
        user_context = MockUserExecutionContext()
        websocket_manager = MockWebSocketManager()
        test_tool = MockBaseTool("validation_tool")
        
        dispatcher = await ToolDispatcher.create_request_scoped_dispatcher(
            user_context=user_context,
            tools=[test_tool],
            websocket_manager=websocket_manager
        )
        
        # Test tool input creation internal method
        tool_input = dispatcher._create_tool_input("validation_tool", {"param1": "value1", "param2": 42})
        
        # Verify tool input structure
        assert isinstance(tool_input, ToolInput)
        assert tool_input.tool_name == "validation_tool"
        assert tool_input.kwargs == {"param1": "value1", "param2": 42}
        
        # Test error result creation
        error_result = dispatcher._create_error_result(tool_input, "Test error message")
        
        # Verify error result structure
        assert isinstance(error_result, ToolResult)
        assert error_result.status == ToolStatus.ERROR
        assert error_result.message == "Test error message"
        assert error_result.tool_input == tool_input