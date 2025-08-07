from app.services.deepagents.sub_agent import SubAgent

class ReportingSubAgent(SubAgent):
    def __init__(self, llm_manager, tools):
        super().__init__(
            name="ReportingSubAgent",
            description="Summarizes the overall results and reports them to the user.",
            llm_manager=llm_manager,
            tools=tools,
            sub_agent_type="reporting"
        )

    def get_initial_prompt(self) -> str:
        return """
        You are the Reporting Sub-Agent. Your role is to summarize the overall results and report them to the user.
        """