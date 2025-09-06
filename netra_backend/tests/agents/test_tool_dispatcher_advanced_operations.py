from unittest.mock import AsyncMock, Mock, patch, MagicMock
import asyncio

"""Unit tests for ToolDispatcher advanced operations."""

import sys
from pathlib import Path
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead


import pytest

from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.tests.tool_dispatcher_assertions import (
    assert_execution_error_response,
)
from netra_backend.tests.helpers.tool_dispatcher_helpers import (
    create_mock_tool,
    create_test_state,
    verify_dispatch_response_error,
    verify_dispatch_response_success,
    verify_metadata,
)

class TestToolDispatcherAdvancedOperations:
    """Test advanced dispatcher operations."""
    @pytest.mark.asyncio
    async def test_dispatch_tool_success(self):
        """Test dispatch_tool method with success."""
        tool, dispatcher, state = self._setup_dispatch_tool_success()
        result = await dispatcher.dispatch_tool("test_tool", {"param": "value"}, state, "run_123")
        self._verify_dispatch_tool_success(result)
    @pytest.mark.asyncio
    async def test_dispatch_tool_not_found(self):
        """Test dispatch_tool with non-existent tool."""
        dispatcher, state = self._setup_dispatch_tool_not_found()
        result = await dispatcher.dispatch_tool("nonexistent_tool", {"param": "value"}, state, "run_123")
        verify_dispatch_response_error(result, "Tool nonexistent_tool not found")
    
    def test_create_tool_not_found_response(self):
        """Test _create_tool_not_found_response method."""
        dispatcher = ToolDispatcher()
        response = dispatcher._create_tool_not_found_response("missing_tool", "run_123")
        self._verify_tool_not_found_response(response)
    @pytest.mark.asyncio
    async def test_execute_tool_with_error_handling_success(self):
        """Test _execute_tool_with_error_handling with success."""
        tool, dispatcher, state = self._setup_execute_with_error_handling_success()
        response = await dispatcher._execute_tool_with_error_handling(tool, "test_tool", {"param": "value"}, state, "run_123")
        verify_dispatch_response_success(response)
    @pytest.mark.asyncio
    async def test_execute_tool_with_error_handling_failure(self):
        """Test _execute_tool_with_error_handling with failure."""
        failing_tool, dispatcher, state = self._setup_execute_with_error_handling_failure()
        response = await dispatcher._execute_tool_with_error_handling(failing_tool, "failing_tool", {"param": "value"}, state, "run_123")
        verify_dispatch_response_error(response, "Tool failing_tool failed")
    @pytest.mark.asyncio
    async def test_execute_tool_by_type_production_tool(self):
        """Test _execute_tool_by_type with ProductionTool."""
        dispatcher, production_tool, state = self._setup_production_tool_test()
        result = await dispatcher._execute_tool_by_type(production_tool, {"param": "value"}, state, "run_123")
        self._verify_production_tool_result(result, production_tool)
    @pytest.mark.asyncio
    async def test_execute_tool_by_type_async_tool(self):
        """Test _execute_tool_by_type with async tool."""
        dispatcher, async_tool = self._setup_async_tool_test()
        result = await dispatcher._execute_tool_by_type(async_tool, {"param": "value"}, None, "run_123")
        self._verify_async_tool_result(result)
    @pytest.mark.asyncio
    async def test_execute_tool_by_type_sync_tool(self):
        """Test _execute_tool_by_type with sync tool."""
        dispatcher, sync_tool = self._setup_sync_tool_test()
        result = await dispatcher._execute_tool_by_type(sync_tool, {"param": "value"}, None, "run_123")
        self._verify_sync_tool_result(result, sync_tool)
    
    def test_create_success_response(self):
        """Test _create_success_response method."""
        dispatcher = ToolDispatcher()
        response = dispatcher._create_success_response({"data": "test"}, "test_tool", "run_123")
        self._verify_success_response(response)
    
    def test_create_error_response(self):
        """Test _create_error_response method."""
        dispatcher = ToolDispatcher()
        error = Exception("Test error")
        response = dispatcher._create_error_response(error, "test_tool", "run_123")
        self._verify_error_response(response)
    
    def _setup_dispatch_tool_success(self) -> tuple:
        """Setup dispatch tool success test."""
        tool = create_mock_tool("test_tool")
        dispatcher = ToolDispatcher([tool])
        state = create_test_state()
        return tool, dispatcher, state
    
    def _verify_dispatch_tool_success(self, result) -> None:
        """Verify dispatch tool success result."""
        verify_dispatch_response_success(result)
        verify_metadata(result, "test_tool", "run_123")
    
    def _setup_dispatch_tool_not_found(self) -> tuple:
        """Setup dispatch tool not found test."""
        dispatcher = ToolDispatcher()
        state = create_test_state()
        return dispatcher, state
    
    def _verify_tool_not_found_response(self, response) -> None:
        """Verify tool not found response."""
        verify_dispatch_response_error(response, "Tool missing_tool not found")
    
    def _setup_execute_with_error_handling_success(self) -> tuple:
        """Setup execute with error handling success test."""
        tool = create_mock_tool("test_tool")
        dispatcher = ToolDispatcher([tool])
        state = create_test_state()
        return tool, dispatcher, state
    
    def _setup_execute_with_error_handling_failure(self) -> tuple:
        """Setup execute with error handling failure test."""
        failing_tool = create_mock_tool("failing_tool", should_fail=True)
        dispatcher = ToolDispatcher([failing_tool])
        state = create_test_state()
        return failing_tool, dispatcher, state
    
    def _setup_production_tool_test(self) -> tuple:
        """Setup production tool test."""
        dispatcher = ToolDispatcher()
        production_tool = dispatcher.tools["create_corpus"]
        # Mock: Async component isolation for testing without real async operations
        production_tool.execute = AsyncMock(return_value={"success": True})
        state = create_test_state()
        return dispatcher, production_tool, state
    
    def _verify_production_tool_result(self, result, production_tool) -> None:
        """Verify production tool execution result."""
        assert result == {"success": True}
        # Verify call was made with correct parameters and run_id, but use ANY for state comparison
        production_tool.execute.assert_called_once_with({"param": "value"}, ANY, "run_123")
    
    def _setup_async_tool_test(self) -> tuple:
        """Setup async tool test."""
        dispatcher = ToolDispatcher()
        async_tool = create_mock_tool("async_tool")
        return dispatcher, async_tool
    
    def _verify_async_tool_result(self, result) -> None:
        """Verify async tool execution result."""
        assert "result" in result
        assert "async_tool" in str(result)
    
    def _setup_sync_tool_test(self) -> tuple:
        """Setup sync tool test."""
        dispatcher = ToolDispatcher()
        # Mock: Generic component isolation for controlled unit testing
        sync_tool = sync_tool_instance  # Initialize appropriate service
        sync_tool.return_value = {"sync": "result"}
        # Ensure it doesn't have arun method to be treated as sync tool
        if hasattr(sync_tool, 'arun'):
            delattr(sync_tool, 'arun')
        return dispatcher, sync_tool
    
    def _verify_sync_tool_result(self, result, sync_tool) -> None:
        """Verify sync tool execution result."""
        assert result == {"sync": "result"}
        sync_tool.assert_called_once_with({"param": "value"})
    
    def _verify_success_response(self, response) -> None:
        """Verify success response format."""
        verify_dispatch_response_success(response)
        assert response.result == {"data": "test"}
        verify_metadata(response, "test_tool", "run_123")
    
    def _verify_error_response(self, response) -> None:
        """Verify error response format."""
        verify_dispatch_response_error(response, "Test error")
        verify_metadata(response, "test_tool", "run_123")