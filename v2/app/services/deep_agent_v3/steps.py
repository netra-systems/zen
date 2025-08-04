import json
from typing import List, Dict, Any

from app.services.deep_agent_v3.core import (
    query_raw_logs,
    enrich_and_cluster_logs,
    propose_optimal_policies,
)
from app.services.deep_agent_v3.state import AgentState
from app.services.deep_agent_v3.tools import (
    cost_reduction_quality_preservation,
    tool_latency_optimization,
    cost_simulation_for_increased_usage,
    advanced_optimization_for_core_function,
    new_model_effectiveness_analysis,
    kv_cache_optimization_audit,
)
from app.config import settings

async def _step_1_fetch_raw_logs(state: AgentState, db_session: Any) -> str:
    """Fetches raw log data from the user's ClickHouse database."""
    state.raw_logs = await query_raw_logs(
        db_session=db_session,
        source_table=state.request.data_source.source_table,
        start_time=state.request.time_range.start_time,
        end_time=state.request.time_range.end_time,
        filters=state.request.data_source.filters,
    )
    return f"Fetched {len(state.raw_logs)} log entries."

async def _step_2_enrich_and_cluster(state: AgentState, llm_connector: Any) -> str:
    """Enriches logs and clusters them to find usage patterns."""
    if not state.raw_logs:
        raise ValueError("Cannot perform clustering without raw logs.")

    state.patterns = await enrich_and_cluster_logs(
        spans=state.raw_logs,
        llm_connector=llm_connector,
    )
    return f"Discovered {len(state.patterns)} usage patterns."

async def _step_3_propose_optimal_policies(state: AgentState, db_session: Any, llm_connector: Any) -> str:
    """Simulates outcomes and proposes optimal routing policies."""
    if not state.patterns:
        raise ValueError("Cannot propose policies without discovered patterns.")

    span_map = {span.trace_context.span_id: span for span in state.raw_logs}
    state.policies = await propose_optimal_policies(
        db_session=db_session,
        patterns=state.patterns,
        span_map=span_map,
        llm_connector=llm_connector,
    )
    return f"Generated {len(state.policies)} optimal policies."

async def _step_4_dispatch_tool(state: AgentState, llm_connector: Any) -> str:
    """Uses an LLM to decide which tool to use based on the user's request."""
    if not state.request.query:
        return "No query provided, skipping tool dispatch."

    tools = [
        cost_reduction_quality_preservation,
        tool_latency_optimization,
        cost_simulation_for_increased_usage,
        advanced_optimization_for_core_function,
        new_model_effectiveness_analysis,
        kv_cache_optimization_audit,
    ]

    tool_defs = [
        {
            "name": tool.__name__,
            "description": tool.__doc__,
            "parameters": tool.__annotations__,
        }
        for tool in tools
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
        
        tool_to_call = next((tool for tool in tools if tool.__name__ == tool_name), None)

        if tool_to_call:
            state.tool_result = tool_to_call(**arguments)
            return f"Executed tool: {tool_name}"
    
    return "No suitable tool found."

async def _step_5_generate_final_report(state: AgentState) -> str:
    """Generates a human-readable summary of the analysis."""
    if not state.policies:
        raise ValueError("Cannot generate a report without policies.")
        
    report = "Analysis Complete. Recommended Policies:\n"
    for policy in state.policies:
        report += f"- For pattern '{policy.pattern_name}', recommend using '{policy.optimal_supply_option_name}'.\n"
    
    if state.tool_result:
        report += "\nTool Execution Result:\n"
        report += json.dumps(state.tool_result, indent=2)

    state.final_report = report
    return "Final report generated."
