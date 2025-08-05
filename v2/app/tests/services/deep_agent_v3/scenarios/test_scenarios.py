
from app.services.deep_agent_v3.scenario_finder import get_scenario

def test_get_scenario():
    """Tests the get_scenario function."""
    scenario = get_scenario("I need to reduce costs but keep quality the same.")
    assert scenario["name"] == "Cost Reduction with Quality Constraint"
