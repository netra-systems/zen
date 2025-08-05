from typing import Dict, Any, Callable
from app.services.deep_agent_v3.tools.cost_reduction_quality_preservation import analyze_current_costs, identify_cost_drivers, propose_cost_optimizations, simulate_quality_impact
from app.services.deep_agent_v3.tools.tool_latency_optimization import analyze_current_latency, identify_latency_bottlenecks, propose_latency_optimizations, simulate_cost_impact
from app.services.deep_agent_v3.tools.cost_simulation_for_increased_usage import analyze_current_usage, model_future_usage, simulate_cost_impact_for_usage, simulate_rate_limit_impact
from app.services.deep_agent_v3.tools.advanced_optimization_for_core_function import analyze_function_performance, research_optimization_methods, propose_optimized_implementation, simulate_performance_gains
from app.services.deep_agent_v3.tools.new_model_effectiveness_analysis import define_evaluation_criteria, run_benchmarks, compare_performance, analyze_cost_implications
from app.services.deep_agent_v3.tools.kv_cache_optimization_audit import identify_kv_caches, analyze_cache_hit_rates, identify_inefficient_usage, propose_cache_optimizations
from app.services.deep_agent_v3.tools.multi_objective_optimization import define_optimization_goals, analyze_trade_offs, propose_balanced_optimizations, simulate_multi_objective_impact

ALL_STEPS: Dict[str, Callable[..., Any]] = {
    # Cost Reduction with Quality Constraint
    "analyze_current_costs": analyze_current_costs,
    "identify_cost_drivers": identify_cost_drivers,
    "propose_cost_optimizations": propose_cost_optimizations,
    "simulate_quality_impact": simulate_quality_impact,

    # Latency Reduction with Cost Constraint
    "analyze_current_latency": analyze_current_latency,
    "identify_latency_bottlenecks": identify_latency_bottlenecks,
    "propose_latency_optimizations": propose_latency_optimizations,
    "simulate_cost_impact": simulate_cost_impact,

    # Usage Increase Impact Analysis
    "analyze_current_usage": analyze_current_usage,
    "model_future_usage": model_future_usage,
    "simulate_cost_impact_for_usage": simulate_cost_impact_for_usage,
    "simulate_rate_limit_impact": simulate_rate_limit_impact,

    # Function Optimization
    "analyze_function_performance": analyze_function_performance,
    "research_optimization_methods": research_optimization_methods,
    "propose_optimized_implementation": propose_optimized_implementation,
    "simulate_performance_gains": simulate_performance_gains,

    # Model Effectiveness Analysis
    "define_evaluation_criteria": define_evaluation_criteria,
    "run_benchmarks": run_benchmarks,
    "compare_performance": compare_performance,
    "analyze_cost_implications": analyze_cost_implications,

    # KV Caching Audit
    "identify_kv_caches": identify_kv_caches,
    "analyze_cache_hit_rates": analyze_cache_hit_rates,
    "identify_inefficient_usage": identify_inefficient_usage,
    "propose_cache_optimizations": propose_cache_optimizations,

    # Multi-Objective Optimization
    "define_optimization_goals": define_optimization_goals,
    "analyze_trade_offs": analyze_trade_offs,
    "propose_balanced_optimizations": propose_balanced_optimizations,
    "simulate_multi_objective_impact": simulate_multi_objective_impact,
}
