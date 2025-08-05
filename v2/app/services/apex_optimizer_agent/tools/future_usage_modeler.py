
class FutureUsageModeler:
    async def run(self, logs: list, usage_increase_percent: float) -> str:
        """Models the future usage of the system."""
        current_usage = len(logs)
        future_usage = current_usage * (1 + usage_increase_percent / 100)
        
        return f"Modeled future usage: {future_usage:.2f} requests"