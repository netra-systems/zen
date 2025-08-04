from app.services.deep_agent_v3.core import simulate_policy_outcome

class PolicySimulator:
    def __init__(self, llm_connector):
        self.llm_connector = llm_connector

    async def execute(self, policy: dict):
        return await simulate_policy_outcome(policy, self.llm_connector)