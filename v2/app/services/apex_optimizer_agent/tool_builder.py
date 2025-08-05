from typing import Any, Dict
from app.llm.llm_manager import LLMManager
from app.services.apex_optimizer_agent.tools.cost_analyzer import CostAnalyzer
from app.services.apex_optimizer_agent.tools.latency_analyzer import LatencyAnalyzer
from app.services.apex_optimizer_agent.tools.code_analyzer import CodeAnalyzer
from app.services.apex_optimizer_agent.tools.function_performance_analyzer import FunctionPerformanceAnalyzer
from app.services.apex_optimizer_agent.tools.evaluation_criteria_definer import EvaluationCriteriaDefiner
from app.services.apex_optimizer_agent.tools.tool_dispatcher import ToolDispatcher
from app.services.apex_optimizer_agent.tools.log_enricher_and_clusterer import LogEnricherAndClusterer
from app.services.apex_optimizer_agent.tools.log_fetcher import LogFetcher
from app.services.apex_optimizer_agent.tools.kv_cache_finder import KVCacheFinder
from app.services.apex_optimizer_agent.tools.final_report_generator import FinalReportGenerator
from app.services.apex_optimizer_agent.tools.cost_driver_identifier import CostDriverIdentifier
from app.services.apex_optimizer_agent.tools.latency_bottleneck_identifier import LatencyBottleneckIdentifier
from app.services.apex_optimizer_agent.tools.future_usage_modeler import FutureUsageModeler
from app.services.apex_optimizer_agent.tools.optimal_policy_proposer import OptimalPolicyProposer
from app.services.apex_optimizer_agent.tools.optimization_proposer import OptimizationProposer
from app.services.apex_optimizer_agent.tools.optimized_implementation_proposer import OptimizedImplementationProposer
from app.services.apex_optimizer_agent.tools.optimization_method_researcher import OptimizationMethodResearcher
from app.services.apex_optimizer_agent.tools.cost_impact_simulator import CostImpactSimulator
from app.services.apex_optimizer_agent.tools.quality_impact_simulator import QualityImpactSimulator
from app.services.apex_optimizer_agent.tools.rate_limit_impact_simulator import RateLimitImpactSimulator
from app.services.apex_optimizer_agent.tools.performance_gains_simulator import PerformanceGainsSimulator
from app.services.apex_optimizer_agent.tools.policy_simulator import PolicySimulator

class ToolBuilder:
    @staticmethod
    def build_all(db_session: any, llm_manager: LLMManager) -> Dict[str, Any]:
        # These are the individual tools that can be used by the agent.
        # They are organized into SuperTools, which are sets of tools for specific tasks.
        
        cost_analysis_tools = {
            "cost_analyzer": CostAnalyzer(llm_manager),
            "cost_driver_identifier": CostDriverIdentifier(llm_manager),
            "cost_impact_simulator": CostImpactSimulator(llm_manager),
        }
        
        performance_analysis_tools = {
            "latency_analyzer": LatencyAnalyzer(llm_manager),
            "latency_bottleneck_identifier": LatencyBottleneckIdentifier(llm_manager),
            "performance_gains_simulator": PerformanceGainsSimulator(llm_manager),
        }
        
        code_optimization_tools = {
            "code_analyzer": CodeAnalyzer(llm_manager),
            "function_performance_analyzer": FunctionPerformanceAnalyzer(llm_manager),
            "optimized_implementation_proposer": OptimizedImplementationProposer(llm_manager),
            "optimization_method_researcher": OptimizationMethodResearcher(llm_manager),
        }
        
        log_analysis_tools = {
            "log_fetcher": LogFetcher(db_session),
            "log_enricher_and_clusterer": LogEnricherAndClusterer(llm_manager),
            "optimal_policy_proposer": OptimalPolicyProposer(llm_manager),
        }
        
        simulation_tools = {
            "future_usage_modeler": FutureUsageModeler(),
            "rate_limit_impact_simulator": RateLimitImpactSimulator(llm_manager),
            "quality_impact_simulator": QualityImpactSimulator(llm_manager),
            "policy_simulator": PolicySimulator(llm_manager),
        }
        
        # The SuperTools are sets of tools that can be selected by the agent based on the triage results.
        # This allows the agent to have a focused set of tools for the task at hand.
        super_tools = {
            "cost_optimization": cost_analysis_tools,
            "performance_tuning": performance_analysis_tools,
            "code_optimization": code_optimization_tools,
            "log_analysis": log_analysis_tools,
            "simulation": simulation_tools,
        }
        
        # The full set of tools is also available for general use.
        all_tools = {
            **cost_analysis_tools,
            **performance_analysis_tools,
            **code_optimization_tools,
            **log_analysis_tools,
            **simulation_tools,
            "kv_cache_finder": KVCacheFinder(llm_manager),
            "final_report_generator": FinalReportGenerator(),
            "tool_dispatcher": ToolDispatcher(llm_manager, None), # Settings will be passed in the agent
            "evaluation_criteria_definer": EvaluationCriteriaDefiner(),
            "optimization_proposer": OptimizationProposer(llm_manager),
        }
        
        return all_tools, super_tools