# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-10T18:48:31.171360+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Add baseline agent tracking to apex optimizer tools
# Git: v6 | be70ff77 | clean
# Change: Feature | Scope: Module | Risk: High
# Session: f4b153af-998e-4648-bfed-e03ac78b4b8f | Seq: 1
# Review: Pending | Score: 85
# ================================
import inspect
from typing import Any, Dict, Callable, Awaitable, TypeVar, Union

T = TypeVar('T')
from langchain_core.tools import StructuredTool
from pydantic import create_model, BaseModel
import asyncio
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

from app.services.context import ToolContext
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

def create_async_tool_wrapper(
    tool_func: Callable[..., Awaitable[T]],
    context: ToolContext,
    has_args: bool
) -> Callable[..., Awaitable[T]]:
    async def wrapper(**kwargs: Any) -> T:
        # LangChain automatically adds this, so we filter it out
        kwargs.pop('callbacks', None)
        tool_name = tool_func.__name__
        
        logger.debug(f"Executing tool: {tool_name} with args: {has_args}")
        
        try:
            if has_args:
                result = await tool_func(context, **kwargs)
            else:
                result = await tool_func(context)
            
            logger.debug(f"Tool {tool_name} completed successfully")
            return result
        
        except Exception as e:
            logger.error(f"Tool {tool_name} execution failed: {e}", exc_info=True)
            raise
    
    return wrapper

class ToolBuilder:
    @staticmethod
    def build_all(context: ToolContext) -> Dict[str, StructuredTool]:
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
            "finish": finish,
        }
        
        bound_tools = {}
        for name, tool_func in all_tools.items():
            sig = inspect.signature(tool_func)
            params = [p for p in sig.parameters.values() if p.name not in ['context', 'callbacks']]
            has_args = len(params) > 0
            
            fields = {}
            for p in params:
                if p.default is inspect.Parameter.empty:
                    fields[p.name] = (p.annotation, ...)
                else:
                    fields[p.name] = (p.annotation, p.default)
            
            if has_args:
                args_schema = create_model(f"{name}_args", **fields, __base__=BaseModel)
            else:
                args_schema = create_model(f"{name}_args", __base__=BaseModel)

            tool = StructuredTool(
                name=name,
                description=tool_func.__doc__,
                args_schema=args_schema,
                coroutine=create_async_tool_wrapper(tool_func, context, has_args),
                func=None
            )
            bound_tools[name] = tool
            
        return bound_tools, {}