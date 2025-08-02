# app/services/demo_agent.py

from app.deepagents import create_deep_agent, DeepAgentState
from app.services.demo_tools import (
    cost_reduction_quality_preservation,
    tool_latency_optimization,
    cost_simulation_for_increased_usage,
    advanced_optimization_for_core_function,
    new_model_effectiveness_analysis,
    kv_cache_optimization_audit,
)

def create_demo_agent(debug_mode: bool = False):
    """Creates a deep agent specifically for the demo."""

    tools = [
        cost_reduction_quality_preservation,
        tool_latency_optimization,
        cost_simulation_for_increased_usage,
        advanced_optimization_for_core_function,
        new_model_effectiveness_analysis,
        kv_cache_optimization_audit,
    ]

    instructions = """
    You are a helpful assistant designed to answer questions about optimizing LLM usage.
    Use the available tools to answer the user's questions.
    """

    agent = create_deep_agent(tools=tools, instructions=instructions, state_schema=DeepAgentState if debug_mode else None)

    return agent
