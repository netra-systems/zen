
from app.services.deep_agent_v3.state import AgentState
from app.services.deep_agent_v3.tools.policy_proposer import PolicyProposer

async def propose_optimal_policies(state: AgentState, tool: PolicyProposer) -> str:
    """Proposes optimal policies based on the identified patterns."""
    state.policies = await tool.execute(state.patterns, state.span_map)
    return f"Proposed {len(state.policies)} policies."
