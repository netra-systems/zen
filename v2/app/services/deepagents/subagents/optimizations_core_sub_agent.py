from app.services.deepagents.sub_agent import SubAgent

class OptimizationsCoreSubAgent(SubAgent):
    def __init__(self, llm_manager, tools):
        super().__init__(
            name="OptimizationsCoreSubAgent",
            description="The core of the optimization process. Analyzes data and proposes optimizations.",
            llm_manager=llm_manager,
            tools=tools,
            sub_agent_type="optimizations_core"
        )

    def get_initial_prompt(self) -> str:
        return """
        You are the Optimizations Core Sub-Agent. You are the heart of the optimization engine. 
        Your task is to analyze the data provided by the Data Sub-Agent and identify potential optimizations. 
        Use your analytical capabilities to devise strategies that will improve performance, reduce costs, or meet other user-defined goals.
        """