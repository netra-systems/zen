import pytest
from unittest.mock import MagicMock, AsyncMock
from app.services.deep_agent_v3.steps.enrich_and_cluster import enrich_and_cluster
from app.services.deep_agent_v3.state import AgentState
from app.db.models_clickhouse import UnifiedLogEntry, Request, Response, Performance, FinOps, TraceContext

@pytest.mark.asyncio
async def test_enrich_and_cluster_success():
    # Arrange
    state = MagicMock(spec=AgentState)
    state.raw_logs=[
        UnifiedLogEntry(
            request=Request(model="test-model", prompt_text="test prompt"),
            response=Response(usage={'prompt_tokens': 10, 'completion_tokens': 20}),
            performance=Performance(latency_ms={'total_e2e_ms': 100, 'time_to_first_token_ms': 50}),
            finops=FinOps(total_cost_usd=0.01),
            trace_context=TraceContext(trace_id='1', span_id='a')
        ),
        UnifiedLogEntry(
            request=Request(model="test-model", prompt_text="test prompt"),
            response=Response(usage={'prompt_tokens': 15, 'completion_tokens': 25}),
            performance=Performance(latency_ms={'total_e2e_ms': 120, 'time_to_first_token_ms': 60}),
            finops=FinOps(total_cost_usd=0.02),
            trace_context=TraceContext(trace_id='2', span_id='b')
        )
    ]
    log_pattern_identifier = MagicMock()
    log_pattern_identifier.identify_patterns = AsyncMock(return_value=(["pattern1", "pattern2"], ["desc1", "desc2"]))

    # Act
    result = await enrich_and_cluster(state, log_pattern_identifier)

    # Assert
    assert result == "Successfully discovered 2 patterns."
    assert len(state.discovered_patterns) == 2
    assert len(state.pattern_descriptions) == 2
    log_pattern_identifier.identify_patterns.assert_called_once()

@pytest.mark.asyncio
async def test_enrich_and_cluster_no_logs():
    # Arrange
    state = MagicMock(spec=AgentState)
    state.raw_logs = []
    log_pattern_identifier = MagicMock()
    log_pattern_identifier.identify_patterns.return_value = ([], [])

    # Act
    result = await enrich_and_cluster(state, log_pattern_identifier)

    # Assert
    assert result == "No logs to enrich and cluster."
    log_pattern_identifier.identify_patterns.assert_not_called()
