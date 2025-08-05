import pytest

from app.services.deep_agent_v3.steps.generate_final_report import generate_final_report
from app.services.deep_agent_v3.state import AgentState

@pytest.mark.asyncio
async def test_generate_final_report():
    """Tests the generate_final_report step."""
    state = AgentState(policies=[])
    
    result = await generate_final_report(state)
    
    assert result == "Final report generated."
    assert state.final_report == "Analysis Complete. Recommended Policies:\n"