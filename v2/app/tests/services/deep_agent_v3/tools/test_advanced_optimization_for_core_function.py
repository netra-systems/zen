
import asyncio
from app.services.deep_agent_v3.tools.advanced_optimization_for_core_function import AdvancedOptimizationForCoreFunctionTool

def test_advanced_optimization_for_core_function_tool():
    """Tests the AdvancedOptimizationForCoreFunctionTool."""
    tool = AdvancedOptimizationForCoreFunctionTool()
    result = asyncio.run(tool.run(function_name="test_function"))
    
    assert "For the core function 'test_function'" in result["message"]
