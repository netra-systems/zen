# netra_apex/main.py
#
# Copyright (C) 2025, netra apex Inc.
#
# Main entry point for simulating the netra apex closed-loop AI workload
# management system. This script orchestrates the entire workflow, from
# receiving a request to executing it and feeding the results back to close
# the loop.

import uuid
from typing import List, Dict, Any

# Core Components
from .core.supply_catalog import SupplyCatalog, populate_initial_catalog
from .core.demand_analyzer import DemandAnalyzer, get_default_config
from .core.controller import MultiObjectiveController
from .core.observability import ObservabilityPlane
from .core.execution_fabric import ExecutionFabric

# Governance Components
from .governance.policy_engine import PolicyEngine
from .governance.human_workflow import HumanGovernanceWorkflow
from .models.schemas import Policy, ParetoSolution, WorkloadProfile, LinguisticFeatures, SLOProfile, RiskProfile

def initialize_system():
    """Initializes all components of the netra apex."""
    print("--- Initializing netra apex System ---")
    
    # Core components
    supply_catalog = SupplyCatalog()
    populate_initial_catalog(supply_catalog)
    
    analyzer_config = get_default_config()
    demand_analyzer = DemandAnalyzer(analyzer_config)
    
    observability_plane = ObservabilityPlane(supply_catalog)
    
    # Pre-populate some baseline performance/quality data
    print("\n--- Running Initial Gauntlet & Seeding Monitoring Data ---")
    for record in supply_catalog.list_all_records():
        # All models must pass the gauntlet to be considered
        observability_plane.run_gauntlet_and_certify(record.supply_id)
        # Seed some initial, plausible data
        observability_plane.process_completed_workload(
            WorkloadProfile(workload_id=uuid.uuid4(), task_vector=[0.1]*384, raw_prompt="seed", linguistic_features=LinguisticFeatures(language="en", has_code=False, domain_jargon=[], prompt_length_tokens=1, prompt_length_chars=4), slo_profile=SLOProfile(), risk_profile=RiskProfile(business_impact_score=1, failure_mode_tags=[])),
            record.supply_id,
            {
                "output_text": "seeded response",
                "metrics": {"ttft_ms": 250, "tpot_ms": 50}
            }
        )
    
    controller = MultiObjectiveController(supply_catalog)
    execution_fabric = ExecutionFabric(observability_plane)
    
    # Governance components
    policy_engine = PolicyEngine()
    policy_engine.add_policy(Policy(
        policy_id="high-risk-guardrail",
        policy_type="RISK_TOLERANCE",
        rules={"impact_threshold": 8, "risk_limit": 4.0}
    ))
    human_workflow = HumanGovernanceWorkflow()
    
    print("\n--- System Initialization Complete ---")
    return {
        "supply_catalog": supply_catalog,
        "demand_analyzer": demand_analyzer,
        "controller": controller,
        "execution_fabric": execution_fabric,
        "policy_engine": policy_engine,
        "human_workflow": human_workflow,
    }

def run_single_workload(system: Dict[str, Any], prompt: str, metadata: Dict[str, Any]):
    """Runs a single, end-to-end workload through the system."""
    
    print("\n" + "#"*80)
    print(f"### Processing new workload for app: {metadata['app_id']} ###".center(80))
    print("#"*80)

    # 1. Demand Analysis: Understand the request
    print("\n[Step 1] Analyzing demand...")
    workload_profile = system["demand_analyzer"].create_workload_profile(prompt, metadata)
    
    # 2. Control: Find the optimal trade-offs
    print("\n[Step 2] Finding Pareto-optimal solutions...")
    pareto_solutions = system["controller"].find_pareto_optimal_solutions(workload_profile)
    if not pareto_solutions:
        print("Execution HALTED: No suitable supply options found.")
        return

    # 3. Governance: Select a decision and get approval
    print("\n[Step 3] Applying governance...")
    final_decision = None
    
    if system["human_workflow"].requires_human_review(workload_profile, pareto_solutions):
        # Escalate to human for review and decision
        final_decision = system["human_workflow"].present_for_review(
            workload_profile, pareto_solutions, system["supply_catalog"]
        )
    else:
        # Use automated selection for low-risk/unambiguous cases
        utility_weights = {"cost": 1.0, "latency": 1.5, "risk": 2.0} # Prioritize risk & latency
        final_decision = system["controller"].select_decision(pareto_solutions, utility_weights)
        print(f"Automated selection chose supply ID: {final_decision.supply_id}")

    if not final_decision:
        print("Execution HALTED: No decision was made.")
        return

    # 3a. Policy Check: Ensure the final decision is compliant
    if not system["policy_engine"].validate_decision(workload_profile, final_decision):
        print("Execution HALTED: Final decision violates system policy.")
        return
        
    # 4. Execution: Run the workload on the approved supply option
    print("\n[Step 4] Executing workload...")
    chosen_supply_record = system["supply_catalog"].get_supply_record(final_decision.supply_id)
    system["execution_fabric"].execute_workload(workload_profile, chosen_supply_record)
    
    print("\n--- Workload Processing Complete ---")

if __name__ == "__main__":
    netra_apex_system = initialize_system()
    
    # --- Simulation Run 1: High-risk, high-impact query ---
    high_risk_prompt = "What are the potential side effects of metformin for treating type 2 diabetes?"
    high_risk_metadata = {"app_id": "medical-qa", "user_id": "user-444"}
    run_single_workload(netra_apex_system, high_risk_prompt, high_risk_metadata)
    
    # --- Simulation Run 2: Low-risk, cost-sensitive query ---
    low_risk_prompt = "Write a short, upbeat marketing email for a new brand of coffee."
    low_risk_metadata = {"app_id": "batch-summarizer", "user_id": "marketing-intern-02"}
    run_single_workload(netra_apex_system, low_risk_prompt, low_risk_metadata)
