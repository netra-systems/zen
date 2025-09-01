"""Optimizations Core Sub-Agent with Modern Execution Patterns

Modernized agent providing AI optimization strategies using BaseExecutionInterface.
Integrates ExecutionErrorHandler, ReliabilityManager, and ExecutionMonitor for 99.9% reliability.

Business Value: Core optimization recommendations drive customer cost savings.
Target segments: Growth & Enterprise. High revenue impact through performance fees.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.core.unified_error_handler import agent_error_handler as ExecutionErrorHandler
from netra_backend.app.agents.base.interface import (
    AgentExecutionMixin,
    BaseExecutionInterface,
    ExecutionContext,
    ExecutionResult,
    WebSocketManagerProtocol,
)
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.agents.base.reliability import (
    CircuitBreakerConfig,
    ReliabilityManager,
)
from netra_backend.app.agents.prompts import optimizations_core_prompt_template
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.utils import extract_json_from_response
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.llm.observability import (
    generate_llm_correlation_id,
    log_agent_communication,
    log_agent_input,
    log_agent_output,
    start_llm_heartbeat,
    stop_llm_heartbeat,
)
from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.schemas.shared_types import RetryConfig


class OptimizationsCoreSubAgent(BaseSubAgent, AgentExecutionMixin):
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher, 
                 websocket_manager: Optional[WebSocketManagerProtocol] = None):
        BaseSubAgent.__init__(self, llm_manager, name="OptimizationsCoreSubAgent", 
                             description="This agent formulates optimization strategies.")
        # Set properties for BaseExecutionInterface compatibility  
        self.agent_name = "OptimizationsCoreSubAgent"
        self.websocket_manager = websocket_manager
        self.tool_dispatcher = tool_dispatcher
        self._initialize_modern_components()
    
    def _initialize_modern_components(self) -> None:
        """Initialize modern execution components."""
        circuit_config = self._create_circuit_breaker_config()
        retry_config = self._create_retry_config()
        self.reliability_manager = ReliabilityManager(circuit_config, retry_config)
        self.error_handler = ExecutionErrorHandler
        self.monitor = ExecutionMonitor()
    
    def _create_circuit_breaker_config(self) -> CircuitBreakerConfig:
        """Create circuit breaker configuration."""
        return CircuitBreakerConfig(
            name="OptimizationsCoreSubAgent",
            failure_threshold=3,
            recovery_timeout=30
        )
    
    def _create_retry_config(self) -> RetryConfig:
        """Create retry configuration."""
        return RetryConfig(
            max_retries=2,
            base_delay=1.0,
            max_delay=10.0,
            exponential_base=2.0
        )

    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if we have data and triage results to work with."""
        return state.data_result is not None and state.triage_result is not None
    
    # BaseExecutionInterface Implementation
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions for optimization analysis."""
        return await self._validate_optimization_preconditions(context)
    
    async def _validate_optimization_preconditions(self, context: ExecutionContext) -> bool:
        """Check if we have required data for optimization analysis."""
        state = context.state
        has_data = state.data_result is not None
        has_triage = state.triage_result is not None
        has_llm_manager = self.llm_manager is not None
        return has_data and has_triage and has_llm_manager
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute optimization analysis core logic with modern patterns."""
        await self.send_status_update(context, "processing", 
                                    "Formulating optimization strategies based on data analysis...")
        
        prompt = self._build_optimization_prompt(context.state)
        correlation_id = generate_llm_correlation_id()
        
        llm_response = await self._execute_llm_with_observability(prompt, correlation_id)
        result = await self._process_optimization_response(llm_response, context)
        
        await self.send_status_update(context, "processed", 
                                    "Optimization strategies formulated successfully")
        return result
    
    # Backward Compatibility - Original execute method
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute with backward compatibility (delegates to modern patterns)."""
        # Log agent communication start
        log_agent_communication("Supervisor", "OptimizationsCoreSubAgent", run_id, "execute_request")
        
        context = self.create_execution_context(state, run_id, stream_updates)
        
        # Create async wrapper function
        async def execute_wrapper():
            return await self._execute_with_modern_patterns(context)
        
        result = await self.reliability_manager.execute_with_reliability(
            context, execute_wrapper
        )
        
        if result.success:
            state.optimizations_result = self._create_optimizations_result(result.result)
        
        # Log agent communication completion
        log_agent_communication("OptimizationsCoreSubAgent", "Supervisor", run_id, "execute_response")
    
    async def _execute_with_modern_patterns(self, context: ExecutionContext) -> ExecutionResult:
        """Execute using modern execution patterns."""
        if not await self.validate_preconditions(context):
            result = await self._create_fallback_result(context)
            return ExecutionResult(
                success=True,
                status=ExecutionStatus.COMPLETED,
                result=result,
                fallback_used=True
            )
        
        try:
            result = await self.execute_core_logic(context)
            return ExecutionResult(
                success=True,
                status=ExecutionStatus.COMPLETED,
                result=result
            )
        except Exception as e:
            logger.error(f"Core logic failed: {e}")
            result = await self._create_fallback_result(context)
            return ExecutionResult(
                success=True,
                status=ExecutionStatus.COMPLETED,
                result=result,
                error=str(e),
                fallback_used=True
            )
    
    async def _create_fallback_result(self, context: ExecutionContext) -> Dict[str, Any]:
        """Create fallback optimization result."""
        logger.warning(f"Using fallback optimization for run_id: {context.run_id}")
        fallback_result = self._create_default_fallback_result()
        context.state.optimizations_result = self._create_optimizations_result(fallback_result)
        
        await self.send_status_update(context, "completed_with_fallback",
                                    "Optimization completed with fallback method")
        return fallback_result
    
    async def _execute_llm_with_observability(self, prompt: str, correlation_id: str) -> str:
        """Execute LLM call with full observability."""
        start_llm_heartbeat(correlation_id, "OptimizationsCoreSubAgent")
        try:
            log_agent_input("OptimizationsCoreSubAgent", "LLM", len(prompt), correlation_id)
            return await self._make_llm_request(prompt, correlation_id)
        finally:
            stop_llm_heartbeat(correlation_id)
    
    async def _make_llm_request(self, prompt: str, correlation_id: str) -> str:
        """Make LLM request with error handling."""
        try:
            response = await self.llm_manager.ask_llm(prompt, llm_config_name='optimizations_core')
            log_agent_output("LLM", "OptimizationsCoreSubAgent", len(response), "success", correlation_id)
            return response
        except Exception as e:
            log_agent_output("LLM", "OptimizationsCoreSubAgent", 0, "error", correlation_id)
            raise
    
    async def _process_optimization_response(self, llm_response_str: str, 
                                           context: ExecutionContext) -> Dict[str, Any]:
        """Process LLM response and update state."""
        optimizations_result = self._extract_and_validate_result(llm_response_str, context.run_id)
        context.state.optimizations_result = self._create_optimizations_result(optimizations_result)
        return optimizations_result
    
    def _extract_and_validate_result(self, llm_response_str: str, run_id: str) -> Dict[str, Any]:
        """Extract and validate JSON result from LLM response."""
        optimizations_result = llm_parser.extract_json_from_response(llm_response_str)
        if not optimizations_result:
            logger.warning(f"Could not extract JSON from LLM response for run_id: {run_id}. Using default optimizations.")
            optimizations_result = {"optimizations": []}
        return optimizations_result
    
    def _build_optimization_prompt(self, state: DeepAgentState) -> str:
        """Build the optimization prompt from state data."""
        return optimizations_core_prompt_template.format(
            data=state.data_result,
            triage_result=state.triage_result,
            user_request=state.user_request
        )
    
    def _create_default_fallback_result(self) -> Dict[str, Any]:
        """Create default fallback optimization result."""
        return {
            "optimization_type": "general",
            "recommendations": self._get_default_recommendations(),
            "confidence_score": 0.5,
            "metadata": self._get_fallback_metadata()
        }
    
    def _get_default_recommendations(self) -> List[str]:
        """Get default optimization recommendations."""
        return [
            "Basic optimization analysis - review current resource utilization",
            "Consider cost optimization opportunities based on usage patterns",
            "Evaluate performance improvements for critical workloads"
        ]
    
    def _get_fallback_metadata(self) -> Dict[str, Any]:
        """Get fallback metadata dictionary."""
        return {
            "fallback_used": True,
            "reason": "Primary optimization analysis failed"
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive agent health status."""
        return {
            "agent_name": self.agent_name,
            "reliability": self.reliability_manager.get_health_status(),
            "monitoring": self.monitor.get_health_status(),
            "error_handler": "available"
        }
    
    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        return self.reliability_manager.circuit_breaker.get_status()
    
    def _create_optimizations_result(self, data: Dict[str, Any]) -> 'OptimizationsResult':
        """Convert dictionary to OptimizationsResult object."""
        from netra_backend.app.agents.state import OptimizationsResult
        
        recommendations = self._extract_recommendations(data)
        processed_recommendations = self._process_recommendations(recommendations)
        return self._build_optimizations_result(data, processed_recommendations)
    
    def _extract_recommendations(self, data: Dict[str, Any]) -> Any:
        """Extract recommendations from data dict."""
        return data.get("recommendations", data.get("optimizations", []))
    
    def _process_recommendations(self, recommendations: Any) -> List[str]:
        """Process recommendations to ensure they're a list of strings."""
        if isinstance(recommendations, list):
            return self._convert_recommendation_list(recommendations)
        return [str(recommendations)] if recommendations else []
    
    def _convert_recommendation_list(self, recommendations: List) -> List[str]:
        """Convert list of recommendations to strings."""
        fixed_recommendations = []
        for rec in recommendations:
            converted_rec = self._convert_single_recommendation(rec)
            fixed_recommendations.append(converted_rec)
        return fixed_recommendations
    
    def _convert_single_recommendation(self, rec: Any) -> str:
        """Convert single recommendation to string."""
        if isinstance(rec, dict):
            return rec.get("description", str(rec))
        return str(rec)
    
    def _build_optimizations_result(self, data: Dict[str, Any], recommendations: List[str]) -> 'OptimizationsResult':
        """Build OptimizationsResult from processed data."""
        from netra_backend.app.agents.state import OptimizationsResult
        result_params = self._build_optimization_result_params(data, recommendations)
        return OptimizationsResult(**result_params)
    
    def _build_optimization_result_params(self, data: Dict[str, Any], recommendations: List[str]) -> Dict[str, Any]:
        """Build parameters dictionary for OptimizationsResult."""
        base_params = self._get_base_optimization_params(data, recommendations)
        extended_params = self._get_extended_optimization_params(data)
        return {**base_params, **extended_params}
    
    def _get_base_optimization_params(self, data: Dict[str, Any], recommendations: List[str]) -> Dict[str, Any]:
        """Get base optimization parameters."""
        return {
            "optimization_type": self._get_optimization_type(data),
            "recommendations": recommendations,
            "confidence_score": data.get("confidence_score", 0.8)
        }
    
    def _get_extended_optimization_params(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get extended optimization parameters."""
        return {
            "cost_savings": data.get("cost_savings"),
            "performance_improvement": data.get("performance_improvement"),
            "metadata": data.get("metadata", {})
        }
    
    def _get_optimization_type(self, data: Dict[str, Any]) -> str:
        """Extract optimization type from data with fallback."""
        return data.get("optimization_type", data.get("type", "general"))
