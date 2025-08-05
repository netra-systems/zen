from typing import Any, Dict
from app.services.deep_agent_v3.state import AgentState

async def propose_optimal_policies(state: AgentState, policy_proposer: Any) -> str:
    """
    Proposes optimal policies based on the clustered logs.
    """
    if not state.patterns:
        return "Error: patterns is not available."

    policies = await policy_proposer.propose_policies(state.patterns)
    state.policies = policies
    return "Optimal policies proposed."