import pytest
import asyncio
from app.services.deepagents.sub_agent import SubAgent
from unittest.mock import MagicMock

class ConcreteSubAgent(SubAgent):
    def get_initial_prompt(self):
        return "Initial prompt"

    async def agent_node(self, state):
        return await super().agent_node(state)

@pytest.mark.asyncio
async def test_agent_node_is_coroutine():
    # Arrange
    llm_manager = MagicMock()
    sub_agent = ConcreteSubAgent(name="test_agent", description="", tools=[], llm_manager=llm_manager)
    # Act & Assert
    assert asyncio.iscoroutinefunction(sub_agent.agent_node)

@pytest.mark.asyncio
async def test_agent_node_preserves_name():
    # Arrange
    llm_manager = MagicMock()
    sub_agent = ConcreteSubAgent(name="test_agent", description="", tools=[], llm_manager=llm_manager)
    # Act & Assert
    assert sub_agent.agent_node.__name__ == "agent_node"