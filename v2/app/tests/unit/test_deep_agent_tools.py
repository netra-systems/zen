
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.deep_agent_v3.tools.log_analyzer import LogAnalyzer
from app.services.deep_agent_v3.tools.policy_simulator import PolicySimulator
from app.services.deep_agent_v3.tools.supply_catalog_search import SupplyCatalogSearch

@pytest.fixture
def mock_llm_connector():
    """Provides a mock LLM connector."""
    connector = MagicMock()
    connector.generate_text_async = AsyncMock(return_value='{"key": "value"}')
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
        policy = {"policy": "test"}
        result = await tool.simulate(policy)
        assert result == {"key": "value"}
        mock_llm_connector.generate_text_async.assert_called_once()

class TestSupplyCatalogSearch:
    @pytest.mark.asyncio
    async def test_search_supply_catalog(self, mock_db_session):
        tool = SupplyCatalogSearch(db_session=mock_db_session)
        query = "test query"
        with patch('app.services.deep_agent_v3.tools.supply_catalog_search.SupplyCatalogSearch.search') as mock_search:
            mock_list_all_records.return_value = [MagicMock(model_name="test query model")]
            result = await tool.search_supply_catalog(query)
            assert len(result) == 1
            assert result[0].model_name == "test query model"
            mock_list_all_records.assert_called_once()
