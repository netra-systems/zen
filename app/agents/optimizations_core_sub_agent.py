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


class OptimizationsCoreSubAgent(BaseSubAgent):
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher):
        super().__init__(llm_manager, name="OptimizationsCoreSubAgent", description="This agent formulates optimization strategies.")
        self.tool_dispatcher = tool_dispatcher
        
        # Initialize reliability wrapper
        self.reliability = get_reliability_wrapper(
            "OptimizationsCoreSubAgent",
            CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=30.0,
                name="OptimizationsCoreSubAgent"
            ),
            RetryConfig(
                max_retries=2,
                base_delay=1.0,
                max_delay=10.0
            )
        )

    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if we have data and triage results to work with."""
        return state.data_result is not None and state.triage_result is not None
    
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute the optimizations core logic."""
        main_operation = self._create_main_optimization_operation(state, run_id, stream_updates)
        fallback_operation = self._create_fallback_optimization_operation(state, run_id, stream_updates)
        
        await self.reliability.execute_safely(
            main_operation,
            "execute_optimization",
            fallback=fallback_operation,
            timeout=30.0
        )
    
    def _create_main_optimization_operation(self, state: DeepAgentState, run_id: str, stream_updates: bool):
        """Create the main optimization operation function."""
        async def _execute_optimization():
            await self._send_processing_update(run_id, stream_updates)
            prompt = self._build_optimization_prompt(state)
            llm_response_str = await self.llm_manager.ask_llm(prompt, llm_config_name='optimizations_core')
            optimizations_result = self._extract_and_validate_result(llm_response_str, run_id)
            state.optimizations_result = self._create_optimizations_result(optimizations_result)
            await self._send_success_update(run_id, stream_updates, optimizations_result)
            return optimizations_result
        return _execute_optimization
    
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
            "recommendations": [
                "Basic optimization analysis - review current resource utilization",
                "Consider cost optimization opportunities based on usage patterns",
                "Evaluate performance improvements for critical workloads"
            ],
            "confidence_score": 0.5,
            "metadata": {
                "fallback_used": True,
                "reason": "Primary optimization analysis failed"
            }
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
        
        # Fix recommendations field - handle both dict and string formats
        recommendations = data.get("recommendations", data.get("optimizations", []))
        
        # Convert dict recommendations to list of strings
        if isinstance(recommendations, list):
            fixed_recommendations = []
            for rec in recommendations:
                if isinstance(rec, dict):
                    # Convert dict to string description
                    desc = rec.get("description", str(rec))
                    fixed_recommendations.append(desc)
                elif isinstance(rec, str):
                    fixed_recommendations.append(rec)
                else:
                    fixed_recommendations.append(str(rec))
            recommendations = fixed_recommendations
        elif not isinstance(recommendations, list):
            recommendations = [str(recommendations)] if recommendations else []
        
        return OptimizationsResult(
            optimization_type=data.get("optimization_type", data.get("type", "general")),
            recommendations=recommendations,
            confidence_score=data.get("confidence_score", 0.8),
            cost_savings=data.get("cost_savings"),
            performance_improvement=data.get("performance_improvement"),
            metadata=data.get("metadata", {})
        )
