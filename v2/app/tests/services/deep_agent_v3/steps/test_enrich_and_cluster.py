import pytest
from unittest.mock import AsyncMock

from app.services.deep_agent_v3.steps.enrich_and_cluster import enrich_and_cluster
from app.services.deep_agent_v3.state import AgentState

@pytest.mark.asyncio
async def test_enrich_and_cluster(mock_llm_connector):
    """Tests the enrich_and_cluster step."""
    state = AgentState(raw_logs=[])
    mock_llm_connector.generate_text_async = AsyncMock(return_value="{}")
    
    result = await enrich_and_cluster(state, mock_llm_connector)
    
    assert result == "Discovered 0 usage patterns."
    assert state.patterns == []