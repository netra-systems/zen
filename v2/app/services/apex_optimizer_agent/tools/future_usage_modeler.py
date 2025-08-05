from app.services.apex_optimizer_agent.state import AgentState

class FutureUsageModeler:
    async def run(self, state: AgentState, usage_increase_percent: float) -> str:
        """Models the future usage of the system."""
        current_usage = len(state.logs)
        future_usage = current_usage * (1 + usage_increase_percent / 100)
        
        state.messages.append({"message": f"Future usage modeled: {future_usage:.2f} requests"})
        return f"Modeled future usage: {future_usage:.2f} requests"