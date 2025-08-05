
class LatencyBottleneckIdentifier:
    def __init__(self, performance_predictor: any):
        self.performance_predictor = performance_predictor

    async def run(self, logs: list) -> str:
        """Identifies the main latency bottlenecks in the system."""
        latency_bottlenecks = {}
        for log in logs:
            latency_result = await self.performance_predictor.execute(log.request.prompt_text, log.model_dump())
            prompt_category = log.request.prompt_text.split(" ")[0] # Simple categorization by first word
            if prompt_category not in latency_bottlenecks:
                latency_bottlenecks[prompt_category] = []
            latency_bottlenecks[prompt_category].append(latency_result["predicted_latency_ms"])
        
        avg_latency_bottlenecks = {k: sum(v) / len(v) for k, v in latency_bottlenecks.items()}
        sorted_latency_bottlenecks = sorted(avg_latency_bottlenecks.items(), key=lambda item: item[1], reverse=True)
        
        return f"Identified latency bottlenecks: {sorted_latency_bottlenecks}"