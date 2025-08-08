import pytest
import asyncio
from app.services.agents.base import BaseSubAgent
from unittest.mock import MagicMock

class ConcreteSubAgent(BaseSubAgent):
    async def run(self, input_data, run_id, stream_updates):
        return await super().run(input_data, run_id, stream_updates)

@pytest.mark.asyncio
async def test_agent_node_is_coroutine():
    # Arrange
    sub_agent = ConcreteSubAgent()
    # Act & Assert
    assert asyncio.iscoroutinefunction(sub_agent.run)
