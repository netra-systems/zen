"""Optimizations Core Sub-Agent using Golden Pattern

Clean optimization agent following BaseAgent golden pattern.
Contains ONLY optimization-specific business logic - all infrastructure 
(reliability, execution, WebSocket events) inherited from BaseAgent.

Business Value: Core optimization recommendations drive customer cost savings.
Target segments: Growth & Enterprise. High revenue impact through performance fees.
BVJ: Growth & Enterprise | Performance & Cost Optimization | +30% cost reduction for customers
"""

from typing import Any, Dict, List, Optional

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.prompts import optimizations_core_prompt_template
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.utils import extract_json_from_response
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class OptimizationsCoreSubAgent(BaseAgent):
    """Clean optimization agent using BaseAgent infrastructure.
    
    Contains ONLY optimization-specific business logic - all infrastructure 
    (reliability, execution, WebSocket events) inherited from BaseAgent.
    """
    
    def __init__(self, llm_manager: Optional[LLMManager] = None, 
                 tool_dispatcher: Optional[ToolDispatcher] = None):
        # Initialize BaseAgent with full infrastructure
        super().__init__(
            llm_manager=llm_manager,
            name="OptimizationsCoreSubAgent", 
            description="Enhanced optimization agent using BaseAgent infrastructure",
            enable_reliability=True,      # Get circuit breaker + retry
            enable_execution_engine=True, # Get modern execution patterns
            enable_caching=True,          # Enable caching for optimization results
            tool_dispatcher=tool_dispatcher
        )
        self.tool_dispatcher = tool_dispatcher

    # Implement BaseAgent's abstract methods for optimization-specific logic
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions for optimization analysis."""
        state = context.state
        
        if not state.data_result:
            self.logger.warning(f"No data result available for optimization in run_id: {context.run_id}")
            return False
            
        if not state.triage_result:
            self.logger.warning(f"No triage result available for optimization in run_id: {context.run_id}")
            return False
            
        if not self.llm_manager:
            self.logger.error(f"No LLM manager available for optimization in run_id: {context.run_id}")
            return False
            
        return True
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute optimization analysis core logic with WebSocket events."""
        # Emit thinking event (agent_started is handled by orchestrator)
        await self.emit_thinking("Starting optimization analysis based on data insights...")
        
        # Emit progress for strategy formulation
        await self.emit_progress("Analyzing data patterns and formulating optimization strategies...")
        
        # Build prompt and execute LLM
        prompt = self._build_optimization_prompt(context.state)
        
        # Emit tool executing event for LLM
        await self.emit_tool_executing("llm_analysis", {
            "model": "optimizations_core",
            "prompt_length": len(prompt)
        })
        
        try:
            llm_response = await self.llm_manager.ask_llm(prompt, llm_config_name='optimizations_core')
            
            # Emit tool completed event
            await self.emit_tool_completed("llm_analysis", {
                "response_length": len(llm_response),
                "status": "success"
            })
            
        except Exception as e:
            await self.emit_tool_completed("llm_analysis", {
                "status": "error",
                "error": str(e)
            })
            raise
        
        # Process the response
        await self.emit_progress("Processing optimization recommendations...")
        result = await self._process_optimization_response(llm_response, context)
        
        # Emit completion event
        await self.emit_progress("Optimization strategies formulated successfully", is_complete=True)
        
        return result
    
    # Legacy compatibility method
    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if we have data and triage results to work with."""
        return state.data_result is not None and state.triage_result is not None
    
    # Backward Compatibility - Original execute method using BaseAgent infrastructure
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute with backward compatibility (delegates to BaseAgent patterns)."""
        # Use BaseAgent's execute_modern method which handles reliability and execution patterns
        result = await self.execute_modern(state, run_id, stream_updates)
        
        if result.success:
            state.optimizations_result = self._create_optimizations_result(result.result)
        else:
            # Create fallback result on failure
            fallback_result = self._create_default_fallback_result()
            state.optimizations_result = self._create_optimizations_result(fallback_result)
    
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
