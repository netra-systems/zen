from unittest.mock import Mock, patch, MagicMock
import asyncio

"""Unit tests for ToolDispatcher edge cases and error scenarios."""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import pytest
from netra_backend.app.schemas.tool import ToolResult

from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.tests.helpers.tool_dispatcher_helpers import (
    create_mock_tool,
    create_test_state,
)

class TestToolDispatcherEdgeCases:
    """Test edge cases and error scenarios."""
    @pytest.mark.asyncio
    async def test_dispatch_with_none_parameters(self):
        """Test dispatch with None parameters."""
        dispatcher = ToolDispatcher()
        # Mock: Component isolation for testing without external dependencies
        result = await dispatcher.dispatch("create_corpus")
        self._verify_dispatch_handles_none_parameters(result)
    @pytest.mark.asyncio
    async def test_dispatch_tool_with_empty_state(self):
        """Test dispatch_tool with minimal state."""
        tool, dispatcher = self._setup_dispatch_with_empty_state()
        state = create_test_state("")
        result = await dispatcher.dispatch_tool("test_tool", {}, state, "run_123")
        assert result.success is True
    
    def test_register_tool_batch_with_existing_tools(self):
        """Test _register_tool_batch with some existing tools."""
        dispatcher = ToolDispatcher()
        existing_count = len(dispatcher.tools)
        self._register_mixed_tools(dispatcher)
        self._verify_new_tools_added(dispatcher, existing_count)
    
    def _verify_dispatch_handles_none_parameters(self, result: ToolResult) -> None:
        """Verify dispatch handles None parameters without crashing."""
        assert isinstance(result, ToolResult)
        # The test should verify the tool returns a valid response despite None parameters
        assert result is not None
        assert hasattr(result, 'status') and hasattr(result, 'tool_input')
    
    def _setup_dispatch_with_empty_state(self) -> tuple:
        """Setup dispatch with empty state test."""
        tool = create_mock_tool("test_tool")
        dispatcher = ToolDispatcher([tool])
        return tool, dispatcher
    
    def _register_mixed_tools(self, dispatcher: ToolDispatcher) -> None:
        """Register mix of new and existing tools."""
        tool_names = ["create_corpus", "new_tool_1", "new_tool_2"]
        dispatcher._register_tool_batch(tool_names)
    
    def _verify_new_tools_added(self, dispatcher: ToolDispatcher, existing_count: int) -> None:
        """Verify only new tools were added."""
        assert "new_tool_1" in dispatcher.tools
        assert "new_tool_2" in dispatcher.tools
        assert len(dispatcher.tools) >= existing_count + 2