import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from app.services.deep_agent_v3.main import DeepAgentV3
from app.services.deep_agent_v3.steps.fetch_raw_logs import fetch_raw_logs
from app.services.deep_agent_v3.steps.enrich_and_cluster import enrich_and_cluster
from app.services.deep_agent_v3.steps.propose_optimal_policies import propose_optimal_policies
from app.db.models_clickhouse import UnifiedLogEntry, AnalysisRequest, Request, Response, Performance, FinOps, TraceContext
from app.db.models_postgres import SupplyOption
from app.schema import DiscoveredPattern, LearnedPolicy, PredictedOutcome
from app.services.deep_agent_v3.state import AgentState

# --- Fixtures ---

@pytest.fixture
def mock_db_session():
    """Provides a mock database session."""
    session = MagicMock()
    session.info = {"user_id": "test_user"}
    return session

@pytest.fixture
def mock_llm_connector():
    """Provides a mock LLM connector."""
    connector = MagicMock()
    connector.get_completion = AsyncMock(return_value='{"key": "value"}')
    return connector

@pytest.fixture
def mock_request():
    """Provides a mock analysis request."""
    return AnalysisRequest(
        user_id="test_user",
        workloads=[{"query": "test query"}],
        query="test query"
    )

@pytest.fixture
def sample_log_entries():
    """Provides sample UnifiedLogEntry objects."""
    return [
        UnifiedLogEntry(
            trace_context=TraceContext(trace_id="trace1", span_id="span1"),
            response=Response(usage={"prompt_tokens": 10, "completion_tokens": 20}),
            performance=Performance(latency_ms={"total_e2e_ms": 100, "time_to_first_token_ms": 50}),
            finops=FinOps(total_cost_usd=0.01),
            request=Request(model="test_model", prompt_text="test prompt"),
        ),
        UnifiedLogEntry(
            trace_context=TraceContext(trace_id="trace2", span_id="span2"),
            response=Response(usage={"prompt_tokens": 30, "completion_tokens": 40}),
            performance=Performance(latency_ms={"total_e2e_ms": 200, "time_to_first_token_ms": 100}),
            finops=FinOps(total_cost_usd=0.02),
            request=Request(model="test_model", prompt_text="test prompt"),
        ),
    ]

# --- Unit Tests for Helper Functions ---

@pytest.mark.asyncio
async def test_query_raw_logs_success(mock_db_session, mock_request):
    """Tests successful fetching and parsing of raw logs."""
    state = AgentState()
    log_fetcher = MagicMock()
    log_fetcher.fetch_logs.return_value = []
    request = {"time_range": {"start_time": "2025-08-01T00:00:00Z", "end_time": "2025-08-01T01:00:00Z"}}

    result = await fetch_raw_logs(state, log_fetcher, request)

    assert result == "Raw logs fetched."

@pytest.mark.asyncio
async def test_enrich_and_cluster_logs_success(sample_log_entries, mock_llm_connector):
    """Tests successful enrichment and clustering of logs."""
    state = MagicMock()
    state.raw_logs = sample_log_entries
    tools = {"llm_connector": mock_llm_connector}
    request = MagicMock()

    result = await enrich_and_cluster(state, tools["llm_connector"])
    assert result["status"] == "success"
    assert len(state.patterns) > 0

@pytest.mark.asyncio
async def test_propose_optimal_policies_success(mock_db_session, mock_llm_connector):
    """Tests successful proposal of optimal policies."""
    patterns = [DiscoveredPattern(pattern_id="p1", pattern_name="p1", pattern_description="test", centroid_features={}, member_span_ids=["s1"], member_count=1)]
    span_map = {"s1": UnifiedLogEntry(trace_context=TraceContext(trace_id="trace1", span_id="span1"), request=Request(model="test_model", prompt_text="test"), finops=FinOps(total_cost_usd=0.1), performance=Performance(latency_ms={"total_e2e_ms": 100}), response=Response(usage={'prompt_tokens': 10, 'completion_tokens': 20}))}
    state = MagicMock()
    state.patterns = patterns
    state.span_map = span_map
    tools = {"llm_connector": mock_llm_connector, "db_session": mock_db_session}
    request = MagicMock()

    with patch('app.services.deep_agent_v3.steps.propose_optimal_policies.PolicySimulator.run', new_callable=AsyncMock) as mock_simulate:
        mock_simulate.return_value = {"supply_option_id": "test-option", "utility_score": 0.9, "predicted_cost_usd": 0.1, "predicted_latency_ms": 100, "predicted_quality_score": 0.9, "explanation": "test", "confidence": 0.9}
        
        result = await propose_optimal_policies(state, tools, request)
        assert result["status"] == "success"
        assert len(state.policies) > 0