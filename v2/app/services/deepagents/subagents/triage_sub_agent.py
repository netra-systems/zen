from app.services.deepagents.sub_agent import SubAgent

class TriageSubAgent(SubAgent):
    def __init__(self, llm_manager, tools):
        super().__init__(
            name="TriageSubAgent",
            description="Triages the user's request and determines the next step.",
            llm_manager=llm_manager,
            tools=tools,
            sub_agent_type="triage"
        )

    def get_initial_prompt(self) -> str:
        return """
        You are the Triage Sub-Agent. Your role is to analyze the user's request and determine the best course of action. 
        Based on the request, decide which Sub-Agent should be activated next. 
        Your analysis should be quick and efficient, focusing on routing the request to the correct specialist Sub-Agent.
        """