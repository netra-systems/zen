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
from app.agents.input_validation import validate_agent_input
from app.llm.observability import (
    start_llm_heartbeat, stop_llm_heartbeat, generate_llm_correlation_id,
    log_agent_communication, log_agent_input, log_agent_output
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
    
    @validate_agent_input('ReportingSubAgent')
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute the reporting logic."""
        # Log agent communication start
        log_agent_communication("Supervisor", "ReportingSubAgent", run_id, "execute_request")
        
        main_operation = self._create_main_reporting_operation(state, run_id, stream_updates)
        fallback_operation = self._create_fallback_reporting_operation(state, run_id, stream_updates)
        
        await self.reliability.execute_safely(
            main_operation,
            "execute_reporting",
            fallback=fallback_operation,
            timeout=30.0
        )
        
        # Log agent communication completion
        log_agent_communication("ReportingSubAgent", "Supervisor", run_id, "execute_response")
    
    def _create_main_reporting_operation(self, state: DeepAgentState, run_id: str, stream_updates: bool):
        """Create the main reporting operation function."""
        async def _execute_reporting():
            await self._send_processing_update(run_id, stream_updates)
            prompt = self._build_reporting_prompt(state)
            
            # Generate correlation ID and start heartbeat
            correlation_id = generate_llm_correlation_id()
            start_llm_heartbeat(correlation_id, "ReportingSubAgent")
            
            try:
                # Log input to LLM
                log_agent_input("ReportingSubAgent", "LLM", len(prompt), correlation_id)
                
                llm_response_str = await self.llm_manager.ask_llm(prompt, llm_config_name='reporting')
                
                # Log output from LLM
                log_agent_output("LLM", "ReportingSubAgent", 
                               len(llm_response_str), "success", correlation_id)
                
            except Exception as e:
                # Log error output
                log_agent_output("LLM", "ReportingSubAgent", 0, "error", correlation_id)
                raise
            finally:
                # Stop heartbeat
                stop_llm_heartbeat(correlation_id)
            
            report_result = self._extract_and_validate_report(llm_response_str, run_id)
            state.report_result = self._create_report_result(report_result)
            await self._send_success_update(run_id, stream_updates, report_result)
            return report_result
        return _execute_reporting
    
    def _create_fallback_reporting_operation(self, state: DeepAgentState, run_id: str, stream_updates: bool):
        """Create the fallback reporting operation function."""
        async def _fallback_reporting():
            logger.warning(f"Using fallback reporting for run_id: {run_id}")
            fallback_result = self._create_default_fallback_report(state)
            state.report_result = self._create_report_result(fallback_result)
            await self._send_fallback_update(run_id, stream_updates, fallback_result)
            return fallback_result
        return _fallback_reporting
    
    async def _send_processing_update(self, run_id: str, stream_updates: bool) -> None:
        """Send processing status update via WebSocket."""
        if stream_updates:
            await self._send_update(run_id, {
                "status": "processing",
                "message": "Generating final report with all analysis results..."
            })
    
    def _build_reporting_prompt(self, state: DeepAgentState) -> str:
        """Build the reporting prompt from state data."""
        return reporting_prompt_template.format(
            action_plan=state.action_plan_result,
            optimizations=state.optimizations_result,
            data=state.data_result,
            triage_result=state.triage_result,
            user_request=state.user_request
        )
    
    def _extract_and_validate_report(self, llm_response_str: str, run_id: str) -> dict:
        """Extract and validate JSON result from LLM response."""
        report_result = extract_json_from_response(llm_response_str)
        if not report_result:
            self.logger.warning(f"Could not extract JSON from LLM response for run_id: {run_id}. Using default report.")
            report_result = {"report": "No report could be generated."}
        return report_result
    
    async def _send_success_update(self, run_id: str, stream_updates: bool, result: dict) -> None:
        """Send success status update via WebSocket."""
        if stream_updates:
            await self._send_update(run_id, {
                "status": "processed",
                "message": "Final report generated successfully",
                "result": result
            })
    
    def _create_default_fallback_report(self, state: DeepAgentState) -> dict:
        """Create default fallback report result."""
        return {
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
    
    async def _send_fallback_update(self, run_id: str, stream_updates: bool, result: dict) -> None:
        """Send fallback completion update via WebSocket."""
        if stream_updates:
            await self._send_update(run_id, {
                "status": "completed_with_fallback",
                "message": "Report completed with fallback method",
                "result": result
            })

    def get_health_status(self) -> dict:
        """Get agent health status"""
        return self.reliability.get_health_status()
    
    def get_circuit_breaker_status(self) -> dict:
        """Get circuit breaker status"""
        return self.reliability.circuit_breaker.get_status()
    
    def _create_report_result(self, data: dict) -> 'ReportResult':
        """Convert dictionary to ReportResult object."""
        from app.agents.state import ReportResult
        return ReportResult(
            report_type="analysis",
            content=data.get("report", "No content available"),
            sections=data.get("sections", []),
            metadata=data.get("metadata", {})
        )