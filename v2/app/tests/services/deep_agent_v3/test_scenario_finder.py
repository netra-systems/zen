import pytest
from app.llm.llm_manager import LLMManager
from unittest.mock import MagicMock

from app.services.deep_agent_v3.scenario_finder import ScenarioFinder
from app.db.models_clickhouse import AnalysisRequest

@pytest.fixture
def mock_llm_manager_for_scenario_finder():
    """Provides a mock LLM manager that returns a specific scenario."""
    llm_manager = MagicMock(spec=LLMManager)
    llm_manager.get_llm.return_value.invoke.return_value.content = '{"scenario_name": "cost_reduction_quality_constraint"}'
    return llm_manager

def test_scenario_finder_finds_correct_scenario(mock_llm_manager_for_scenario_finder):
    """Tests that the ScenarioFinder correctly identifies the scenario from the LLM response."""
    # Arrange
    scenario_finder = ScenarioFinder(llm_manager=mock_llm_manager_for_scenario_finder)
    mock_request = AnalysisRequest(query="I need to reduce costs but keep quality the same.", user_id="test_user", workloads=[])

    # Act
    scenario = scenario_finder.find_scenario(mock_request)

    # Assert
    assert scenario["scenario"]["name"] == "Cost Reduction with Quality Constraint"
    assert "analyze_current_costs" in scenario["scenario"]["steps"]