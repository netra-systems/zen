# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-10T18:47:58.913945+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Add baseline agent tracking to sub-agents
# Git: v6 | 2c55fb99 | dirty (27 uncommitted)
# Change: Feature | Scope: Component | Risk: High
# Session: ca70b55b-5f0c-4900-9648-9218422567b5 | Seq: 4
# Review: Pending | Score: 85
# ================================
import json

from app.llm.llm_manager import LLMManager
from app.agents.base import BaseSubAgent
from app.agents.prompts import reporting_prompt_template
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.agents.utils import extract_json_from_response
from app.logging_config import central_logger as logger
from app.core.reliability import (
    get_reliability_wrapper, CircuitBreakerConfig, RetryConfig
)


class ReportingSubAgent(BaseSubAgent):
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher):
        super().__init__(llm_manager, name="ReportingSubAgent", description="This agent generates a final report.")
        self.tool_dispatcher = tool_dispatcher
        
        # Initialize reliability wrapper
        self.reliability = get_reliability_wrapper(
            "ReportingSubAgent",
            CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=30.0,
                name="ReportingSubAgent"
            ),
            RetryConfig(
                max_retries=2,
                base_delay=1.0,
                max_delay=10.0
            )
        )

    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if we have all previous results to generate a report."""
        return (state.action_plan_result is not None and 
                state.optimizations_result is not None and 
                state.data_result is not None and 
                state.triage_result is not None)
    
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute the reporting logic."""
        
        async def _execute_reporting():
            # Update status via WebSocket
            if stream_updates:
                await self._send_update(run_id, {
                    "status": "processing",
                    "message": "Generating final report with all analysis results..."
                })

            prompt = reporting_prompt_template.format(
                action_plan=state.action_plan_result,
                optimizations=state.optimizations_result,
                data=state.data_result,
                triage_result=state.triage_result,
                user_request=state.user_request
            )

            llm_response_str = await self.llm_manager.ask_llm(prompt, llm_config_name='reporting')
            
            report_result = extract_json_from_response(llm_response_str)
            if not report_result:
                self.logger.warning(f"Could not extract JSON from LLM response for run_id: {run_id}. Using default report.")
                report_result = {
                    "report": "No report could be generated.",
                }

            state.report_result = report_result
            
            # Update with results
            if stream_updates:
                await self._send_update(run_id, {
                    "status": "processed",
                    "message": "Final report generated successfully",
                    "result": report_result
                })
            
            return report_result
        
        async def _fallback_reporting():
            """Fallback reporting when main operation fails"""
            logger.warning(f"Using fallback reporting for run_id: {run_id}")
            fallback_result = {
                "report": "Report generation failed. Using fallback summary.",
                "summary": {
                    "status": "Analysis completed with limitations",
                    "data_analyzed": bool(state.data_result),
                    "optimizations_provided": bool(state.optimizations_result),
                    "action_plan_created": bool(state.action_plan_result),
                    "fallback_used": True
                },
                "metadata": {
                    "fallback_used": True,
                    "reason": "Primary report generation failed"
                }
            }
            state.report_result = fallback_result
            
            if stream_updates:
                await self._send_update(run_id, {
                    "status": "completed_with_fallback",
                    "message": "Report completed with fallback method",
                    "result": fallback_result
                })
            
            return fallback_result
        
        # Execute with reliability protection
        await self.reliability.execute_safely(
            _execute_reporting,
            "execute_reporting",
            fallback=_fallback_reporting,
            timeout=30.0
        )
    
    def get_health_status(self) -> dict:
        """Get agent health status"""
        return self.reliability.get_health_status()
    
    def get_circuit_breaker_status(self) -> dict:
        """Get circuit breaker status"""
        return self.reliability.circuit_breaker.get_status()
