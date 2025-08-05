
from typing import Dict, Any

# TBD move to tests
COST_REDUCTION_QUALITY_CONSTRAINT: Dict[str, Any] = {
    "name": "Cost Reduction with Quality Constraint",
    "description": "Reduces costs while maintaining a certain level of quality.",
    "steps": [
        "analyze_current_costs",
        "identify_cost_drivers",
        "propose_optimizations",
        "simulate_impact_on_quality",
        "generate_report"
    ]
}

LATENCY_REDUCTION_COST_CONSTRAINT: Dict[str, Any] = {
    "name": "Latency Reduction with Cost Constraint",
    "description": "Reduces latency without increasing costs.",
    "steps": [
        "analyze_current_latency",
        "identify_latency_bottlenecks",
        "propose_optimizations",
        "simulate_impact_on_costs",
        "generate_report"
    ]
}

USAGE_INCREASE_IMPACT_ANALYSIS: Dict[str, Any] = {
    "name": "Usage Increase Impact Analysis",
    "description": "Analyzes the impact of a usage increase on costs and rate limits.",
    "steps": [
        "analyze_current_usage_patterns",
        "model_future_usage",
        "simulate_impact_on_costs",
        "simulate_impact_on_rate_limits",
        "generate_report"
    ]
}

FUNCTION_OPTIMIZATION: Dict[str, Any] = {
    "name": "Function Optimization",
    "description": "Optimizes a specific function using advanced methods.",
    "steps": [
        "analyze_function_performance",
        "research_optimization_methods",
        "propose_optimized_implementation",
        "simulate_performance_gains",
        "generate_report"
    ]
}

MODEL_EFFECTIVENESS_ANALYSIS: Dict[str, Any] = {
    "name": "Model Effectiveness Analysis",
    "description": "Analyzes the effectiveness of new models in the current setup.",
    "steps": [
        "define_evaluation_criteria",
        "run_benchmarks_with_new_models",
        "compare_performance_with_current_models",
        "analyze_cost_implications",
        "generate_report"
    ]
}

KV_CACHING_AUDIT: Dict[str, Any] = {
    "name": "KV Caching Audit",
    "description": "Audits all uses of KV caching in the system to find optimization opportunities.",
    "steps": [
        "identify_all_kv_caches",
        "analyze_cache_hit_rates",
        "identify_inefficient_cache_usage",
        "propose_optimizations",
        "generate_report"
    ]
}

MULTI_OBJECTIVE_OPTIMIZATION: Dict[str, Any] = {
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

SCENARIOS: Dict[str, Dict[str, Any]] = {
    "cost_reduction_quality_constraint": COST_REDUCTION_QUALITY_CONSTRAINT,
    "latency_reduction_cost_constraint": LATENCY_REDUCTION_COST_CONSTRAINT,
    "usage_increase_impact_analysis": USAGE_INCREASE_IMPACT_ANALYSIS,
    "function_optimization": FUNCTION_OPTIMIZATION,
    "model_effectiveness_analysis": MODEL_EFFECTIVENESS_ANALYSIS,
    "kv_caching_audit": KV_CACHING_AUDIT,
    "multi_objective_optimization": MULTI_OBJECTIVE_OPTIMIZATION,
}
