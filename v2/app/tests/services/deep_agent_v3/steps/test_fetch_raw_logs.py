import pytest
from unittest.mock import MagicMock
from app.services.deep_agent_v3.steps.fetch_raw_logs import fetch_raw_logs
from app.services.deep_agent_v3.state import AgentState

@pytest.mark.asyncio
async def test_fetch_raw_logs_success():
    # Arrange
    state = MagicMock(spec=AgentState)
    log_fetcher = MagicMock()
    log_fetcher.fetch_logs.return_value = (["log1", "log2"], ["trace1", "trace2"])
    request = {
        "time_range": {
            "start_time": "2025-08-01T00:00:00Z",
            "end_time": "2025-08-01T01:00:00Z"
        },
        "source_table": "test_table"
    }

    # Act
    result = await fetch_raw_logs(state, log_fetcher, request)

    # Assert
    assert result == "Raw logs fetched."
    assert len(state.raw_logs) == 2
    assert len(state.trace_ids) == 2
    log_fetcher.fetch_logs.assert_called_once_with(
        time_range={
            "start_time": "2025-08-01T00:00:00Z",
            "end_time": "2025-08-01T01:00:00Z"
        },
        source_table="test_table"
    )

@pytest.mark.asyncio
async def test_fetch_raw_logs_no_logs():
    # Arrange
    state = MagicMock(spec=AgentState)
    log_fetcher = MagicMock()
    log_fetcher.fetch_logs.return_value = ([], [])
    request = {
        "time_range": {
            "start_time": "2025-08-01T00:00:00Z",
            "end_time": "2025-08-01T01:00:00Z"
        },
        "source_table": "test_table"
    }

    # Act
    result = await fetch_raw_logs(state, log_fetcher, request)

    # Assert
    assert result == "Raw logs fetched."
    assert len(state.raw_logs) == 0
    assert len(state.trace_ids) == 0
    log_fetcher.fetch_logs.assert_called_once_with(
        time_range={
            "start_time": "2025-08-01T00:00:00Z",
            "end_time": "2025-08-01T01:00:00Z"
        },
        source_table="test_table"
    )