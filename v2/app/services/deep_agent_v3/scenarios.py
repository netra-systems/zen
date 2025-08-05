from typing import Dict, Any

from .scenarios.cost_reduction_quality_constraint import COST_REDUCTION_QUALITY_CONSTRAINT
from .scenarios.latency_reduction_cost_constraint import LATENCY_REDUCTION_COST_CONSTRAINT
from .scenarios.usage_increase_impact_analysis import USAGE_INCREASE_IMPACT_ANALYSIS
from .scenarios.function_optimization import FUNCTION_OPTIMIZATION
from .scenarios.model_effectiveness_analysis import MODEL_EFFECTIVENESS_ANALYSIS
from .scenarios.kv_caching_audit import KV_CACHING_AUDIT
from .scenarios.multi_objective_optimization import MULTI_OBJECTIVE_OPTIMIZATION

SCENARIOS: Dict[str, Dict[str, Any]] = {
    "cost_reduction_quality_constraint": COST_REDUCTION_QUALITY_CONSTRAINT,
    "latency_reduction_cost_constraint": LATENCY_REDUCTION_COST_CONSTRAINT,
    "usage_increase_impact_analysis": USAGE_INCREASE_IMPACT_ANALYSIS,
    "function_optimization": FUNCTION_OPTIMIZATION,
    "model_effectiveness_analysis": MODEL_EFFECTIVENESS_ANALYSIS,
    "kv_caching_audit": KV_CACHING_AUDIT,
    "multi_objective_optimization": MULTI_OBJECTIVE_OPTIMIZATION,
}

def get_scenario(prompt: str) -> Dict[str, Any]:
    """Selects the best scenario based on the user's prompt."""
    # This is a simple implementation that uses keyword matching. A more advanced
    # implementation would use a language model to understand the user's intent.
    if "cost" in prompt and "quality" in prompt:
        return SCENARIOS["cost_reduction_quality_constraint"]
    elif "latency" in prompt and "cost" in prompt:
        return SCENARIOS["latency_reduction_cost_constraint"]
    elif "usage" in prompt and ("cost" in prompt or "rate limits" in prompt):
        return SCENARIOS["usage_increase_impact_analysis"]
    elif "optimize" in prompt and "function" in prompt:
        return SCENARIOS["function_optimization"]
    elif "model" in prompt and "effective" in prompt:
        return SCENARIOS["model_effectiveness_analysis"]
    elif "audit" in prompt and "caching" in prompt:
        return SCENARIOS["kv_caching_audit"]
    elif "cost" in prompt and "latency" in prompt and "usage" in prompt:
        return SCENARIOS["multi_objective_optimization"]
    else:
        # Default to a generic scenario if no specific match is found
        return {
            "name": "Generic Optimization",
            "description": "A generic optimization scenario.",
            "steps": [
                "analyze_request",
                "propose_solution",
                "generate_report"
            ]
        }