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
        
        async def _execute_optimization():
            # Update status via WebSocket
            if stream_updates:
                await self._send_update(run_id, {
                    "status": "processing",
                    "message": "Formulating optimization strategies based on data analysis..."
                })

            prompt = optimizations_core_prompt_template.format(
                data=state.data_result,
                triage_result=state.triage_result,
                user_request=state.user_request
            )

            llm_response_str = await self.llm_manager.ask_llm(prompt, llm_config_name='optimizations_core')
            
            optimizations_result = extract_json_from_response(llm_response_str)
            if not optimizations_result:
                self.logger.warning(f"Could not extract JSON from LLM response for run_id: {run_id}. Using default optimizations.")
                optimizations_result = {
                    "optimizations": [],
                }

            state.optimizations_result = optimizations_result
            
            # Update with results
            if stream_updates:
                await self._send_update(run_id, {
                    "status": "processed",
                    "message": "Optimization strategies formulated successfully",
                    "result": optimizations_result
                })
            
            return optimizations_result
        
        async def _fallback_optimization():
            """Fallback optimization when main operation fails"""
            logger.warning(f"Using fallback optimization for run_id: {run_id}")
            fallback_result = {
                "optimizations": [
                    {
                        "type": "general",
                        "description": "Basic optimization analysis",
                        "priority": "medium",
                        "fallback": True
                    }
                ],
                "metadata": {
                    "fallback_used": True,
                    "reason": "Primary optimization analysis failed"
                }
            }
            state.optimizations_result = fallback_result
            
            if stream_updates:
                await self._send_update(run_id, {
                    "status": "completed_with_fallback",
                    "message": "Optimization completed with fallback method",
                    "result": fallback_result
                })
            
            return fallback_result
        
        # Execute with reliability protection
        await self.reliability.execute_safely(
            _execute_optimization,
            "execute_optimization",
            fallback=_fallback_optimization,
            timeout=30.0
        )
    
    def get_health_status(self) -> dict:
        """Get agent health status"""
        return self.reliability.get_health_status()
    
    def get_circuit_breaker_status(self) -> dict:
        """Get circuit breaker status"""
        return self.reliability.circuit_breaker.get_status()
