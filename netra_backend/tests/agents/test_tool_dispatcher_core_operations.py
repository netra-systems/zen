"""Unit tests for ToolDispatcher core operations."""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

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
        # Mock: Component isolation for testing without external dependencies
        tool, dispatcher = self._setup_successful_dispatch()
        # Mock: Component isolation for testing without external dependencies
        result = await dispatcher.dispatch("test_tool", param1="value1", param2="value2")
        
        # Fixed: Verify ToolResult directly instead of using helper
        from netra_backend.app.schemas.tool import ToolResult, ToolStatus
        assert isinstance(result, ToolResult)
        assert result.status == ToolStatus.SUCCESS
        assert result.tool_input.tool_name == "test_tool"
        assert result.tool_input.kwargs == {"param1": "value1", "param2": "value2"}
    @pytest.mark.asyncio
    async def test_dispatch_tool_not_found(self):
        """Test dispatch with non-existent tool."""
        dispatcher = ToolDispatcher()
        # Mock: Component isolation for testing without external dependencies
        result = await dispatcher.dispatch("nonexistent_tool", param="value")
        
        # Direct assertion instead of helper function to avoid type issues
        assert hasattr(result, 'status'), f"Result should have status attribute, got: {type(result)}"
        assert result.status.value == 'error', f"Status should be error, got: {result.status}"
        assert "Tool nonexistent_tool not found" in str(result.message), f"Message should contain error, got: {result.message}"
    @pytest.mark.asyncio
    async def test_dispatch_tool_failure(self):
        """Test dispatch with failing tool."""
        # Mock: Component isolation for testing without external dependencies
        failing_tool, dispatcher = self._setup_failing_dispatch()
        # Mock: Component isolation for testing without external dependencies
        result = await dispatcher.dispatch("failing_tool", param="value")
        
        # Direct assertion instead of helper function to avoid type issues
        assert hasattr(result, 'status'), f"Result should have status attribute, got: {type(result)}"
        assert result.status.value == 'error', f"Status should be error, got: {result.status}"
        assert "Tool failing_tool failed" in str(result.message), f"Message should contain error, got: {result.message}"
    
    def test_create_error_result(self):
        """Test _create_error_result method."""
        dispatcher = ToolDispatcher()
        tool_input, error_message = self._setup_error_result_test()
        result = dispatcher._create_error_result(tool_input, error_message)
        
        # Direct assertion instead of helper function
        assert hasattr(result, 'status'), f"Result should have status attribute, got: {type(result)}"
        assert result.status.value == 'error', f"Status should be error, got: {result.status}"
        assert error_message in str(result.message), f"Message should contain error, got: {result.message}"
        assert result.tool_input == tool_input
    @pytest.mark.asyncio
    async def test_execute_tool_success(self):
        """Test _execute_tool method with success."""
        dispatcher, tool, tool_input, kwargs = self._setup_execute_tool_test()
        result = await dispatcher.executor.execute_tool_with_input(tool_input, tool, kwargs)
        
        # Direct assertion for success
        assert hasattr(result, 'status'), f"Result should have status attribute, got: {type(result)}"
        assert result.status.value == 'success', f"Status should be success, got: {result.status}"
        assert result.tool_input.tool_name == "test_tool"
    @pytest.mark.asyncio
    async def test_execute_tool_failure(self):
        """Test _execute_tool method with failure."""
        dispatcher, failing_tool, tool_input = self._setup_execute_tool_failure_test()
        result = await dispatcher.executor.execute_tool_with_input(tool_input, failing_tool, {})
        
        # Direct assertion for failure
        assert hasattr(result, 'status'), f"Result should have status attribute, got: {type(result)}"
        assert result.status.value == 'error', f"Status should be error, got: {result.status}"
        assert "Tool failing_tool failed" in str(result.message), f"Message should contain error, got: {result.message}"
    
    def _verify_existing_tool_found(self, dispatcher: ToolDispatcher) -> None:
        """Verify existing tool is found."""
        assert dispatcher.has_tool("create_corpus") is True
    
    def _verify_nonexistent_tool_not_found(self, dispatcher: ToolDispatcher) -> None:
        """Verify non-existing tool is not found."""
        assert dispatcher.has_tool("nonexistent_tool") is False
    
    # Mock: Component isolation for testing without external dependencies
    def _setup_successful_dispatch(self) -> tuple:
        """Setup successful dispatch test."""
        tool = create_mock_tool("test_tool")
        dispatcher = ToolDispatcher([tool])
        return tool, dispatcher
    
    def _verify_successful_dispatch_result(self, result) -> None:
        """Verify successful dispatch result."""
        # Fixed: Direct verification without helper function
        from netra_backend.app.schemas.tool import ToolResult, ToolStatus
        assert isinstance(result, ToolResult)
        assert result.status == ToolStatus.SUCCESS
        assert result.tool_input.tool_name == "test_tool"
    
    # Mock: Component isolation for testing without external dependencies
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
    
    @pytest.mark.asyncio
    async def test_concurrent_tool_dispatch(self):
        """Test concurrent tool dispatch operations."""
        import asyncio
        # Create multiple tools for concurrent testing
        tools = [create_mock_tool(f"tool_{i}") for i in range(5)]
        dispatcher = ToolDispatcher(tools)
        
        # Create concurrent dispatch tasks
        tasks = [
            dispatcher.dispatch(f"tool_{i}", param=f"value_{i}")
            for i in range(5)
        ]
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)
        
        # Verify all results are successful and contain correct data
        from netra_backend.app.schemas.tool import ToolResult, ToolStatus
        for i, result in enumerate(results):
            assert isinstance(result, ToolResult)
            assert result.status == ToolStatus.SUCCESS
            assert result.tool_input.tool_name == f"tool_{i}"
            assert result.tool_input.kwargs == {"param": f"value_{i}"}
            # Verify tool execution actually occurred
            assert result.payload is not None
            assert "result" in result.payload.result
    
    @pytest.mark.asyncio
    async def test_dispatch_with_empty_kwargs(self):
        """Test dispatch with no keyword arguments."""
        tool = create_mock_tool("empty_tool")
        dispatcher = ToolDispatcher([tool])
        
        result = await dispatcher.dispatch("empty_tool")
        
        from netra_backend.app.schemas.tool import ToolResult, ToolStatus
        assert isinstance(result, ToolResult)
        assert result.status == ToolStatus.SUCCESS
        assert result.tool_input.kwargs == {}
    
    def test_tool_registration_validation(self):
        """Test tool registration with duplicate names."""
        tool1 = create_mock_tool("duplicate_tool")
        tool2 = create_mock_tool("duplicate_tool")  # Same name
        
        # Should handle duplicate names gracefully
        dispatcher = ToolDispatcher([tool1, tool2])
        
        # Should have the tool registered (latest wins)
        assert dispatcher.has_tool("duplicate_tool") == True