import pytest
from unittest.mock import AsyncMock

from app.services.deep_agent_v3.steps.propose_optimal_policies import propose_optimal_policies
from app.services.deep_agent_v3.state import AgentState

@pytest.mark.asyncio
async def test_propose_optimal_policies(mock_db_session, mock_llm_connector):
    """Tests the propose_optimal_policies step."""
    state = AgentState(patterns=[], raw_logs=[])
    mock_db_session.exec.return_value.all.return_value = []
    mock_llm_connector.generate_text_async = AsyncMock(return_value="{}")
    
    result = await propose_optimal_policies(state, mock_db_session, mock_llm_connector)
    
    assert result == "Generated 0 optimal policies."
    assert state.policies == []