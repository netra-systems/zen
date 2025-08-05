
class OptimizationProposer:
    def __init__(self, policy_proposer: any):
        self.policy_proposer = policy_proposer

    async def run(self, discovered_patterns: list, span_map: dict) -> str:
        """Proposes optimizations to reduce costs or latency."""
        policies, outcomes = await self.policy_proposer.propose_policies(discovered_patterns, span_map)
        return f"Proposed {len(policies)} optimizations."