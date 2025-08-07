from app.services.deepagents.sub_agent import SubAgent

class OptimizationsCoreSubAgent(SubAgent):
    def __init__(self, llm_manager, tools):
        super().__init__(
            name="OptimizationsCoreSubAgent",
            description="Analyzes data and formulates optimization strategies.",
            llm_manager=llm_manager,
            tools=tools,
            sub_agent_type="optimizations_core"
        )

    def get_initial_prompt(self) -> str:
        return """
        You are the Optimizations Core Sub-Agent. Your role is to analyze data and formulate optimization strategies.
        """