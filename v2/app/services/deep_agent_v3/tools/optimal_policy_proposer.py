from typing import Any, Dict
from app.services.deep_agent_v3.state import AgentState

class OptimalPolicyProposer:
    def __init__(self, policy_proposer: any):
        self.policy_proposer = policy_proposer

    async def run(self, state: AgentState) -> str:
        """
        Proposes optimal policies based on the clustered logs.
        """
        if not state.patterns:
            return "Error: patterns is not available."

        policies = await self.policy_proposer.propose_policies(state.patterns)
        state.policies = policies
        return "Optimal policies proposed."