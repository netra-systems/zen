
import pytest
from unittest.mock import AsyncMock

from app.services.deep_agent_v3.steps.fetch_raw_logs import fetch_raw_logs
from app.services.deep_agent_v3.state import AgentState
from app.services.deep_agent_v3.models import DataSource, TimeRange
from app.db.models_clickhouse import AnalysisRequest

@pytest.mark.asyncio
async def test_fetch_raw_logs(mock_db_session):
    """Tests the fetch_raw_logs step."""
    state = AgentState(
        request=AnalysisRequest(
            user_id="test_user",
            workloads=[],
            data_source=DataSource(source_table="test.table"),
            time_range=TimeRange(start_time="2025-01-01T00:00:00Z", end_time="2025-01-02T00:00:00Z")
        )
    )
    mock_db_session.execute = AsyncMock(return_value=([], []))
    
    result = await fetch_raw_logs(state, mock_db_session)
    
    assert result == "Fetched 0 log entries."
    assert state.raw_logs == []
