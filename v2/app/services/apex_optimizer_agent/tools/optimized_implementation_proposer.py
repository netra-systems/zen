from app.services.apex_optimizer_agent.state import AgentState

class OptimizedImplementationProposer:
    def __init__(self, llm_connector: any):
        self.llm_connector = llm_connector

    async def run(self, state: AgentState, function_name: str) -> str:
        """Proposes an optimized implementation for a function."""
        prompt = f"""
        Given the function '{function_name}', propose an optimized implementation.
        Provide the optimized code and an explanation of the changes.
        """
        
        response = await self.llm_connector.get_completion(prompt)
        
        state.messages.append({"message": f"Optimized implementation for {function_name}:\n{response}"})
        return f"Proposed optimized implementation for {function_name}."