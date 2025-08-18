# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-10T18:47:58.913945+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Add baseline agent tracking to sub-agents
# Git: v6 | 2c55fb99 | dirty (27 uncommitted)
# Change: Feature | Scope: Component | Risk: High
# Session: ca70b55b-5f0c-4900-9648-9218422567b5 | Seq: 3
# Review: Pending | Score: 85
# ================================
import json
from typing import Any, List

from app.llm.llm_manager import LLMManager
from app.agents.base import BaseSubAgent
from app.agents.prompts import optimizations_core_prompt_template
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.agents.utils import extract_json_from_response
from app.logging_config import central_logger as logger
from app.core.reliability import (
    get_reliability_wrapper, CircuitBreakerConfig, RetryConfig
)
from app.llm.observability import (
    start_llm_heartbeat, stop_llm_heartbeat, generate_llm_correlation_id,
    log_agent_communication, log_agent_input, log_agent_output
)


class OptimizationsCoreSubAgent(BaseSubAgent):
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher):
        super().__init__(llm_manager, name="OptimizationsCoreSubAgent", description="This agent formulates optimization strategies.")
        self.tool_dispatcher = tool_dispatcher
        self.reliability = self._initialize_reliability_wrapper()
    
    def _initialize_reliability_wrapper(self):
        """Initialize reliability wrapper with circuit breaker and retry configs."""
        circuit_config = self._create_circuit_breaker_config()
        retry_config = self._create_retry_config()
        return get_reliability_wrapper("OptimizationsCoreSubAgent", circuit_config, retry_config)
    
    def _create_circuit_breaker_config(self) -> CircuitBreakerConfig:
        """Create circuit breaker configuration."""
        return CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30.0,
            name="OptimizationsCoreSubAgent"
        )
    
    def _create_retry_config(self) -> RetryConfig:
        """Create retry configuration."""
        return RetryConfig(
            max_retries=2,
            base_delay=1.0,
            max_delay=10.0
        )

    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if we have data and triage results to work with."""
        return state.data_result is not None and state.triage_result is not None
    
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute the optimizations core logic."""
        # Log agent communication start
        log_agent_communication("Supervisor", "OptimizationsCoreSubAgent", run_id, "execute_request")
        
        main_operation = self._create_main_optimization_operation(state, run_id, stream_updates)
        fallback_operation = self._create_fallback_optimization_operation(state, run_id, stream_updates)
        
        await self.reliability.execute_safely(
            main_operation,
            "execute_optimization",
            fallback=fallback_operation,
            timeout=30.0
        )
        
        # Log agent communication completion
        log_agent_communication("OptimizationsCoreSubAgent", "Supervisor", run_id, "execute_response")
    
    def _create_main_optimization_operation(self, state: DeepAgentState, run_id: str, stream_updates: bool):
        """Create the main optimization operation function."""
        async def _execute_optimization():
            await self._send_processing_update(run_id, stream_updates)
            prompt = self._build_optimization_prompt(state)
            correlation_id = generate_llm_correlation_id()
            
            llm_response_str = await self._execute_llm_with_observability(prompt, correlation_id)
            return await self._process_optimization_response(llm_response_str, run_id, stream_updates, state)
        return _execute_optimization
    
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
    
    async def _process_optimization_response(
        self, llm_response_str: str, run_id: str, stream_updates: bool, state: DeepAgentState
    ) -> dict:
        """Process LLM response and update state."""
        optimizations_result = self._extract_and_validate_result(llm_response_str, run_id)
        state.optimizations_result = self._create_optimizations_result(optimizations_result)
        await self._send_success_update(run_id, stream_updates, optimizations_result)
        return optimizations_result
    
    def _create_fallback_optimization_operation(self, state: DeepAgentState, run_id: str, stream_updates: bool):
        """Create the fallback optimization operation function."""
        async def _fallback_optimization():
            logger.warning(f"Using fallback optimization for run_id: {run_id}")
            fallback_result = self._create_default_fallback_result()
            state.optimizations_result = self._create_optimizations_result(fallback_result)
            await self._send_fallback_update(run_id, stream_updates, fallback_result)
            return fallback_result
        return _fallback_optimization
    
    async def _send_processing_update(self, run_id: str, stream_updates: bool) -> None:
        """Send processing status update via WebSocket."""
        if stream_updates:
            await self._send_update(run_id, {
                "status": "processing",
                "message": "Formulating optimization strategies based on data analysis..."
            })
    
    def _build_optimization_prompt(self, state: DeepAgentState) -> str:
        """Build the optimization prompt from state data."""
        return optimizations_core_prompt_template.format(
            data=state.data_result,
            triage_result=state.triage_result,
            user_request=state.user_request
        )
    
    def _extract_and_validate_result(self, llm_response_str: str, run_id: str) -> dict:
        """Extract and validate JSON result from LLM response."""
        optimizations_result = extract_json_from_response(llm_response_str)
        if not optimizations_result:
            self.logger.warning(f"Could not extract JSON from LLM response for run_id: {run_id}. Using default optimizations.")
            optimizations_result = {"optimizations": []}
        return optimizations_result
    
    async def _send_success_update(self, run_id: str, stream_updates: bool, result: dict) -> None:
        """Send success status update via WebSocket."""
        if stream_updates:
            await self._send_update(run_id, {
                "status": "processed",
                "message": "Optimization strategies formulated successfully",
                "result": result
            })
    
    def _create_default_fallback_result(self) -> dict:
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
    
    def _get_fallback_metadata(self) -> dict:
        """Get fallback metadata dictionary."""
        return {
            "fallback_used": True,
            "reason": "Primary optimization analysis failed"
        }
    
    async def _send_fallback_update(self, run_id: str, stream_updates: bool, result: dict) -> None:
        """Send fallback completion update via WebSocket."""
        if stream_updates:
            await self._send_update(run_id, {
                "status": "completed_with_fallback",
                "message": "Optimization completed with fallback method",
                "result": result
            })

    def get_health_status(self) -> dict:
        """Get agent health status"""
        return self.reliability.get_health_status()
    
    def get_circuit_breaker_status(self) -> dict:
        """Get circuit breaker status"""
        return self.reliability.circuit_breaker.get_status()
    
    def _create_optimizations_result(self, data: dict) -> 'OptimizationsResult':
        """Convert dictionary to OptimizationsResult object."""
        from app.agents.state import OptimizationsResult
        
        recommendations = self._extract_recommendations(data)
        processed_recommendations = self._process_recommendations(recommendations)
        return self._build_optimizations_result(data, processed_recommendations)
    
    def _extract_recommendations(self, data: dict) -> Any:
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
    
    def _build_optimizations_result(self, data: dict, recommendations: List[str]) -> 'OptimizationsResult':
        """Build OptimizationsResult from processed data."""
        from app.agents.state import OptimizationsResult
        return OptimizationsResult(
            optimization_type=self._get_optimization_type(data),
            recommendations=recommendations,
            confidence_score=data.get("confidence_score", 0.8),
            cost_savings=data.get("cost_savings"),
            performance_improvement=data.get("performance_improvement"),
            metadata=data.get("metadata", {})
        )
    
    def _get_optimization_type(self, data: dict) -> str:
        """Extract optimization type from data with fallback."""
        return data.get("optimization_type", data.get("type", "general"))
