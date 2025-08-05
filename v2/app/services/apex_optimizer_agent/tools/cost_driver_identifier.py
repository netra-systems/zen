from app.services.apex_optimizer_agent.state import AgentState

class CostDriverIdentifier:
    def __init__(self, cost_estimator: any):
        self.cost_estimator = cost_estimator

    async def run(self, state: AgentState) -> str:
        """Identifies the main drivers of cost in the system."""
        cost_drivers = {}
        for log in state.logs:
            cost_result = await self.cost_estimator.execute(log.request.prompt_text, log.model_dump())
            prompt_category = log.request.prompt_text.split(" ")[0] # Simple categorization by first word
            if prompt_category not in cost_drivers:
                cost_drivers[prompt_category] = 0
            cost_drivers[prompt_category] += cost_result["estimated_cost_usd"]
        
        sorted_cost_drivers = sorted(cost_drivers.items(), key=lambda item: item[1], reverse=True)
        
        state.messages.append({"message": f"Cost drivers identified: {sorted_cost_drivers}"})
        return f"Identified cost drivers: {sorted_cost_drivers}"