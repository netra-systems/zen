import json
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
        Selects the best scenario based on the user's prompt using a language model,
        providing a confidence score and justification.
        """
        scenario_descriptions = self._get_scenario_descriptions()
        system_prompt = f"""
You are an expert scenario router for a system that analyzes and optimizes LLM usage.
Your task is to select the most appropriate scenario from the list below based on the user's request.

You must respond in JSON format with the following three keys:
1.  "scenario_name": The name of the best matching scenario (e.g., "cost_reduction_quality_constraint").
2.  "confidence": A float between 0.0 and 1.0, representing your confidence in the selection.
3.  "justification": A brief explanation for your choice.

Available Scenarios:
{scenario_descriptions}
"""
        try:
            response_text = self.llm_connector.get_completion(
                prompt=prompt,
                system_prompt=system_prompt
            )
            
            response_data = json.loads(response_text)
            scenario_name = response_data.get("scenario_name")
            
            if scenario_name in SCENARIOS:
                return {
                    "scenario": SCENARIOS[scenario_name],
                    "confidence": response_data.get("confidence", 0.0),
                    "justification": response_data.get("justification", "No justification provided.")
                }
            else:
                # Fallback for cases where the model's output is not a perfect key match
                for key in SCENARIOS:
                    if key in str(scenario_name).lower().replace(" ", "_"):
                        return {
                            "scenario": SCENARIOS[key],
                            "confidence": response_data.get("confidence", 0.5), # Lower confidence on fallback
                            "justification": f"Fallback match: {response_data.get('justification', 'No justification provided.')}"
                        }

        except Exception as e:
            print(f"Error during scenario finding: {e}")
            # Fallback to a generic scenario in case of errors
        
        return {
            "scenario": {
                "name": "Generic Optimization",
                "description": "A generic optimization scenario for when a specific one cannot be determined.",
                "steps": [
                    "analyze_request",
                    "propose_solution",
                    "generate_report"
                ]
            },
            "confidence": 0.1,
            "justification": "An error occurred during scenario selection, falling back to generic optimization."
        }
