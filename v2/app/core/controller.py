# netra_apex/core/controller.py
#
# Copyright (C) 2025, netra apex Inc.
#
# This module implements the Multi-Objective Controller, the cognitive core of
# the netra apex. It takes a WorkloadProfile and the current state of the
# SupplyCatalog to perform an intelligent matching process. Its goal is not to
# find a single "best" option but to identify the Pareto-optimal set of supply
# choices, making the trade-offs between cost, latency, and risk explicit.
# Reference: Section 4: The Multi-Objective Controller.

import math
from typing import List, Dict, Any

from ..models.schemas import WorkloadProfile, SupplyRecord, ParetoSolution
from .supply_catalog import SupplyCatalog
from ..utils.predictors import TokenizationInefficiencyPredictor

class ObjectivePredictor:
    """
    A sub-component that houses the predictive models for each objective
    (cost, latency, risk). In a real system, these would be sophisticated ML
    models trained on historical data. Here, they are implemented as rule-based
    functions for demonstration.
    """
    def __init__(self):
        self.token_inefficiency_predictor = TokenizationInefficiencyPredictor()
        print("ObjectivePredictor initialized.")

    def predict_cost(self, workload: WorkloadProfile, supply: SupplyRecord) -> float:
        """Predicts the total cost for the workload on the given supply option."""
        # Estimate output tokens as a function of input tokens
        estimated_output_tokens = workload.linguistic_features.prompt_length_tokens * 1.5
        
        # Account for tokenization inefficiency
        inefficiency_ratio = self.token_inefficiency_predictor.predict_ratio(workload, supply)
        actual_input_tokens = workload.linguistic_features.prompt_length_tokens * inefficiency_ratio
        
        cost_model = supply.cost_model
        if cost_model.type == "API":
            input_cost = (actual_input_tokens / 1_000_000) * cost_model.input_cost_per_million_tokens
            output_cost = (estimated_output_tokens / 1_000_000) * cost_model.output_cost_per_million_tokens
            return input_cost + output_cost
        
        if cost_model.type == "TCO":
            # Simplified TCO: cost is a function of processing time
            # Assume 1 task takes a fraction of an hour based on its complexity
            processing_time_hours = (workload.linguistic_features.prompt_length_tokens / 50000.0) # tasks per hour
            return processing_time_hours * cost_model.amortized_cost_per_hour

        return float('inf')

    def predict_latency(self, workload: WorkloadProfile, supply: SupplyRecord) -> Dict[str, float]:
        """Predicts the p95 TTFT and TPOT for the workload on the supply option."""
        if not supply.performance: # If no live data, can't predict
            return {"ttft": float('inf'), "tpot": float('inf')}
        
        # Use batch_1 for simplicity
        base_ttft = supply.performance.ttft_ms.get("batch_1").p99
        base_tpot = supply.performance.tpot_ms.get("batch_1").p99

        # Adjust latency based on prompt length (prefill phase)
        # Simple linear scaling for demonstration
        ttft_scaling_factor = max(1.0, workload.linguistic_features.prompt_length_tokens / 512.0)
        
        return {
            "ttft": base_ttft * ttft_scaling_factor,
            "tpot": base_tpot
        }

    def predict_risk_score(self, workload: WorkloadProfile, supply: SupplyRecord) -> float:
        """
        Predicts a consolidated risk score. Lower is better.
        This function combines the workload's intrinsic risk with the supply's
        observed safety profile.
        """
        if not supply.safety_and_quality: # Un-profiled models are max risk
            return 10.0
            
        # Base risk from the workload itself
        base_risk = workload.risk_profile.business_impact_score
        
        # Modulate risk based on the model's known failure rates for the
        # specific failure modes we care about for this workload.
        risk_multiplier = 1.0
        relevant_risks = 0
        for tag in workload.risk_profile.failure_mode_tags:
            if tag == 'risk_of_hallucination':
                risk_multiplier += supply.safety_and_quality.hallucination_rate * 5
                relevant_risks += 1
            if tag == 'risk_of_pii_leakage':
                risk_multiplier += supply.safety_and_quality.pii_leakage_rate * 10 # Higher penalty
                relevant_risks += 1
            if tag == 'risk_of_bias':
                 risk_multiplier += supply.safety_and_quality.toxicity_score * 3
                 relevant_risks += 1
        
        # Average the multiplier effect if multiple risks apply
        if relevant_risks > 0:
            final_risk = base_risk * (risk_multiplier / (relevant_risks or 1))
        else: # If no specific failure modes are tagged, use a general quality score
            final_risk = base_risk * (1 / (supply.safety_and_quality.adversarial_robustness_score + 0.01))

        return min(10.0, final_risk) # Cap risk at 10

