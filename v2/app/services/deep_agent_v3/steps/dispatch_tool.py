
import json
from typing import Any

from app.services.deep_agent_v3.state import AgentState
from app.services.deep_agent_v3.tools.cost_reduction_quality_preservation import CostReductionQualityPreservationTool
from app.services.deep_agent_v3.tools.tool_latency_optimization import ToolLatencyOptimizationTool
from app.services.deep_agent_v3.tools.cost_simulation_for_increased_usage import CostSimulationForIncreasedUsageTool
from app.services.deep_agent_v3.tools.advanced_optimization_for_core_function import AdvancedOptimizationForCoreFunctionTool
from app.services.deep_agent_v3.tools.new_model_effectiveness_analysis import NewModelEffectivenessAnalysisTool
from app.services.deep_agent_v3.tools.kv_cache_optimization_audit import KVCacheOptimizationAuditTool
from app.config import settings

async def dispatch_tool(state: AgentState, llm_connector: Any) -> str:
    """Uses an LLM to decide which tool to use based on the user's request."""
    if not state.request.query:
        return "No query provided, skipping tool dispatch."

    tools = {
        "cost_reduction_quality_preservation": CostReductionQualityPreservationTool(),
        "tool_latency_optimization": ToolLatencyOptimizationTool(),
        "cost_simulation_for_increased_usage": CostSimulationForIncreasedUsageTool(),
        "advanced_optimization_for_core_function": AdvancedOptimizationForCoreFunctionTool(),
        "new_model_effectiveness_analysis": NewModelEffectivenessAnalysisTool(),
        "kv_cache_optimization_audit": KVCacheOptimizationAuditTool(),
    }

    tool_defs = [
        {
            "name": name,
            "description": tool.run.__doc__,
            "parameters": tool.run.__annotations__,
        }
        for name, tool in tools.items()
    ]

    prompt = f"""
    Given the user's query, which of the following tools should be used?
    User Query: {state.request.query}
    Available Tools: {json.dumps(tool_defs, indent=2)}
    
    Respond with a JSON object containing the tool name and its arguments.
    Example: {{'tool_name': 'cost_reduction_quality_preservation', 'arguments': {{'feature_x_latency': 500, 'feature_y_latency': 200}}}}
    """
    
    response_text = await llm_connector.generate_text_async(prompt, settings.analysis_model, settings.analysis_model_fallback)
    tool_call = json.loads(response_text) if response_text else {}

    if tool_call and "tool_name" in tool_call:
        tool_name = tool_call["tool_name"]
        arguments = tool_call.get("arguments", {})
        
        if tool_name in tools:
            tool_to_call = tools[tool_name]
            state.tool_result = tool_to_call.run(**arguments)
            return f"Executed tool: {tool_name}"
    
    return "No suitable tool found."
