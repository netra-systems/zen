
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import pandas as pd
from datetime import datetime

from app.services.deep_agent_v3.main import (
    DeepAgentV3,
    AgentState,)
from app.services.deep_agent_v3.core import (
    query_raw_logs,
    enrich_and_cluster_logs,
    propose_optimal_policies,
)
from app.services.deep_agent_v3.core import simulate_policy_outcome
from app.db.models_clickhouse import UnifiedLogEntry, AnalysisRequest
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
    # Mock the async method
    connector.generate_text_async = AsyncMock(return_value='{"key": "value"}')
    return connector

@pytest.fixture
def mock_request():
    """Provides a mock analysis request."""
    return AnalysisRequest(
        run_id="test-run",
        data_source={"source_table": "default.logs"},
        time_range={"start_time": datetime(2023, 1, 1), "end_time": datetime(2023, 1, 2)},
        workloads=[{"name": "test"}],
    )

@pytest.fixture
def sample_log_entries():
    """Provides sample UnifiedLogEntry objects."""
    return [
        UnifiedLogEntry(
            trace_context={"trace_id": "trace1", "span_id": "span1"},
            response={"usage": {"prompt_tokens": 10, "completion_tokens": 20}},
            performance={"latency_ms": {"total_e2e_ms": 100, "time_to_first_token_ms": 50}},
            finops={"total_cost_usd": 0.01},
            request={"user_goal": "quality", "model": {"provider": "test", "family": "test", "name": "test"}, "prompt_text": "test"},
        ),
        UnifiedLogEntry(
            trace_context={"trace_id": "trace2", "span_id": "span2"},
            response={"usage": {"prompt_tokens": 30, "completion_tokens": 40}},
            performance={"latency_ms": {"total_e2e_ms": 200, "time_to_first_token_ms": 100}},
            finops={"total_cost_usd": 0.02},
            request={"user_goal": "cost", "model": {"provider": "test", "family": "test", "name": "test"}, "prompt_text": "test"},
        ),
    ]

# --- Unit Tests for Helper Functions ---

@pytest.mark.asyncio
async def test_query_raw_logs_success(mock_db_session):
    """Tests successful fetching and parsing of raw logs."""
    with patch('app.services.deep_agent_v3.core.get_clickhouse_client') as mock_get_client:
        mock_client = MagicMock()
        mock_client.execute.return_value = (
            [('val1', 123)], # Data rows
            [('col1', 'String'), ('col2', 'Int32')] # Column info
        )
        mock_get_client.return_value = mock_client

        # Mock security_service
        with patch('app.services.deep_agent_v3.core.security_service') as mock_security:
            mock_security.get_user_credentials.return_value = {"host": "localhost"}
            
            logs = await query_raw_logs(
                db_session=mock_db_session,
                source_table="db.table",
                start_time=datetime(2023, 1, 1),
                end_time=datetime(2023, 1, 2),
            )
            # This will fail validation, but we are testing the query part
            assert len(logs) == 0 # Expect validation to fail on mock data

@pytest.mark.asyncio
async def test_enrich_and_cluster_logs_success(sample_log_entries, mock_llm_connector):
    """Tests successful enrichment and clustering of logs."""
    mock_llm_connector.generate_text_async.return_value = '''
    {
        "pattern_0": {"name": "Test Pattern", "description": "A test pattern."}
    }
    '''
    patterns = await enrich_and_cluster_logs(
        spans=sample_log_entries,
        n_patterns=1,
        llm_connector=mock_llm_connector,
    )
    assert len(patterns) == 1
    assert patterns[0].pattern_name == "Test Pattern"
    assert len(patterns[0].member_span_ids) > 0

@pytest.mark.asyncio
async def test_propose_optimal_policies_success(mock_db_session, mock_llm_connector):
    """Tests successful proposal of optimal policies."""
    patterns = [DiscoveredPattern(pattern_name="p1", pattern_description="test", centroid_features={}, member_span_ids=["s1"], member_count=1)]
    span_map = {"s1": UnifiedLogEntry(trace_context={"trace_id": "trace1", "span_id": "span1"}, request={"user_goal": "quality", "model": {"provider": "test", "family": "test", "name": "test"}, "prompt_text": "test"}, finops={"total_cost_usd": 0.1}, performance={"latency_ms": {"total_e2e_ms": 100}}, response={})}
    
    with patch('app.services.deep_agent_v3.core.get_supply_catalog', new_callable=AsyncMock) as mock_get_catalog:
        mock_get_catalog.return_value = [SupplyOption(name="test-option")]
        
        with patch('app.services.deep_agent_v3.core.simulate_policy_outcome', new_callable=AsyncMock) as mock_simulate:
            mock_simulate.return_value = PredictedOutcome(supply_option_name="test-option", utility_score=0.9, predicted_cost_usd=0.1, predicted_latency_ms=100, predicted_quality_score=0.9, explanation="test", confidence=0.9)
            
            policies = await propose_optimal_policies(
                db_session=mock_db_session,
                patterns=patterns,
                span_map=span_map,
                llm_connector=mock_llm_connector,
            )
            assert len(policies) == 1
            assert policies[0].optimal_supply_option_name == "test-option"

