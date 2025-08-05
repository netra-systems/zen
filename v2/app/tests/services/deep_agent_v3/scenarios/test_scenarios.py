from unittest.mock import MagicMock
from app.services.deep_agent_v3.scenario_finder import ScenarioFinder

def test_get_scenario():
    """Tests the get_scenario function."""
    mock_llm_connector = MagicMock()
    mock_llm_connector.get_completion.return_value = '{"scenario": {"name": "cost_reduction_quality_constraint"}}'

    scenario_finder = ScenarioFinder(llm_connector=mock_llm_connector)
    scenario = scenario_finder.find_scenario("I need to reduce costs but keep quality the same.")
    assert scenario["scenario"]["name"] == "cost_reduction_quality_constraint"
