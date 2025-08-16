"""Unit tests for ToolDispatcher edge cases and error scenarios."""

import pytest

from app.agents.tool_dispatcher import ToolDispatcher
from app.schemas import ToolResult
from app.tests.helpers.tool_dispatcher_helpers import (
    create_mock_tool,
    create_test_state
)


class TestToolDispatcherEdgeCases:
    """Test edge cases and error scenarios."""
    async def test_dispatch_with_none_parameters(self):
        """Test dispatch with None parameters."""
        dispatcher = ToolDispatcher()
        result = await dispatcher.dispatch("create_corpus")
        self._verify_dispatch_handles_none_parameters(result)
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