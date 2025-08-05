from typing import Any, Dict
from app.llm.llm_manager import LLMManager
from app.services.apex_optimizer_agent.tools.cost_analyzer import cost_analyzer
from app.services.apex_optimizer_agent.tools.latency_analyzer import latency_analyzer
from app.services.apex_optimizer_agent.tools.code_analyzer import code_analyzer
from app.services.apex_optimizer_agent.tools.function_performance_analyzer import function_performance_analyzer
from app.services.apex_optimizer_agent.tools.evaluation_criteria_definer import evaluation_criteria_definer
from app.services.apex_optimizer_agent.tools.log_enricher_and_clusterer import log_enricher_and_clusterer
from app.services.apex_optimizer_agent.tools.log_fetcher import log_fetcher
from app.services.apex_optimizer_agent.tools.kv_cache_finder import kv_cache_finder
from app.services.apex_optimizer_agent.tools.final_report_generator import final_report_generator
from app.services.apex_optimizer_agent.tools.cost_driver_identifier import cost_driver_identifier
from app.services.apex_optimizer_agent.tools.latency_bottleneck_identifier import latency_bottleneck_identifier
from app.services.apex_optimizer_agent.tools.future_usage_modeler import future_usage_modeler
from app.services.apex_optimizer_agent.tools.optimal_policy_proposer import optimal_policy_proposer
from app.services.apex_optimizer_agent.tools.optimization_proposer import optimization_proposer
from app.services.apex_optimizer_agent.tools.optimized_implementation_proposer import optimized_implementation_proposer
from app.services.apex_optimizer_agent.tools.optimization_method_researcher import optimization_method_researcher
from app.services.apex_optimizer_agent.tools.cost_impact_simulator import cost_impact_simulator
from app.services.apex_optimizer_agent.tools.quality_impact_simulator import quality_impact_simulator
from app.services.apex_optimizer_agent.tools.rate_limit_impact_simulator import rate_limit_impact_simulator
from app.services.apex_optimizer_agent.tools.performance_gains_simulator import performance_gains_simulator
from app.services.apex_optimizer_agent.tools.policy_simulator import policy_simulator

class ToolBuilder:
    @staticmethod
    def build_all(db_session: any, llm_manager: LLMManager) -> Dict[str, Any]:
        all_tools = {
            "cost_analyzer": cost_analyzer,
            "latency_analyzer": latency_analyzer,
            "code_analyzer": code_analyzer,
            "function_performance_analyzer": function_performance_analyzer,
            "evaluation_criteria_definer": evaluation_criteria_definer,
            "log_enricher_and_clusterer": log_enricher_and_clusterer,
            "log_fetcher": log_fetcher,
            "kv_cache_finder": kv_cache_finder,
            "final_report_generator": final_report_generator,
            "cost_driver_identifier": cost_driver_identifier,
            "latency_bottleneck_identifier": latency_bottleneck_identifier,
            "future_usage_modeler": future_usage_modeler,
            "optimal_policy_proposer": optimal_policy_proposer,
            "optimization_proposer": optimization_proposer,
            "optimized_implementation_proposer": optimized_implementation_proposer,
            "optimization_method_researcher": optimization_method_researcher,
            "cost_impact_simulator": cost_impact_simulator,
            "quality_impact_simulator": quality_impact_simulator,
            "rate_limit_impact_simulator": rate_limit_impact_simulator,
            "performance_gains_simulator": performance_gains_simulator,
            "policy_simulator": policy_simulator,
        }
        
        return all_tools, {}
