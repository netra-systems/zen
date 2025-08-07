from app.services.deepagents.sub_agent import SubAgent

class ReportingSubAgent(SubAgent):
    def __init__(self, llm_manager, tools):
        super().__init__(
            name="ReportingSubAgent",
            description="Summarizes the results of the optimization process and reports back to the user.",
            llm_manager=llm_manager,
            tools=tools,
            sub_agent_type="reporting"
        )

    def get_initial_prompt(self) -> str:
        return """
        You are the Reporting Sub-Agent. Your final duty is to compile a comprehensive report of the optimization process. 
        This report should summarize the initial request, the data gathered, the optimizations proposed, and the expected outcomes. 
        Present the information in a clear and easily understandable format for the user.
        """