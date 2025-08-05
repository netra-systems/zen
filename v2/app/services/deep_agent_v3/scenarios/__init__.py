
from .cost_reduction_quality_constraint import COST_REDUCTION_QUALITY_CONSTRAINT
from .function_optimization import FUNCTION_OPTIMIZATION
from .kv_caching_audit import KV_CACHING_AUDIT
from .latency_reduction_cost_constraint import LATENCY_REDUCTION_COST_CONSTRAINT
from .model_effectiveness_analysis import MODEL_EFFECTIVENESS_ANALYSIS
from .multi_objective_optimization import MULTI_OBJECTIVE_OPTIMIZATION
from .usage_increase_impact_analysis import USAGE_INCREASE_IMPACT_ANALYSIS

SCENARIOS = {
    "cost_reduction_quality_constraint": COST_REDUCTION_QUALITY_CONSTRAINT,
    "function_optimization": FUNCTION_OPTIMIZATION,
    "kv_caching_audit": KV_CACHING_AUDIT,
    "latency_reduction_cost_constraint": LATENCY_REDUCTION_COST_CONSTRAINT,
    "model_effectiveness_analysis": MODEL_EFFECTIVENESS_ANALYSIS,
    "multi_objective_optimization": MULTI_OBJECTIVE_OPTIMIZATION,
    "usage_increase_impact_analysis": USAGE_INCREASE_IMPACT_ANALYSIS,
}
