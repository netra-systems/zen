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
from app.services.apex_optimizer_agent.tools.finish import finish
from app.services.deepagents.tools import update_state
from functools import partial

class ToolBuilder:
    @staticmethod
    def build_all(db_session: Any, llm_manager: LLMManager) -> Dict[str, Any]:
        all_tools = {
            "cost_analyzer": partial(cost_analyzer, db_session=db_session, llm_manager=llm_manager),
            "latency_analyzer": partial(latency_analyzer, db_session=db_session, llm_manager=llm_manager),
            "code_analyzer": partial(code_analyzer, db_session=db_session, llm_manager=llm_manager),
            "function_performance_analyzer": partial(function_performance_analyzer, db_session=db_session, llm_manager=llm_manager),
            "evaluation_criteria_definer": partial(evaluation_criteria_definer, db_session=db_session, llm_manager=llm_manager),
            "log_enricher_and_clusterer": partial(log_enricher_and_clusterer, db_session=db_session, llm_manager=llm_manager),
            "log_fetcher": partial(log_fetcher, db_session=db_session, llm_manager=llm_manager),
            "kv_cache_finder": partial(kv_cache_finder, db_session=db_session, llm_manager=llm_manager),
            "final_report_generator": partial(final_report_generator, db_session=db_session, llm_manager=llm_manager),
            "cost_driver_identifier": partial(cost_driver_identifier, db_session=db_session, llm_manager=llm_manager),
            "latency_bottleneck_identifier": partial(latency_bottleneck_identifier, db_session=db_session, llm_manager=llm_manager),
            "future_usage_modeler": partial(future_usage_modeler, db_session=db_session, llm_manager=llm_manager),
            "optimal_policy_proposer": partial(optimal_policy_proposer, db_session=db_session, llm_manager=llm_manager),
            "optimization_proposer": partial(optimization_proposer, db_session=db_session, llm_manager=llm_manager),
            "optimized_implementation_proposer": partial(optimized_implementation_proposer, db_session=db_session, llm_manager=llm_manager),
            "optimization_method_researcher": partial(optimization_method_researcher, db_session=db_session, llm_manager=llm_manager),
            "cost_impact_simulator": partial(cost_impact_simulator, db_session=db_session, llm_manager=llm_manager),
            "quality_impact_simulator": partial(quality_impact_simulator, db_session=db_session, llm_manager=llm_manager),
            "rate_limit_impact_simulator": partial(rate_limit_impact_simulator, db_session=db_session, llm_manager=llm_manager),
            "performance_gains_simulator": partial(performance_gains_simulator, db_session=db_session, llm_manager=llm_manager),
            "policy_simulator": partial(policy_simulator, db_session=db_session, llm_manager=llm_manager),
            "finish": finish,
            "update_state": update_state,
        }
        
        for name, tool in all_tools.items():
            if isinstance(tool, partial):
                setattr(tool, 'name', name)

        return all_tools, {}