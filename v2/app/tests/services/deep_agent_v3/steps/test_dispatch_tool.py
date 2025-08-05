import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.deep_agent_v3.steps.dispatch_tool import dispatch_tool
from app.services.deep_agent_v3.state import AgentState
from app.db.models_clickhouse import AnalysisRequest
from app.config import settings

@pytest.fixture
def mock_llm_connector():
    return MagicMock()

@pytest.mark.asyncio
async def test_dispatch_tool(mock_llm_connector):
    """Tests the dispatch_tool step."""
    state = MagicMock(spec=AgentState)
    state.request = AnalysisRequest(
        user_id="test_user",
        workloads=[],
        query="Test query"
    )
    mock_llm_connector.generate_text_async = AsyncMock(return_value='{"tool_name": "cost_reduction_quality_preservation", "arguments": {"feature_x_latency": 500, "feature_y_latency": 200}}')

    result = await dispatch_tool(state, mock_llm_connector, settings)

    assert result == "Successfully dispatched tool: cost_reduction_quality_preservation"
    assert state.current_tool_name == "cost_reduction_quality_preservation"
    assert state.current_tool_args == {"feature_x_latency": 500, "feature_y_latency": 200}