from app.services.deepagents.sub_agent import SubAgent

class DataSubAgent(SubAgent):
    @property
    def name(self) -> str:
        return "DataSubAgent"

    @property
    def description(self) -> str:
        return "This agent is responsible for collecting and processing data."

    async def ainvoke(self, state):
        # Placeholder for data processing logic
        state["current_agent"] = "OptimizationsCoreSubAgent"
        return state