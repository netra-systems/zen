"""Test file with incorrect SupplyResearcherAgent imports to test the fix script."""

# This should be fixed by the script
from netra_backend.app.agents.corpus_admin.agent import SupplyResearcherAgent

# This should also be fixed
from netra_backend.app.agents.supply_researcher_sub_agent import SupplyResearcherAgent as SubAgent

# This should be standardized to module level
from netra_backend.app.agents.supply_researcher.agent import SupplyResearcherAgent as DirectAgent

def test_agent():
    """Test function using the agents."""
    agent = SupplyResearcherAgent(None, None)
    sub_agent = SubAgent(None, None)
    direct_agent = DirectAgent(None, None)
    return agent, sub_agent, direct_agent