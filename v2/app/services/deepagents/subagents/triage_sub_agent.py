from app.services.deepagents.sub_agent import SubAgent

class TriageSubAgent(SubAgent):
    @property
    def name(self) -> str:
        return "TriageSubAgent"

    @property
    def description(self) -> str:
        return "This agent is responsible for triaging incoming requests and routing them to the appropriate sub-agent."

    async def ainvoke(self, state):
        # Placeholder for triage logic
        state["current_agent"] = "DataSubAgent"
        return state
