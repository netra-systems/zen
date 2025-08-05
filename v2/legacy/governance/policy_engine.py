# netra_apex/governance/policy_engine.py
#
# Copyright (C) 2025, netra apex Inc.
#
# Implements the Policy Engine, a centralized administrative console for defining
# global rules and guardrails that the system must obey.
# Reference: Section 6, Component 1.

from typing import List, Dict, Any

from ..models.schemas import WorkloadProfile, ParetoSolution, Policy

class PolicyEngine:
    """
    Enforces global policies, ensuring optimizations align with strategic goals.
    """
    def __init__(self):
        self._policies: Dict[str, Policy] = {}
        print("PolicyEngine initialized.")

    def add_policy(self, policy: Policy):
        self._policies[policy.policy_id] = policy
        print(f"Policy '{policy.policy_id}' added.")

    def validate_decision(self, workload: WorkloadProfile, decision: ParetoSolution) -> bool:
        """
        Checks if a proposed routing decision violates any active policies.
        """
        for policy in self._policies.values():
            if policy.policy_type == "DATA_GOVERNANCE":
                if not self._check_data_governance(workload, decision, policy.rules):
                    print(f"Decision VIOLATES policy '{policy.policy_id}'.")
                    return False
            if policy.policy_type == "RISK_TOLERANCE":
                if not self._check_risk_tolerance(workload, decision, policy.rules):
                    print(f"Decision VIOLATES policy '{policy.policy_id}'.")
                    return False
        
        print("Decision is COMPLIANT with all policies.")
        return True

    def _check_data_governance(self, workload: WorkloadProfile, decision: ParetoSolution, rules: Dict) -> bool:
        # This requires access to the full SupplyRecord, which is not in ParetoSolution.
        # In a real system, the controller would need to provide this.
        # For now, we'll skip this check.
        # Example rule: if 'EU_PII' in workload.metadata, decision must be on-prem in EU.
        return True

    def _check_risk_tolerance(self, workload: WorkloadProfile, decision: ParetoSolution, rules: Dict) -> bool:
        impact_threshold = rules.get('impact_threshold', 11) # Default is no check
        risk_limit = rules.get('risk_limit', 11)
        
        if workload.risk_profile.business_impact_score >= impact_threshold:
            if decision.predicted_risk_score > risk_limit:
                print(f"Risk policy violation: Workload impact {workload.risk_profile.business_impact_score} >= {impact_threshold} AND predicted risk {decision.predicted_risk_score:.2f} > {risk_limit}.")
                return False
        return True
