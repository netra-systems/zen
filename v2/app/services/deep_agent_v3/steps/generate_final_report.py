import json

from app.services.deep_agent_v3.state import AgentState

async def generate_final_report(state: AgentState) -> str:
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