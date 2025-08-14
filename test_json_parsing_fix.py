"""Test for JSON parsing fix in LLM manager"""
import asyncio
import json
from app.llm.llm_manager import LLMManager
from app.agents.triage.models import TriageResult

async def test_nested_json_parsing():
    """Test that nested JSON strings are properly parsed"""
    
    # Initialize LLM manager with settings
    from app.settings import Settings
    settings = Settings()
    llm_manager = LLMManager(settings)
    
    # Test data with nested JSON strings (simulating what the LLM might return)
    test_data = {
        "category": "Cost Optimization",
        "secondary_categories": [],
        "confidence_score": 0.9,
        "priority": "high",
        "complexity": "moderate",
        "tool_recommendations": [
            {
                "tool_name": "latency_reducer",
                "relevance_score": 0.95,
                "parameters": '{"latency_reduction_factor": 0.2, "cost_constraint": "no_increase"}'  # JSON string
            },
            {
                "tool_name": "monitor_metric",
                "relevance_score": 0.8,
                "parameters": '{"metric": "latency"}'  # JSON string
            },
            {
                "tool_name": "report_generator",
                "relevance_score": 0.7,
                "parameters": '{}'  # Empty JSON string
            }
        ]
    }
    
    # Test the _parse_nested_json method
    parsed_data = llm_manager._parse_nested_json(test_data)
    
    # Verify that parameters are now dictionaries
    assert isinstance(parsed_data["tool_recommendations"][0]["parameters"], dict)
    assert parsed_data["tool_recommendations"][0]["parameters"]["latency_reduction_factor"] == 0.2
    assert parsed_data["tool_recommendations"][0]["parameters"]["cost_constraint"] == "no_increase"
    
    assert isinstance(parsed_data["tool_recommendations"][1]["parameters"], dict)
    assert parsed_data["tool_recommendations"][1]["parameters"]["metric"] == "latency"
    
    assert isinstance(parsed_data["tool_recommendations"][2]["parameters"], dict)
    assert parsed_data["tool_recommendations"][2]["parameters"] == {}
    
    # Now verify it works with TriageResult
    try:
        result = TriageResult(**parsed_data)
        print("✓ Successfully created TriageResult with parsed nested JSON")
        print(f"  Tool recommendations: {len(result.tool_recommendations)}")
        for i, tool in enumerate(result.tool_recommendations):
            print(f"    {i+1}. {tool.tool_name}: parameters={tool.parameters}")
        return True
    except Exception as e:
        print(f"✗ Failed to create TriageResult: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_nested_json_parsing())
    if success:
        print("\n✅ JSON parsing fix is working correctly!")
    else:
        print("\n❌ JSON parsing fix failed")