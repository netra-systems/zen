
class CostAnalyzer:
    def __init__(self, cost_estimator: any):
        self.cost_estimator = cost_estimator

    async def run(self, logs: list) -> str:
        """Analyzes the current costs of the system."""
        total_cost = 0
        for log in logs:
            cost_result = await self.cost_estimator.execute(log.request.prompt_text, log.model_dump())
            total_cost += cost_result["estimated_cost_usd"]
        
        return f"Analyzed current costs. Total estimated cost: ${total_cost:.2f}"