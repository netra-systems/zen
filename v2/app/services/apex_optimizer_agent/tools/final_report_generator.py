from langchain_core.tools import tool
from typing import List
from pydantic import BaseModel, Field

class LearnedPolicy(BaseModel):
    pattern_name: str = Field(..., description="The name of the pattern.")
    optimal_supply_option_name: str = Field(..., description="The name of the optimal supply option.")

class PredictedOutcome(BaseModel):
    supply_option_name: str = Field(..., description="The name of the supply option.")
    explanation: str = Field(..., description="The explanation of the outcome.")

@tool
async def final_report_generator(learned_policies: List[LearnedPolicy], predicted_outcomes: List[PredictedOutcome], db_session: Any, llm_manager: Any) -> str:
    """Generates a human-readable summary of the analysis."""
    if not learned_policies:
        raise ValueError("Cannot generate a report without learned policies.")
        
    report = "Analysis Complete. Recommended Policies:\n"
    for policy in learned_policies:
        report += f"- For pattern '{policy.pattern_name}', recommend using '{policy.optimal_supply_option_name}'.\n"
    
    if predicted_outcomes:
        report += "\nPredicted Outcomes:\n"
        for outcome in predicted_outcomes:
            report += f"- {outcome.supply_option_name}: {outcome.explanation}\n"

    return report