class MultiObjectiveController:
    """
    The main controller class that orchestrates the optimization process.
    """
    def __init__(self, supply_catalog: SupplyCatalog):
        """
        Initializes the controller.
        
        Args:
            supply_catalog: A singleton instance of the SupplyCatalog.
        """
        self.supply_catalog = supply_catalog
        self.predictor = ObjectivePredictor()
        print("MultiObjectiveController initialized.")

    def find_pareto_optimal_solutions(self, workload: WorkloadProfile) -> List[ParetoSolution]:
        """
        The core method that performs the multi-objective optimization. It
        evaluates all viable supply options and identifies the Pareto front.
        Reference: Section 4, Component 1 & 2.

        Args:
            workload: The WorkloadProfile object representing the demand.

        Returns:
            A list of ParetoSolution objects representing the optimal trade-offs.
        """
        candidate_supplies = self.supply_catalog.list_certified_records()
        
        # Filter out supplies that clearly cannot handle the workload
        viable_supplies = [
            s for s in candidate_supplies 
            if s.technical_specs.max_context_window >= workload.linguistic_features.prompt_length_tokens
            and s.performance is not None
            and s.safety_and_quality is not None
        ]
        
        if not viable_supplies:
            print("Warning: No viable supply options found for this workload.")
            return []

        # 1. Evaluate all viable options against the objectives
        evaluated_solutions = []
        for supply in viable_supplies:
            cost = self.predictor.predict_cost(workload, supply)
            latency = self.predictor.predict_latency(workload, supply)
            risk = self.predictor.predict_risk_score(workload, supply)
            
            evaluated_solutions.append({
                "supply_id": supply.supply_id,
                "cost": cost,
                "ttft": latency["ttft"],
                "tpot": latency["tpot"],
                "risk": risk
            })
            
        # 2. Identify the Pareto front
        # An option is on the Pareto front if no other option is better or equal
        # on all objectives and strictly better on at least one objective.
        pareto_front = []
        for sol1 in evaluated_solutions:
            is_dominated = False
            for sol2 in evaluated_solutions:
                if sol1 == sol2:
                    continue
                # Check if sol2 dominates sol1
                if (sol2['cost'] <= sol1['cost'] and 
                    sol2['ttft'] <= sol1['ttft'] and
                    sol2['tpot'] <= sol1['tpot'] and 
                    sol2['risk'] <= sol1['risk'] and
                    # Check for strict dominance on at least one objective
                    (sol2['cost'] < sol1['cost'] or 
                     sol2['ttft'] < sol1['ttft'] or
                     sol2['tpot'] < sol1['tpot'] or
                     sol2['risk'] < sol1['risk'])):
                    is_dominated = True
                    break
            if not is_dominated:
                pareto_front.append(sol1)

        # 3. Format the output
        return [
            ParetoSolution(
                supply_id=sol['supply_id'],
                predicted_cost=sol['cost'],
                predicted_ttft_ms_p95=sol['ttft'],
                predicted_tpot_ms_p95=sol['tpot'],
                predicted_risk_score=sol['risk'],
                trade_off_profile=self._characterize_solution(sol)
            ) for sol in pareto_front
        ]

    def _characterize_solution(self, solution: Dict) -> str:
        """A helper to create a human-readable profile for a solution."""
        # Simple characterization based on which metric is lowest relative to others
        # This is a simplification; a real system might use clustering or relative ranking.
        if solution['cost'] < 0.01:
            return "Cost-Optimized"
        if solution['ttft'] < 400:
            return "Latency-Optimized"
        if solution['risk'] < 4.0:
            return "Quality/Risk-Optimized"
        return "Balanced"
        
    def select_decision(self, pareto_solutions: List[ParetoSolution], utility_weights: Dict[str, float]) -> Optional[ParetoSolution]:
        """
        Selects a single best option from the Pareto front based on a utility function.
        Reference: Section 4, Component 3.

        Args:
            pareto_solutions: The list of solutions on the Pareto front.
            utility_weights: A dictionary of weights for {'cost', 'latency', 'risk'}.

        Returns:
            The single ParetoSolution with the highest utility score.
        """
        if not pareto_solutions:
            return None

        best_solution = None
        max_utility = -float('inf')

        for sol in pareto_solutions:
            # Normalize objectives to be "higher is better" for utility calculation
            # We invert cost and latency. For risk, we use (10 - risk).
            # A small epsilon is added to avoid division by zero.
            utility = (
                utility_weights.get('cost', 1.0) * (1 / (sol.predicted_cost + 1e-9)) +
                utility_weights.get('latency', 1.0) * (1 / (sol.predicted_ttft_ms_p95 + sol.predicted_tpot_ms_p95 + 1e-9)) +
                utility_weights.get('risk', 1.0) * (10 - sol.predicted_risk_score)
            )
            
            if utility > max_utility:
                max_utility = utility
                best_solution = sol
        
        return best_solution
