from app.services.deep_agent_v3.state import AgentState

class EvaluationCriteriaDefiner:
    async def run(self, state: AgentState, criteria: dict) -> str:
        """Defines the evaluation criteria for new models."""
        state.evaluation_criteria = criteria
        state.messages.append({"message": f"Evaluation criteria defined: {criteria}"})
        return f"Defined evaluation criteria: {criteria}"