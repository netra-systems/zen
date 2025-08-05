from app.services.deep_agent_v3.state import AgentState

async def propose_optimizations(state: AgentState, policy_proposer: any) -> str:
    """Proposes optimizations to reduce costs or latency."""
    policies, outcomes = await policy_proposer.propose_policies(state.discovered_patterns, state.span_map)
    state.learned_policies = policies
    state.predicted_outcomes = outcomes
    
    state.messages.append({"message": f"Proposed {len(policies)} optimizations."})
    return f"Proposed {len(policies)} optimizations."