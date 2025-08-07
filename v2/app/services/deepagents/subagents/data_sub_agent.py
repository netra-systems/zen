from app.services.deepagents.sub_agent import SubAgent

class DataSubAgent(SubAgent):
    def __init__(self, llm_manager, tools):
        super().__init__(
            name="DataSubAgent",
            description="Gathers and enriches data for the optimization process.",
            llm_manager=llm_manager,
            tools=tools,
            sub_agent_type="data"
        )

    def get_initial_prompt(self) -> str:
        return """
        You are the Data Sub-Agent. Your responsibility is to gather all necessary data to address the user's request. 
        This may involve querying databases, fetching logs, or using other data-related tools. 
        Ensure the data is clean, relevant, and ready for the next stage of the optimization process.
        """