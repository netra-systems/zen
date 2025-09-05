"""Unit tests for ToolDispatcher initialization and tool registration."""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import pytest

from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.tests.helpers.tool_dispatcher_helpers import (
    assert_corpus_tools_registered,
    assert_synthetic_tools_registered,
    create_mock_tool,
)

class TestToolDispatcherInitialization:
    """Test ToolDispatcher initialization and tool registration."""
    
    def test_init_empty(self):
        """Test initialization without tools."""
        dispatcher = ToolDispatcher()
        self._verify_default_tools_registered(dispatcher)
    
    def test_init_with_tools(self):
        """Test initialization with provided tools."""
        tools = self._create_test_tools()
        dispatcher = ToolDispatcher(tools)
        self._verify_provided_tools_registered(dispatcher, tools)
    
    def test_register_synthetic_tools(self):
        """Test synthetic tools registration."""
        dispatcher = ToolDispatcher()
        assert_synthetic_tools_registered(dispatcher)
    
    def test_register_corpus_tools(self):
        """Test corpus tools registration."""
        dispatcher = ToolDispatcher()
        assert_corpus_tools_registered(dispatcher)
    
    def _verify_default_tools_registered(self, dispatcher: ToolDispatcher) -> None:
        """Verify synthetic and corpus tools are registered."""
        assert "generate_synthetic_data_batch" in dispatcher.tools
        assert "create_corpus" in dispatcher.tools
        assert "search_corpus" in dispatcher.tools
        assert len(dispatcher.tools) > 0
    
    def _create_test_tools(self) -> list:
        """Create test tools for initialization."""
        tool1 = create_mock_tool("test_tool_1")
        tool2 = create_mock_tool("test_tool_2")
        return [tool1, tool2]
    
    def _verify_provided_tools_registered(self, dispatcher: ToolDispatcher, tools: list) -> None:
        """Verify provided tools are registered correctly."""
        assert "test_tool_1" in dispatcher.tools
        assert "test_tool_2" in dispatcher.tools
        assert dispatcher.tools["test_tool_1"] == tools[0]
        assert dispatcher.tools["test_tool_2"] == tools[1]