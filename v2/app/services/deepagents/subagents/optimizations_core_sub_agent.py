from app.services.deepagents.sub_agent import SubAgent

class OptimizationsCoreSubAgent(SubAgent):
    @property
    def name(self) -> str:
        return "OptimizationsCoreSubAgent"

    @property
    def description(self) -> str:
        return "This agent is responsible for performing optimizations."

    async def ainvoke(self, state):
        # Placeholder for optimization logic
        state["current_agent"] = "ActionsToMeetGoalsSubAgent"
        return state