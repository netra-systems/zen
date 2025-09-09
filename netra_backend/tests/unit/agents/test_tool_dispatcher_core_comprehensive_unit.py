"""
Comprehensive Unit Tests for ToolDispatcher Core

Tests the core tool dispatcher functionality focusing on request-scoped architecture,
tool registration, dispatch logic, WebSocket integration, and security patterns.

CRITICAL REQUIREMENTS from CLAUDE.md:
1. Uses absolute imports 
2. Follows SSOT patterns from test_framework/ssot/
3. Uses StronglyTypedUserExecutionContext and proper type safety
4. Tests MUST RAISE ERRORS (no try/except blocks that hide failures)
5. Focuses on individual methods/functions in isolation

Business Value: Platform/Internal - System Stability & Development Velocity
Ensures the core tool dispatch system works correctly with proper user isolation.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from typing import List, Dict, Any, Optional
from uuid import uuid4

from langchain_core.tools import BaseTool
from pydantic import BaseModel

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID

from netra_backend.app.agents.tool_dispatcher_core import (
    ToolDispatcher, 
    ToolDispatchRequest, 
    ToolDispatchResponse
)
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.schemas.tool import ToolInput, ToolResult, ToolStatus


class MockTool(BaseTool):
    """Mock tool for testing purposes."""
    name: str = "mock_tool"
    description: str = "A mock tool for testing"
    
    def _run(self, *args, **kwargs):
        return {"success": True, "result": "mock_result"}
    
    async def _arun(self, *args, **kwargs):
        return {"success": True, "result": "mock_async_result"}


class MockAsyncTool(BaseTool):
    """Mock async tool for testing purposes."""
    name: str = "mock_async_tool"
    description: str = "A mock async tool for testing"
    
    def _run(self, *args, **kwargs):
        return {"success": True, "result": "mock_sync_result"}
    
    async def _arun(self, *args, **kwargs):
        return {"success": True, "result": "mock_async_result"}


class TestToolDispatcherCoreUnit(SSotBaseTestCase):
    """Comprehensive unit tests for ToolDispatcher core functionality."""

    @pytest.fixture
    def mock_websocket_bridge(self):
        """Mock AgentWebSocketBridge for WebSocket integration."""
        bridge = AsyncMock()
        bridge.notify_tool_executing = AsyncMock()
        bridge.notify_tool_completed = AsyncMock()
        bridge.notify_tool_error = AsyncMock()
        return bridge

    @pytest.fixture
    def mock_user_context(self):
        """Mock strongly typed user execution context."""
        return StronglyTypedUserExecutionContext(
            user_id=UserID("test-user-123"),
            thread_id=ThreadID("test-thread-456"),
            run_id=RunID(str(uuid4())),
            request_id=RequestID(str(uuid4())),
            websocket_client_id=WebSocketID("ws-client-789")
        )

    @pytest.fixture
    def sample_tools(self):
        """Sample tools for testing."""
        return [MockTool(), MockAsyncTool()]

    def test_init_prevents_direct_instantiation(self):
        """Test that direct instantiation is prevented for security."""
        with pytest.raises(RuntimeError) as exc_info:
            ToolDispatcher()
        
        error_msg = str(exc_info.value)
        assert "Direct ToolDispatcher instantiation is no longer supported" in error_msg
        assert "create_request_scoped_dispatcher" in error_msg
        assert "proper user isolation" in error_msg

    def test_init_from_factory_creates_proper_components(self, mock_websocket_bridge, sample_tools):
        """Test factory initialization creates proper components."""
        # Use the internal factory method
        dispatcher = ToolDispatcher._init_from_factory(sample_tools, mock_websocket_bridge)
        
        # Verify components are initialized
        assert hasattr(dispatcher, 'registry')
        assert hasattr(dispatcher, 'executor')
        assert hasattr(dispatcher, 'validator')
        
        # Verify tools were registered
        assert dispatcher.has_tool("mock_tool")
        assert dispatcher.has_tool("mock_async_tool")
        
        # Verify executor has WebSocket bridge
        assert hasattr(dispatcher.executor, 'websocket_bridge')
        assert dispatcher.executor.websocket_bridge == mock_websocket_bridge

    def test_tools_property_exposes_registry(self, mock_websocket_bridge, sample_tools):
        """Test tools property exposes the registry correctly."""
        dispatcher = ToolDispatcher._init_from_factory(sample_tools, mock_websocket_bridge)
        
        tools_dict = dispatcher.tools
        
        # Verify tools are accessible
        assert isinstance(tools_dict, dict)
        assert "mock_tool" in tools_dict
        assert "mock_async_tool" in tools_dict

    def test_has_websocket_support_property(self, mock_websocket_bridge, sample_tools):
        """Test has_websocket_support property logic."""
        # Test with WebSocket bridge
        dispatcher_with_ws = ToolDispatcher._init_from_factory(sample_tools, mock_websocket_bridge)
        assert dispatcher_with_ws.has_websocket_support is True
        
        # Test without WebSocket bridge
        dispatcher_without_ws = ToolDispatcher._init_from_factory(sample_tools, None)
        assert dispatcher_without_ws.has_websocket_support is False

    def test_has_tool_checks_registry(self, mock_websocket_bridge, sample_tools):
        """Test has_tool method checks registry correctly."""
        dispatcher = ToolDispatcher._init_from_factory(sample_tools, mock_websocket_bridge)
        
        # Test existing tools
        assert dispatcher.has_tool("mock_tool") is True
        assert dispatcher.has_tool("mock_async_tool") is True
        
        # Test non-existing tool
        assert dispatcher.has_tool("nonexistent_tool") is False

    def test_register_tool_with_basetool(self, mock_websocket_bridge):
        """Test registering a tool that's already a BaseTool."""
        dispatcher = ToolDispatcher._init_from_factory([], mock_websocket_bridge)
        new_tool = MockTool()
        
        dispatcher.register_tool("new_mock_tool", new_tool, "A new mock tool")
        
        # Verify tool was registered
        assert dispatcher.has_tool("new_mock_tool") is True

    def test_register_tool_with_function_creates_wrapper(self, mock_websocket_bridge):
        """Test registering a function creates proper BaseTool wrapper."""
        dispatcher = ToolDispatcher._init_from_factory([], mock_websocket_bridge)
        
        def test_function(param1: str, param2: int = 5):
            return f"Result: {param1} + {param2}"
        
        dispatcher.register_tool("test_func", test_function, "Test function tool")
        
        # Verify tool was registered
        assert dispatcher.has_tool("test_func") is True
        
        # Verify the tool in registry is a BaseTool
        tool = dispatcher.registry.get_tool("test_func")
        assert isinstance(tool, BaseTool)
        assert tool.name == "test_func"
        assert tool.description == "Test function tool"

    def test_register_tool_with_async_function(self, mock_websocket_bridge):
        """Test registering an async function creates proper wrapper."""
        dispatcher = ToolDispatcher._init_from_factory([], mock_websocket_bridge)
        
        async def async_test_function(data: str):
            return f"Async result: {data}"
        
        dispatcher.register_tool("async_func", async_test_function, "Async test function")
        
        # Verify tool was registered
        assert dispatcher.has_tool("async_func") is True
        
        # Verify the tool in registry is a BaseTool
        tool = dispatcher.registry.get_tool("async_func")
        assert isinstance(tool, BaseTool)
        assert tool.name == "async_func"

    @pytest.mark.asyncio
    async def test_dispatch_successful_tool_execution(self, mock_websocket_bridge, sample_tools):
        """Test successful tool dispatch and execution."""
        dispatcher = ToolDispatcher._init_from_factory(sample_tools, mock_websocket_bridge)
        
        # Mock the executor
        mock_result = ToolResult(
            tool_input=ToolInput(tool_name="mock_tool", kwargs={"param": "value"}),
            status=ToolStatus.SUCCESS,
            result={"success": True, "data": "test_result"}
        )
        dispatcher.executor.execute_tool_with_input = AsyncMock(return_value=mock_result)
        
        # Dispatch tool
        result = await dispatcher.dispatch("mock_tool", param="value")
        
        # Verify result
        assert isinstance(result, ToolResult)
        assert result.status == ToolStatus.SUCCESS
        assert result.result["success"] is True
        
        # Verify executor was called
        dispatcher.executor.execute_tool_with_input.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_tool_not_found(self, mock_websocket_bridge, sample_tools):
        """Test dispatch behavior when tool is not found."""
        dispatcher = ToolDispatcher._init_from_factory(sample_tools, mock_websocket_bridge)
        
        # Dispatch non-existent tool
        result = await dispatcher.dispatch("nonexistent_tool", param="value")
        
        # Verify error result
        assert isinstance(result, ToolResult)
        assert result.status == ToolStatus.ERROR
        assert "not found" in result.message.lower()

    @pytest.mark.asyncio
    async def test_dispatch_tool_with_state(self, mock_websocket_bridge, sample_tools):
        """Test dispatch_tool method with state and run_id."""
        dispatcher = ToolDispatcher._init_from_factory(sample_tools, mock_websocket_bridge)
        
        # Mock state and executor
        mock_state = Mock(spec=DeepAgentState)
        mock_state.user_id = UserID("test-user")
        mock_state.thread_id = ThreadID("test-thread")
        
        mock_response = ToolDispatchResponse(
            success=True,
            result={"data": "success"},
            metadata={"execution_time": 1.5}
        )
        dispatcher.executor.execute_with_state = AsyncMock(return_value=mock_response)
        
        # Dispatch tool
        response = await dispatcher.dispatch_tool(
            tool_name="mock_tool",
            parameters={"param1": "value1"},
            state=mock_state,
            run_id="test-run-123"
        )
        
        # Verify response
        assert isinstance(response, ToolDispatchResponse)
        assert response.success is True
        assert response.result["data"] == "success"
        
        # Verify executor was called correctly
        dispatcher.executor.execute_with_state.assert_called_once()
        call_args = dispatcher.executor.execute_with_state.call_args
        assert call_args[0][1] == "mock_tool"  # tool_name
        assert call_args[0][2] == {"param1": "value1"}  # parameters
        assert call_args[0][3] == mock_state  # state
        assert call_args[0][4] == "test-run-123"  # run_id

    @pytest.mark.asyncio
    async def test_dispatch_tool_not_found_error(self, mock_websocket_bridge, sample_tools):
        """Test dispatch_tool error handling for missing tool."""
        dispatcher = ToolDispatcher._init_from_factory(sample_tools, mock_websocket_bridge)
        
        mock_state = Mock(spec=DeepAgentState)
        
        # Dispatch non-existent tool
        response = await dispatcher.dispatch_tool(
            tool_name="missing_tool",
            parameters={"param": "value"},
            state=mock_state,
            run_id="test-run-123"
        )
        
        # Verify error response
        assert isinstance(response, ToolDispatchResponse)
        assert response.success is False
        assert "not found" in response.error.lower()

    def test_set_websocket_bridge_updates_executor(self, mock_websocket_bridge, sample_tools):
        """Test WebSocket bridge can be updated after initialization."""
        dispatcher = ToolDispatcher._init_from_factory(sample_tools, None)
        
        # Initially no bridge
        assert dispatcher.get_websocket_bridge() is None
        
        # Set bridge
        dispatcher.set_websocket_bridge(mock_websocket_bridge)
        
        # Verify bridge was set
        assert dispatcher.get_websocket_bridge() == mock_websocket_bridge
        assert dispatcher.executor.websocket_bridge == mock_websocket_bridge

    def test_set_websocket_bridge_to_none(self, mock_websocket_bridge, sample_tools):
        """Test setting WebSocket bridge to None."""
        dispatcher = ToolDispatcher._init_from_factory(sample_tools, mock_websocket_bridge)
        
        # Initially has bridge
        assert dispatcher.get_websocket_bridge() == mock_websocket_bridge
        
        # Set to None
        dispatcher.set_websocket_bridge(None)
        
        # Verify bridge was cleared
        assert dispatcher.get_websocket_bridge() is None
        assert dispatcher.executor.websocket_bridge is None

    def test_diagnose_websocket_wiring_comprehensive(self, mock_websocket_bridge, sample_tools):
        """Test comprehensive WebSocket wiring diagnosis."""
        dispatcher = ToolDispatcher._init_from_factory(sample_tools, mock_websocket_bridge)
        
        diagnosis = dispatcher.diagnose_websocket_wiring()
        
        # Verify diagnosis structure
        assert isinstance(diagnosis, dict)
        required_keys = [
            "dispatcher_has_executor", "executor_type", "executor_has_websocket_bridge_attr",
            "websocket_bridge_is_none", "websocket_bridge_type", "has_websocket_support",
            "critical_issues"
        ]
        for key in required_keys:
            assert key in diagnosis
        
        # Verify positive diagnosis
        assert diagnosis["dispatcher_has_executor"] is True
        assert "UnifiedToolExecutionEngine" in diagnosis["executor_type"]
        assert diagnosis["executor_has_websocket_bridge_attr"] is True
        assert diagnosis["websocket_bridge_is_none"] is False
        assert diagnosis["websocket_bridge_type"] is not None
        assert diagnosis["has_websocket_support"] is True
        assert len(diagnosis["critical_issues"]) == 0

    def test_diagnose_websocket_wiring_missing_bridge(self, sample_tools):
        """Test WebSocket wiring diagnosis when bridge is missing."""
        dispatcher = ToolDispatcher._init_from_factory(sample_tools, None)
        
        diagnosis = dispatcher.diagnose_websocket_wiring()
        
        # Verify negative diagnosis
        assert diagnosis["websocket_bridge_is_none"] is True
        assert diagnosis["websocket_bridge_type"] is None
        assert diagnosis["has_websocket_support"] is False
        assert len(diagnosis["critical_issues"]) > 0
        assert "WebSocket bridge is None" in diagnosis["critical_issues"][0]

    def test_create_tool_input_structure(self, mock_websocket_bridge, sample_tools):
        """Test _create_tool_input creates proper structure."""
        dispatcher = ToolDispatcher._init_from_factory(sample_tools, mock_websocket_bridge)
        
        kwargs = {"param1": "value1", "param2": 42}
        tool_input = dispatcher._create_tool_input("test_tool", kwargs)
        
        # Verify structure
        assert isinstance(tool_input, ToolInput)
        assert tool_input.tool_name == "test_tool"
        assert tool_input.kwargs == kwargs

    def test_create_error_result_structure(self, mock_websocket_bridge, sample_tools):
        """Test _create_error_result creates proper error structure."""
        dispatcher = ToolDispatcher._init_from_factory(sample_tools, mock_websocket_bridge)
        
        tool_input = ToolInput(tool_name="test_tool", kwargs={})
        error_result = dispatcher._create_error_result(tool_input, "Test error message")
        
        # Verify error structure
        assert isinstance(error_result, ToolResult)
        assert error_result.tool_input == tool_input
        assert error_result.status == ToolStatus.ERROR
        assert error_result.message == "Test error message"

    def test_create_tool_not_found_response(self, mock_websocket_bridge, sample_tools):
        """Test _create_tool_not_found_response creates proper response."""
        dispatcher = ToolDispatcher._init_from_factory(sample_tools, mock_websocket_bridge)
        
        response = dispatcher._create_tool_not_found_response("missing_tool", "run-123")
        
        # Verify response structure
        assert isinstance(response, ToolDispatchResponse)
        assert response.success is False
        assert "missing_tool" in response.error
        assert "not found" in response.error.lower()

    @pytest.mark.asyncio
    async def test_execute_tool_delegates_to_executor(self, mock_websocket_bridge, sample_tools):
        """Test _execute_tool properly delegates to executor."""
        dispatcher = ToolDispatcher._init_from_factory(sample_tools, mock_websocket_bridge)
        
        tool_input = ToolInput(tool_name="mock_tool", kwargs={"param": "value"})
        tool = MockTool()
        kwargs = {"param": "value"}
        
        mock_result = ToolResult(
            tool_input=tool_input,
            status=ToolStatus.SUCCESS,
            result={"success": True}
        )
        dispatcher.executor.execute_tool_with_input = AsyncMock(return_value=mock_result)
        
        # Execute tool
        result = await dispatcher._execute_tool(tool_input, tool, kwargs)
        
        # Verify delegation
        assert result == mock_result
        dispatcher.executor.execute_tool_with_input.assert_called_once_with(tool_input, tool, kwargs)

    def test_tool_dispatch_request_model(self):
        """Test ToolDispatchRequest pydantic model."""
        request = ToolDispatchRequest(
            tool_name="test_tool",
            parameters={"param1": "value1", "param2": 42}
        )
        
        # Verify model structure
        assert request.tool_name == "test_tool"
        assert request.parameters == {"param1": "value1", "param2": 42}

    def test_tool_dispatch_request_default_parameters(self):
        """Test ToolDispatchRequest with default parameters."""
        request = ToolDispatchRequest(tool_name="test_tool")
        
        # Verify default parameters
        assert request.tool_name == "test_tool"
        assert request.parameters == {}

    def test_tool_dispatch_response_model(self):
        """Test ToolDispatchResponse pydantic model."""
        response = ToolDispatchResponse(
            success=True,
            result={"data": "test_result"},
            error=None,
            metadata={"execution_time": 1.5}
        )
        
        # Verify model structure
        assert response.success is True
        assert response.result["data"] == "test_result"
        assert response.error is None
        assert response.metadata["execution_time"] == 1.5

    def test_tool_dispatch_response_default_fields(self):
        """Test ToolDispatchResponse with default field values."""
        response = ToolDispatchResponse(success=False)
        
        # Verify defaults
        assert response.success is False
        assert response.result is None
        assert response.error is None
        assert response.metadata == {}