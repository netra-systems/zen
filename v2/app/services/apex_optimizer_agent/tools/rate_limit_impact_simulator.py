from app.services.apex_optimizer_agent.state import AgentState

class RateLimitImpactSimulator:
    def __init__(self, llm_connector: any):
        self.llm_connector = llm_connector

    async def run(self, state: AgentState, usage_increase_percent: float) -> str:
        """Simulates the impact of usage increase on rate limits."""
        prompt = f"""
        Given a {usage_increase_percent}% increase in agent usage, how will this impact my costs and rate limits?
        Current usage is {len(state.logs)} requests.
        """
        
        response = await self.llm_connector.get_completion(prompt)
        
        state.messages.append({"message": f"Impact on rate limits:\n{response}"})
        return f"Simulated impact on rate limits."
