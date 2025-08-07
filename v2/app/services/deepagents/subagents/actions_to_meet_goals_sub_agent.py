from app.services.deepagents.sub_agent import SubAgent

class ActionsToMeetGoalsSubAgent(SubAgent):
    def __init__(self, llm_manager, tools):
        super().__init__(
            name="ActionsToMeetGoalsSubAgent",
            description="Formulates tangible actions and changes to meet optimization goals.",
            llm_manager=llm_manager,
            tools=tools,
            sub_agent_type="actions_to_meet_goals"
        )

    def get_initial_prompt(self) -> str:
        return """
        You are the Actions to Meet Goals Sub-Agent. Your role is to formulate tangible actions and changes to meet optimization goals.
        """