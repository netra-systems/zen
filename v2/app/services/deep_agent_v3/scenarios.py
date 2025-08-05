from typing import Dict, Any, List

SCENARIOS: Dict[str, Dict[str, Any]] = {
    "cost_reduction_quality_constraint": {
        "name": "Cost Reduction with Quality Constraint",
        "description": "Reduces costs while maintaining a certain level of quality.",
        "steps": [
            "analyze_current_costs",
            "identify_cost_drivers",
            "propose_optimizations",
            "simulate_impact_on_quality",
            "generate_report"
        ]
    },
    "latency_reduction_cost_constraint": {
        "name": "Latency Reduction with Cost Constraint",
        "description": "Reduces latency without increasing costs.",
        "steps": [
            "analyze_current_latency",
            "identify_latency_bottlenecks",
            "propose_optimizations",
            "simulate_impact_on_costs",
            "generate_report"
        ]
    },
    "usage_increase_impact_analysis": {
        "name": "Usage Increase Impact Analysis",
        "description": "Analyzes the impact of a usage increase on costs and rate limits.",
        "steps": [
            "analyze_current_usage_patterns",
            "model_future_usage",
            "simulate_impact_on_costs",
            "simulate_impact_on_rate_limits",
            "generate_report"
        ]
    },
    "function_optimization": {
        "name": "Function Optimization",
        "description": "Optimizes a specific function using advanced methods.",
        "steps": [
            "analyze_function_performance",
            "research_optimization_methods",
            "propose_optimized_implementation",
            "simulate_performance_gains",
            "generate_report"
        ]
    },
    "model_effectiveness_analysis": {
        "name": "Model Effectiveness Analysis",
        "description": "Analyzes the effectiveness of new models in the current setup.",
        "steps": [
            "define_evaluation_criteria",
            "run_benchmarks_with_new_models",
            "compare_performance_with_current_models",
            "analyze_cost_implications",
            "generate_report"
        ]
    },
    "kv_caching_audit": {
        "name": "KV Caching Audit",
        "description": "Audits all uses of KV caching in the system to find optimization opportunities.",
        "steps": [
            "identify_all_kv_caches",
            "analyze_cache_hit_rates",
            "identify_inefficient_cache_usage",
            "propose_optimizations",
            "generate_report"
        ]
    },
    "multi_objective_optimization": {
        "name": "Multi-Objective Optimization",
        "description": "Optimizes for multiple objectives simultaneously (e.g., cost, latency, usage).",
        "steps": [
            "define_optimization_goals",
            "analyze_trade_offs",
            "propose_balanced_optimizations",
            "simulate_impact_on_all_objectives",
            "generate_report"
        ]
    }
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
