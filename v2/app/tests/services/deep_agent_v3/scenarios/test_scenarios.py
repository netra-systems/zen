import json
from unittest.mock import MagicMock
from app.llm.llm_manager import LLMManager
from app.services.deep_agent_v3.scenario_finder import ScenarioFinder
from app.db.models_clickhouse import AnalysisRequest

def test_get_scenario():
    """Tests the get_scenario function."""
    mock_llm_manager = MagicMock(spec=LLMManager)
    mock_llm_manager.get_llm.return_value.invoke.return_value.content = '{"scenario_name": "cost_reduction_quality_constraint"}'

    scenario_finder = ScenarioFinder(llm_manager=mock_llm_manager)
    mock_request = AnalysisRequest(query="I need to reduce costs but keep quality the same.", user_id="test_user", workloads=[])
    scenario = scenario_finder.find_scenario(mock_request)
    assert scenario["scenario"]["name"] == "Cost Reduction with Quality Constraint"