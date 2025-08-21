"""Agent test fixtures."""

import pytest
from unittest.mock import MagicMock, AsyncMock

@pytest.fixture
def mock_llm_agent():
    """Create a mock LLM agent."""
    agent = MagicMock()
    agent.process = AsyncMock(return_value={"response": "Test response"})
    return agent

@pytest.fixture
def mock_tool_registry():
    """Create a mock tool registry."""
    registry = MagicMock()
    registry.get_tool = MagicMock(return_value=MagicMock())
    return registry
