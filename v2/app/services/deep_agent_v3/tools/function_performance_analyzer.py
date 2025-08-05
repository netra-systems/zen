from app.services.deep_agent_v3.state import AgentState

class FunctionPerformanceAnalyzer:
    def __init__(self, performance_predictor: any):
        self.performance_predictor = performance_predictor

    async def run(self, state: AgentState, function_name: str) -> str:
        """Analyzes the performance of a specific function."""
        total_latency = 0
        function_logs = [log for log in state.logs if function_name in log.request.prompt_text]
        
        if not function_logs:
            return f"No logs found for function: {function_name}"
        
        for log in function_logs:
            latency_result = await self.performance_predictor.execute(log.request.prompt_text, log.model_dump())
            total_latency += latency_result["predicted_latency_ms"]
        
        average_latency = total_latency / len(function_logs)
        
        state.messages.append({"message": f"Average predicted latency for {function_name}: {average_latency:.2f}ms"})
        return f"Analyzed function performance for {function_name}. Average predicted latency: {average_latency:.2f}ms"