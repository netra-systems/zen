from unittest.mock import Mock, patch, MagicMock, AsyncMock
"""Agent test fixtures."""

from unittest.mock import AsyncMock, MagicMock

import pytest

@pytest.fixture
def mock_llm_agent():
    """Create a mock LLM agent."""
    agent = MagicMock()
    agent.process = AsyncMock(return_value = {"response": "Test response"})
    return agent

@pytest.fixture
def mock_tool_registry():
    """Create a mock tool registry."""
    registry = MagicMock()
    registry.get_tool = MagicMock(return_value = MagicMock())
    return registry
