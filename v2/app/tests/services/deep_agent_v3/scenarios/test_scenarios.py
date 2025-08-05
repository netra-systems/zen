from unittest.mock import MagicMock
from app.services.deep_agent_v3.scenario_finder import ScenarioFinder
from app.db.models_clickhouse import AnalysisRequest

def test_get_scenario():
    """Tests the get_scenario function."""
    mock_llm_connector = MagicMock()
    mock_llm_connector.get_completion.return_value = '{"scenario_name": "cost_reduction_quality_constraint"}'

    scenario_finder = ScenarioFinder(llm_connector=mock_llm_connector)
    mock_request = AnalysisRequest(query="I need to reduce costs but keep quality the same.", user_id="test_user", workloads=[])
    scenario = scenario_finder.find_scenario(mock_request)
    assert scenario["scenario"]["name"] == "Cost Reduction with Quality Constraint"