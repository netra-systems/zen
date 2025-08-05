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
async def test_query_raw_logs_success(mock_db_session):
    """Tests successful fetching and parsing of raw logs."""
    with patch('app.services.deep_agent_v3.steps.fetch_raw_logs.get_clickhouse_client') as mock_get_client:
        mock_client = MagicMock()
        mock_client.execute.return_value = (
            [],
            [('event_metadata_log_schema_version', 'String'), ('event_metadata_event_id', 'UUID'), ('event_metadata_timestamp_utc', 'DateTime64(3)'), ('event_metadata_ingestion_source', 'String'), ('trace_context_trace_id', 'UUID'), ('trace_context_span_id', 'UUID'), ('trace_context_span_name', 'String'), ('trace_context_span_kind', 'String'), ('identity_context_user_id', 'UUID'), ('identity_context_organization_id', 'String'), ('identity_context_api_key_hash', 'String'), ('identity_context_auth_method', 'String'), ('application_context_app_name', 'String'), ('application_context_service_name', 'String'), ('application_context_sdk_version', 'String'), ('application_context_environment', 'LowCardinality(String)'), ('application_context_client_ip', 'IPv4'), ('request_model', 'JSON'), ('request_prompt', 'JSON'), ('request_generation_config', 'JSON'), ('response', 'JSON'), ('response_completion', 'JSON'), ('response_tool_calls', 'JSON'), ('response_usage', 'JSON'), ('response_system', 'JSON'), ('performance_latency_ms', 'JSON'), ('finops_attribution', 'JSON'), ('finops_cost', 'JSON'), ('finops_pricing_info', 'JSON'), ('governance_audit_context', 'JSON'), ('governance_safety', 'JSON'), ('governance_security', 'JSON')]
        )
        mock_get_client.return_value = mock_client

        with patch('app.services.security_service.SecurityService.get_user_credentials') as mock_get_user_credentials:
            mock_get_user_credentials.return_value = {"host": "localhost", "port": 9000, "user": "default", "password": "", "database": "default"}
            
            logs = await fetch_raw_logs(
                state=MagicMock(),
                tools=MagicMock(),
                request=mock_request(),
            )
            assert logs is not None

@pytest.mark.asyncio
async def test_enrich_and_cluster_logs_success(sample_log_entries, mock_llm_connector):
    """Tests successful enrichment and clustering of logs."""
    state = MagicMock()
    state.raw_logs = sample_log_entries
    tools = {"llm_connector": mock_llm_connector}
    request = MagicMock()

    result = await enrich_and_cluster(state, tools, request)
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

    with patch('app.services.deep_agent_v3.steps.propose_optimal_policies.SupplyCatalog.list_all_records', new_callable=AsyncMock) as mock_list_all_records:
        mock_list_all_records.return_value = [SupplyOption(id="test-option", name="test-option")]
        
        with patch('app.services.deep_agent_v3.steps.propose_optimal_policies.PolicySimulator.run', new_callable=AsyncMock) as mock_simulate:
            mock_simulate.return_value = {"supply_option_id": "test-option", "utility_score": 0.9, "predicted_cost_usd": 0.1, "predicted_latency_ms": 100, "predicted_quality_score": 0.9, "explanation": "test", "confidence": 0.9}
            
            result = await propose_optimal_policies(state, tools, request)
            assert result["status"] == "success"
            assert len(state.policies) > 0

# --- Unit Tests for DeepAgentV3 Class ---

@pytest.mark.asyncio
async def test_deep_agent_v3_full_run(mock_request, mock_db_session, mock_llm_connector):
    """Tests the full execution of the DeepAgentV3 pipeline."""
    with patch('app.services.deep_agent_v3.main.ScenarioFinder.find_scenario', return_value={"steps": []}):
        agent = DeepAgentV3(run_id="test-run", request=mock_request, db_session=mock_db_session, llm_connector=mock_llm_connector)
        await agent.run_full_analysis()
        assert agent.status == "complete"

@pytest.mark.asyncio
async def test_deep_agent_v3_step_by_step(mock_request, mock_db_session, mock_llm_connector):
    """Tests the step-by-step execution of the agent."""
    with patch('app.services.deep_agent_v3.main.ScenarioFinder.find_scenario', return_value={"steps": ["fetch_raw_logs"]}):
        agent = DeepAgentV3(run_id="test-run", request=mock_request, db_session=mock_db_session, llm_connector=mock_llm_connector)
        with patch('app.services.deep_agent_v3.steps.fetch_raw_logs.fetch_raw_logs', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {"status": "success"}
            result = await agent.run_next_step()
            assert result["status"] == "success"

@pytest.mark.asyncio
async def test_deep_agent_v3_step_failure(mock_request, mock_db_session, mock_llm_connector):
    """Tests that a step failure is handled gracefully."""
    with patch('app.services.deep_agent_v3.main.ScenarioFinder.find_scenario', return_value={"steps": ["fetch_raw_logs"]}):
        agent = DeepAgentV3(run_id="test-run", request=mock_request, db_session=mock_db_session, llm_connector=mock_llm_connector)
        with patch('app.services.deep_agent_v3.steps.fetch_raw_logs.fetch_raw_logs', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("Test Error")
            result = await agent.run_next_step()
            assert result["status"] == "failed"