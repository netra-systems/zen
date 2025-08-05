from app.services.apex_optimizer_agent.state import AgentState

class OptimizationMethodResearcher:
    def __init__(self, llm_connector: any):
        self.llm_connector = llm_connector

    async def run(self, state: AgentState, function_name: str) -> str:
        """Researches advanced optimization methods for a function."""
        prompt = f'''
        Research and suggest advanced optimization methods for the function '{function_name}'.
        '''
        
        response = await self.llm_connector.get_completion(prompt)
        
        state.messages.append({"message": f"Optimization methods for {function_name}:\n{response}"})
        return f"Researched optimization methods for {function_name}."
