
class EvaluationCriteriaDefiner:
    async def run(self, criteria: dict) -> str:
        """Defines the evaluation criteria for new models."""
        return f"Defined evaluation criteria: {criteria}"