import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.deep_agent_v3.tools.log_analyzer import LogAnalyzer
from app.services.deep_agent_v3.tools.policy_simulator import PolicySimulator
from app.services.deep_agent_v3.tools.supply_catalog_search import SupplyCatalogSearch

@pytest.fixture
def mock_llm_connector():
    """Provides a mock LLM connector."""
    connector = MagicMock()
    connector.get_completion = AsyncMock(return_value='{"utility_score": 0.9, "predicted_cost_usd": 0.1, "predicted_latency_ms": 100, "predicted_quality_score": 0.9, "explanation": "test", "confidence": 0.9}')
    return connector

@pytest.fixture
def mock_db_session():
    """Provides a mock database session."""
    session = MagicMock()
    session.info = {"user_id": "test_user"}
    return session

class TestLogAnalyzer:
    @pytest.mark.asyncio
    async def test_analyze_logs(self, mock_llm_connector):
        tool = LogAnalyzer(llm_connector=mock_llm_connector)
        logs = ["log1", "log2", "log3"]
        result = await tool.analyze_logs(logs)
        assert result == {"key": "value"}
        mock_llm_connector.generate_text_async.assert_called_once()

class TestPolicySimulator:
    @pytest.mark.asyncio
    async def test_simulate_policy(self, mock_llm_connector):
        tool = PolicySimulator(llm_connector=mock_llm_connector)
        policy = {"pattern_name": "test", "optimal_supply_option_name": "test"}
        result = await tool.simulate(policy)
        assert result.utility_score == 0.9
        mock_llm_connector.get_completion.assert_called_once()

class TestSupplyCatalogSearch:
    @pytest.mark.asyncio
    async def test_search_supply_catalog(self, mock_db_session):
        tool = SupplyCatalogSearch(db_session=mock_db_session)
        query = "test query"
        with patch('app.services.supply_catalog_service.SupplyCatalogService.get_all_options') as mock_get_all_options:
            mock_get_all_options.return_value = [MagicMock(model_name="test query model")]
            result = await tool.search(query)
            assert len(result) == 1
            assert result[0].model_name == "test query model"
            mock_get_all_options.assert_called_once()