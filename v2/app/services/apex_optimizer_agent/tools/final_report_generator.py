from langchain_core.tools import tool
import json

@tool
async def final_report_generator(learned_policies: list, predicted_outcomes: list) -> str:
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