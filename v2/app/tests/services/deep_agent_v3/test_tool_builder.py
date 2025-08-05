
from app.services.deep_agent_v3.tool_builder import ToolBuilder
from app.services.deep_agent_v3.tools.log_fetcher import LogFetcher
from app.services.deep_agent_v3.tools.log_pattern_identifier import LogPatternIdentifier
from app.services.deep_agent_v3.tools.policy_proposer import PolicyProposer
from app.services.deep_agent_v3.tools.policy_simulator import PolicySimulator
from app.services.deep_agent_v3.tools.supply_catalog_search import SupplyCatalogSearch
from app.services.deep_agent_v3.tools.cost_estimator import CostEstimator
from app.services.deep_agent_v3.tools.performance_predictor import PerformancePredictor

def test_tool_builder_builds_all_tools(mock_db_session, mock_llm_connector):
    """Tests that the ToolBuilder correctly builds all the tools."""
    # Arrange & Act
    tools = ToolBuilder.build_all(mock_db_session, mock_llm_connector)

    # Assert
    assert isinstance(tools["log_fetcher"], LogFetcher)
    assert isinstance(tools["log_pattern_identifier"], LogPatternIdentifier)
    assert isinstance(tools["policy_proposer"], PolicyProposer)
    assert isinstance(tools["policy_simulator"], PolicySimulator)
    assert isinstance(tools["supply_catalog_search"], SupplyCatalogSearch)
    assert isinstance(tools["cost_estimator"], CostEstimator)
    assert isinstance(tools["performance_predictor"], PerformancePredictor)
