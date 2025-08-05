
from app.services.deep_agent_v3.tools.new_model_effectiveness_analysis import NewModelEffectivenessAnalysisTool

def test_new_model_effectiveness_analysis_tool():
    """Tests the NewModelEffectivenessAnalysisTool."""
    tool = NewModelEffectivenessAnalysisTool()
    result = tool.run(new_models=["gpt-4o", "claude-3-sonnet"])
    
    assert "The new models gpt-4o, claude-3-sonnet have been analyzed" in result["message"]
