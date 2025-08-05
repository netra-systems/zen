
class LatencyAnalyzer:
    def __init__(self, performance_predictor: any):
        self.performance_predictor = performance_predictor

    async def run(self, logs: list) -> str:
        """Analyzes the current latency of the system."""
        total_latency = 0
        for log in logs:
            latency_result = await self.performance_predictor.execute(log.request.prompt_text, log.model_dump())
            total_latency += latency_result["predicted_latency_ms"]
        
        average_latency = total_latency / len(logs) if logs else 0
        
        return f"Analyzed current latency. Average predicted latency: {average_latency:.2f}ms"