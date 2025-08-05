import json
from typing import Any
from app.services.deep_agent_v3.state import AgentState
from app.config import settings

async def dispatch_tool(state: AgentState, llm_connector: Any) -> str:
    """Uses an LLM to decide which tool to use based on the user's request."""
    if not state.request.query:
        return "No query found in the request."

    prompt = f"""
    Given the user query, select the best tool to answer the request.
    User Query: {state.request.query}
    Available Tools: ["cost_reduction_quality_preservation", "tool_latency_optimization", "cost_simulation_for_increased_usage", "advanced_optimization_for_core_function", "new_model_effectiveness_analysis", "kv_cache_optimization_audit", "multi_objective_optimization"]
    Output Format (JSON ONLY):
    {{
        "tool_name": "<selected_tool_name>",
        "arguments": {{<arguments_for_the_tool>}}
    }}
    """

    response_text = await llm_connector.generate_text_async(prompt, settings.google_model.analysis_model, settings.google_model.analysis_model_fallback)
    tool_data = json.loads(response_text)

    state.current_tool_name = tool_data.get("tool_name")
    state.current_tool_args = tool_data.get("arguments")

    return f"Successfully dispatched tool: {state.current_tool_name}"