# netra_apex/governance/human_workflow.py
#
# Implements the human governance workflow for high-stakes decisions.
# Reference: Section 6, Component 3.

import textwrap
from typing import List
from ..models.schemas import WorkloadProfile, ParetoSolution

class HumanGovernanceWorkflow:
    """
    Formalizes the "Human-in-the-Loop" principle by creating an evidence
    package for review and recording the final, accountable decision.
    """
    def __init__(self):
        print("HumanGovernanceWorkflow initialized.")

    def requires_human_review(self, workload: WorkloadProfile, solutions: List[ParetoSolution]) -> bool:
        """
        Determines if a decision needs to be escalated to a human.
        """
        if workload.risk_profile.business_impact_score >= 8:
            print(f"Escalation Trigger: High business impact score ({workload.risk_profile.business_impact_score}).")
            return True
        if len(solutions) > 1:
            # Simplified check for ambiguity: if there's more than one option
            # on the Pareto front, escalate.
            print(f"Escalation Trigger: Ambiguous choice with {len(solutions)} Pareto-optimal solutions.")
            return True
        return False
        
    def present_for_review(self, workload: WorkloadProfile, solutions: List[ParetoSolution], catalog):
        """
        Generates a formatted evidence package for a human reviewer. This would
        be displayed in a UI or sent as a report.
        """
        print("\n" + "="*80)
        print("|| HUMAN GOVERNANCE REVIEW REQUIRED ||".center(80))
        print("="*80)
        print(f"Workload ID: {workload.workload_id}")
        print(f"Application: {workload.metadata.get('app_id')}")
        print(f"Business Impact Score: {workload.risk_profile.business_impact_score}")
        print(f"Prompt Snippet: '{workload.raw_prompt[:100]}...'")
        
        print("\n--- Pareto-Optimal Routing Solutions ---")
        print(f"{ 'Model Name':<35} {'Cost ($)':<10} {'TTFT (ms)':<10} {'TPOT (ms)':<10} {'Risk':<5}")
        print("-"*80)
        for sol in solutions:
            record = catalog.get_supply_record(sol.supply_id)
            print(
                f"{record.model_name:<35} "
                f"${sol.predicted_cost:<9.5f} "
                f"{sol.predicted_ttft_ms_p95:<10.2f} "
                f"{sol.predicted_tpot_ms_p95:<10.2f} "
                f"{sol.predicted_risk_score:<5.2f}"
            )
        print("="*80)

        # In a real system, this would wait for an input. Here we simulate it.
        print("\nSimulating human decision...")
        # A human might choose the balanced option despite a utility function
        # picking the cheapest. We'll simulate picking the one with the lowest risk.
        approved_solution = min(solutions, key=lambda s: s.predicted_risk_score)
        print(f"Decision: Human operator selected the lowest risk option.")
        self.record_decision(workload, approved_solution, "Operator chose lowest risk due to high impact score.")
        return approved_solution

    def record_decision(self, workload: WorkloadProfile, decision: ParetoSolution, justification: str):
        """
        Formally logs the human's decision and justification for audit purposes.
        """
        print("\n--- GOVERNANCE DECISION LOGGED ---")
        print(f"Workload ID: {workload.workload_id}")
        print(f"Approved Supply ID: {decision.supply_id}")
        print(f"Justification: {justification}")
        print("-