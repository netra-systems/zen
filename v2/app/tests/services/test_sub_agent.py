import pytest
from app.services.deepagents.sub_agent import SubAgent

class ConcreteSubAgent(SubAgent):
    def get_initial_prompt(self):
        return "Initial prompt"

@pytest.mark.asyncio
async def test_agent_node_is_coroutine():
    # Arrange
    sub_agent = ConcreteSubAgent(name="test_agent", description="", prompt="", tools=[])
    # Act & Assert
    assert asyncio.iscoroutinefunction(sub_agent.agent_node)

@pytest.mark.asyncio
async def test_agent_node_preserves_name():
    # Arrange
    sub_agent = ConcreteSubAgent(name="test_agent", description="", prompt="", tools=[])
    # Act & Assert
    assert sub_agent.agent_node.__name__ == "test_agent"