import json

from app.services.deep_agent_v3.state import AgentState

class FinalReportGenerator:
    async def run(self, state: AgentState) -> str:
        """Generates a human-readable summary of the analysis."""
        if not state.learned_policies:
            raise ValueError("Cannot generate a report without learned policies.")
            
        report = "Analysis Complete. Recommended Policies:\n"
        for policy in state.learned_policies:
            report += f"- For pattern '{policy.pattern_name}', recommend using '{policy.optimal_supply_option_name}'.\n"
        
        if state.predicted_outcomes:
            report += "\nPredicted Outcomes:\n"
            for outcome in state.predicted_outcomes:
                report += f"- {outcome.supply_option_name}: {outcome.explanation}\n"

        state.final_report = report
        return "Final report generated."
