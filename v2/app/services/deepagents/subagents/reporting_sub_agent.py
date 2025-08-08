from app.services.deepagents.sub_agent import SubAgent

class ReportingSubAgent(SubAgent):
    @property
    def name(self) -> str:
        return "ReportingSubAgent"

    @property
    def description(self) -> str:
        return "This agent is responsible for generating and delivering reports."

    async def ainvoke(self, state):
        # Placeholder for reporting logic
        state["current_agent"] = "__end__"
        return state