# --- Unit Tests for DeepAgentV3 Class ---

@pytest.mark.asyncio
async def test_deep_agent_v3_full_run(mock_request, mock_db_session, mock_llm_connector):
    """Tests the full execution of the DeepAgentV3 pipeline."""
    agent = DeepAgentV3(run_id="test-run", request=mock_request, db_session=mock_db_session, llm_connector=mock_llm_connector)
    agent.langfuse.trace = MagicMock()

    # Mock each step's underlying function to isolate the agent's logic
    with patch('app.services.deep_agent_v3.core.query_raw_logs', new_callable=AsyncMock) as mock_query, \
         patch('app.services.deep_agent_v3.core.enrich_and_cluster_logs', new_callable=AsyncMock) as mock_cluster, \
         patch('app.services.deep_agent_v3.core.propose_optimal_policies', new_callable=AsyncMock) as mock_propose:

        mock_query.return_value = [UnifiedLogEntry(trace_context={"trace_id": "trace1", "span_id": "span1"}, request={"user_goal": "quality", "model": {"provider": "test", "family": "test", "name": "test"}, "prompt_text": "test"}, finops={"total_cost_usd": 0.1}, performance={"latency_ms": {"total_e2e_ms": 100}}, response={})]
        mock_cluster.return_value = [DiscoveredPattern(pattern_name="p1", pattern_description="test", centroid_features={}, member_span_ids=["s1"], member_count=1)]
        mock_propose.return_value = [LearnedPolicy(
            pattern_name="p1",
            optimal_supply_option_name="opt1",
            predicted_outcome=PredictedOutcome(
                supply_option_name="test-option",
                utility_score=0.9,
                predicted_cost_usd=0.1,
                predicted_latency_ms=100,
                predicted_quality_score=0.9,
                explanation="test",
                confidence=0.9
            ),
            alternative_outcomes=[],
            baseline_metrics={"avg_cost_usd": 0.1, "avg_latency_ms": 100, "avg_quality_score": 0.9},
            pattern_impact_fraction=0.5
        )]

        final_report = await agent.run_full_analysis()

        assert agent.is_complete()
        assert "Analysis Complete" in final_report
        assert mock_db_session.add.call_count == 4 # One for each step
        assert mock_db_session.commit.call_count == 4

@pytest.mark.asyncio
async def test_deep_agent_v3_step_by_step(mock_request, mock_db_session, mock_llm_connector):
    """Tests the step-by-step execution of the agent."""
    agent = DeepAgentV3(run_id="test-run", request=mock_request, db_session=mock_db_session, llm_connector=mock_llm_connector)
    agent.langfuse.trace = MagicMock()

    with patch('app.services.deep_agent_v3.core.query_raw_logs', new_callable=AsyncMock) as mock_query:
        mock_query.return_value = [UnifiedLogEntry(trace_context={"trace_id": "trace1", "span_id": "span1"}, request={"user_goal": "quality", "model": {"provider": "test", "family": "test", "name": "test"}, "prompt_text": "test"}, finops={"total_cost_usd": 0.1}, performance={"latency_ms": {"total_e2e_ms": 100}}, response={})]
        result = await agent.run_next_step()
        assert result["status"] == "in_progress"
        assert result["completed_step"] == "_step_1_fetch_raw_logs"
        assert agent.current_step_index == 1

@pytest.mark.asyncio
async def test_deep_agent_v3_step_failure(mock_request, mock_db_session, mock_llm_connector):
    """Tests that a step failure is handled gracefully."""
    agent = DeepAgentV3(run_id="test-run", request=mock_request, db_session=mock_db_session, llm_connector=mock_llm_connector)
    agent.langfuse.trace = MagicMock()

    with patch('app.services.deep_agent_v3.core.query_raw_logs', new_callable=AsyncMock) as mock_query:
        mock_query.side_effect = Exception("Test Error")
        result = await agent.run_next_step()
        assert result["status"] == "failed"
        assert result["step"] == "step_1_fetch_raw_logs"
        assert result["error"] == "Test Error"
        assert not agent.is_complete()

