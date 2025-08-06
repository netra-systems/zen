import pytest
from unittest.mock import MagicMock, AsyncMock
from app.services.deepagents.sub_agent import SubAgent
from app.services.deepagents.state import DeepAgentState

@pytest.mark.asyncio
async def test_agent_node_is_coroutine():
    # Arrange
    sub_agent = SubAgent(name="test_agent", description="", prompt="", tools=[])
    llm_manager = MagicMock()
    llm_manager.get_llm.return_value.bind_tools.return_value = AsyncMock()

    # Act
    agent_runnable = sub_agent.as_runnable(llm_manager)

    # Assert
    assert asyncio.iscoroutinefunction(agent_runnable)

@pytest.mark.asyncio
async def test_agent_node_preserves_name():
    # Arrange
    sub_agent = SubAgent(name="test_agent", description="", prompt="", tools=[])
    llm_manager = MagicMock()

    # Act
    agent_runnable = sub_agent.as_runnable(llm_manager)

    # Assert
    assert agent_runnable.__name__ == 'agent_node'
