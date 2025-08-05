from typing import Dict, Any, List
from app.services.deep_agent_v3.scenarios import SCENARIOS

class ScenarioFinder:
    def __init__(self, llm_connector: Any):
        self.llm_connector = llm_connector

    def _get_scenario_descriptions(self) -> str:
        """Formats scenario descriptions for the language model."""
        return "\n".join([
            f"- {name}: {details['description']}"
            for name, details in SCENARIOS.items()
        ])

    def find_scenario(self, prompt: str) -> Dict[str, Any]:
        """
        Selects the best scenario based on the user's prompt using a language model.
        """
        scenario_descriptions = self._get_scenario_descriptions()
        system_prompt = f"""
You are a scenario router for a system that analyzes and optimizes LLM usage.
Your task is to select the most appropriate scenario from the list below based on the user's request.
Respond with only the name of the best matching scenario (e.g., "cost_reduction_quality_constraint").

Available Scenarios:
{scenario_descriptions}
"""
        try:
            response = self.llm_connector.get_completion(
                prompt=prompt,
                system_prompt=system_prompt
            )
            
            # Basic validation to ensure the response is a valid scenario key
            if response in SCENARIOS:
                return SCENARIOS[response]
            else:
                # Fallback for cases where the model's output is not a perfect key match
                for key in SCENARIOS:
                    if key in response.lower().replace(" ", "_"):
                        return SCENARIOS[key]

        except Exception as e:
            print(f"Error during scenario finding: {e}")
            # Fallback to a generic scenario in case of errors
        
        return {
            "name": "Generic Optimization",
            "description": "A generic optimization scenario for when a specific one cannot be determined.",
            "steps": [
                "analyze_request",
                "propose_solution",
                "generate_report"
            ]
        }