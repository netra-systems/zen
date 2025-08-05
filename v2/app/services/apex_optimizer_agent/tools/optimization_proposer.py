from app.services.apex_optimizer_agent.state import AgentState

class OptimizationProposer:
    def __init__(self, policy_proposer: any):
        self.policy_proposer = policy_proposer

    async def run(self, state: AgentState) -> str:
        """Proposes optimizations to reduce costs or latency."""
        policies, outcomes = await self.policy_proposer.propose_policies(state.discovered_patterns, state.span_map)
        state.learned_policies = policies
        state.predicted_outcomes = outcomes
        
        state.messages.append({"message": f"Proposed {len(policies)} optimizations."})
        return f"Proposed {len(policies)} optimizations."