"""Unit tests for ToolDispatcher core operations."""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import pytest
from netra_backend.app.schemas import ToolInput

from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.tests.helpers.tool_dispatcher_helpers import (
    create_mock_tool,
    create_tool_input,
    verify_tool_result_error,
    verify_tool_result_success,
)

class TestToolDispatcherCoreOperations:
    """Test core dispatcher operations."""
    
    def test_has_tool(self):
        """Test has_tool method."""
        dispatcher = ToolDispatcher()
        self._verify_existing_tool_found(dispatcher)
        self._verify_nonexistent_tool_not_found(dispatcher)
    @pytest.mark.asyncio
    async def test_dispatch_success(self):
        """Test successful tool dispatch."""
        tool, dispatcher = self._setup_successful_dispatch()
        result = await dispatcher.dispatch("test_tool", param1="value1", param2="value2")
        self._verify_successful_dispatch_result(result)
    @pytest.mark.asyncio
    async def test_dispatch_tool_not_found(self):
        """Test dispatch with non-existent tool."""
        dispatcher = ToolDispatcher()
        result = await dispatcher.dispatch("nonexistent_tool", param="value")
        verify_tool_result_error(result, "Tool nonexistent_tool not found")
    @pytest.mark.asyncio
    async def test_dispatch_tool_failure(self):
        """Test dispatch with failing tool."""
        failing_tool, dispatcher = self._setup_failing_dispatch()
        result = await dispatcher.dispatch("failing_tool", param="value")
        verify_tool_result_error(result, "Tool failing_tool failed")
    
    def test_create_error_result(self):
        """Test _create_error_result method."""
        dispatcher = ToolDispatcher()
        tool_input, error_message = self._setup_error_result_test()
        result = dispatcher._create_error_result(tool_input, error_message)
        self._verify_error_result(result, tool_input, error_message)
    @pytest.mark.asyncio
    async def test_execute_tool_success(self):
        """Test _execute_tool method with success."""
        dispatcher, tool, tool_input, kwargs = self._setup_execute_tool_test()
        result = await dispatcher._execute_tool(tool_input, tool, kwargs)
        self._verify_execute_tool_success(result)
    @pytest.mark.asyncio
    async def test_execute_tool_failure(self):
        """Test _execute_tool method with failure."""
        dispatcher, failing_tool, tool_input = self._setup_execute_tool_failure_test()
        result = await dispatcher._execute_tool(tool_input, failing_tool, {})
        verify_tool_result_error(result, "Tool failing_tool failed")
    
    def _verify_existing_tool_found(self, dispatcher: ToolDispatcher) -> None:
        """Verify existing tool is found."""
        assert dispatcher.has_tool("create_corpus") is True
    
    def _verify_nonexistent_tool_not_found(self, dispatcher: ToolDispatcher) -> None:
        """Verify non-existing tool is not found."""
        assert dispatcher.has_tool("nonexistent_tool") is False
    
    def _setup_successful_dispatch(self) -> tuple:
        """Setup successful dispatch test."""
        tool = create_mock_tool("test_tool")
        dispatcher = ToolDispatcher([tool])
        return tool, dispatcher
    
    def _verify_successful_dispatch_result(self, result) -> None:
        """Verify successful dispatch result."""
        verify_tool_result_success(result, "test_tool")
        assert result.tool_input.kwargs == {"param1": "value1", "param2": "value2"}
    
    def _setup_failing_dispatch(self) -> tuple:
        """Setup failing dispatch test."""
        failing_tool = create_mock_tool("failing_tool", should_fail=True)
        dispatcher = ToolDispatcher([failing_tool])
        return failing_tool, dispatcher
    
    def _setup_error_result_test(self) -> tuple:
        """Setup error result test."""
        tool_input = create_tool_input("test_tool", param="value")
        error_message = "Test error message"
        return tool_input, error_message
    
    def _verify_error_result(self, result, tool_input: ToolInput, error_message: str) -> None:
        """Verify error result format."""
        verify_tool_result_error(result, error_message)
        assert result.tool_input == tool_input
    
    def _setup_execute_tool_test(self) -> tuple:
        """Setup execute tool test."""
        dispatcher = ToolDispatcher()
        tool = create_mock_tool("test_tool")
        tool_input = create_tool_input("test_tool", param="value")
        kwargs = {"param": "value"}
        return dispatcher, tool, tool_input, kwargs
    
    def _verify_execute_tool_success(self, result) -> None:
        """Verify execute tool success result."""
        verify_tool_result_success(result, "test_tool")
        from netra_backend.tests.tool_dispatcher_assertions import (
            assert_simple_tool_payload,
        )
        assert_simple_tool_payload(result)
    
    def _setup_execute_tool_failure_test(self) -> tuple:
        """Setup execute tool failure test."""
        dispatcher = ToolDispatcher()
        failing_tool = create_mock_tool("failing_tool", should_fail=True)
        tool_input = create_tool_input("failing_tool")
        return dispatcher, failing_tool, tool_input