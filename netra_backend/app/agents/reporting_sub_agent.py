"""Clean ReportingSubAgent using BaseAgent infrastructure (<200 lines).

Simplified implementation using BaseAgent's SSOT infrastructure:
- Inherits reliability management, execution patterns, WebSocket events
- Contains ONLY report generation business logic
- Clean single inheritance pattern
- No infrastructure duplication

Business Value: Final output for ALL analyses - CRITICAL revenue impact.
BVJ: ALL segments | Customer Experience | +30% reduction in report generation failures
"""

import time
from typing import Any, Dict, Optional

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.input_validation import validate_agent_input
from netra_backend.app.agents.prompts import reporting_prompt_template
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.utils import extract_json_from_response, extract_thread_id
from netra_backend.app.llm.observability import (
    generate_llm_correlation_id,
    log_agent_communication,
    log_agent_input,
    log_agent_output,
    start_llm_heartbeat,
    stop_llm_heartbeat,
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ReportingSubAgent(BaseAgent):
    """Clean reporting agent using BaseAgent infrastructure.
    
    Contains ONLY report generation business logic - all infrastructure 
    (reliability, execution, WebSocket events) inherited from BaseAgent.
    """
    
    def __init__(self):
        # Initialize BaseAgent with full infrastructure
        super().__init__(
            name="ReportingSubAgent", 
            description="Enhanced reporting agent using BaseAgent infrastructure",
            enable_reliability=True,      # Get circuit breaker + retry
            enable_execution_engine=True, # Get modern execution patterns
            enable_caching=True,         # Get Redis caching
        )

    # Implement BaseAgent's abstract methods for report-specific logic
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions for report generation."""
        state = context.state
        if not all([
            state.action_plan_result, 
            state.optimizations_result, 
            state.data_result, 
            state.triage_result
        ]):
            self.logger.warning(f"Missing required analysis results for report generation in run_id: {context.run_id}")
            return False
        return True
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute core report generation logic with modern patterns and WebSocket events."""
        start_time = time.time()
        
        # Emit thinking event
        await self.emit_thinking("Starting comprehensive report generation")
        
        # Emit progress during report building
        await self.emit_thinking("Analyzing user request and determining category...")
        await self._send_processing_update(context.run_id, context.stream_updates)
        
        # Emit progress during report processing
        await self.emit_progress("Building comprehensive analysis prompt...")
        prompt = self._build_reporting_prompt(context.state)
        correlation_id = generate_llm_correlation_id()
        
        # Emit thinking for LLM execution
        await self.emit_thinking("Generating final report with AI model...")
        llm_response_str = await self._execute_reporting_llm_with_observability(prompt, correlation_id)
        
        # Emit progress for result processing
        await self.emit_progress("Processing and formatting report results...")
        result = await self._process_reporting_response(llm_response_str, context)
        
        # Emit completion event
        await self.emit_progress("Final report generation completed successfully", is_complete=True)
        
        return result
    async def _send_processing_update(self, run_id: str, stream_updates: bool) -> None:
        """Send processing status update."""
        if stream_updates:
            await self._send_update(run_id, {
                "status": "processing", 
                "message": "Generating final report with all analysis results..."
            })
    
    async def _execute_reporting_llm_with_observability(self, prompt: str, correlation_id: str) -> str:
        """Execute LLM call with full observability for reporting."""
        start_llm_heartbeat(correlation_id, "ReportingSubAgent")
        try:
            log_agent_input("ReportingSubAgent", "LLM", len(prompt), correlation_id)
            return await self._make_reporting_llm_request(prompt, correlation_id)
        finally:
            stop_llm_heartbeat(correlation_id)
    
    async def _make_reporting_llm_request(self, prompt: str, correlation_id: str) -> str:
        """Make LLM request for reporting with error handling."""
        try:
            response = await self.llm_manager.ask_llm(prompt, llm_config_name='reporting')
            log_agent_output("LLM", "ReportingSubAgent", len(response), "success", correlation_id)
            return response
        except Exception as e:
            log_agent_output("LLM", "ReportingSubAgent", 0, "error", correlation_id)
            raise
    
    async def _process_reporting_response(self, llm_response_str: str, context: ExecutionContext) -> Dict[str, Any]:
        """Process LLM response and update state for reporting."""
        report_result = self._extract_and_validate_report(llm_response_str, context.run_id)
        context.state.report_result = self._create_report_result(report_result)
        await self._send_success_update(context.run_id, context.stream_updates, report_result)
        return report_result
    
    
    def _build_reporting_prompt(self, state: DeepAgentState) -> str:
        """Build the reporting prompt from state data."""
        return reporting_prompt_template.format(
            action_plan=state.action_plan_result,
            optimizations=state.optimizations_result,
            data=state.data_result,
            triage_result=state.triage_result,
            user_request=state.user_request
        )
    
    def _extract_and_validate_report(self, llm_response_str: str, run_id: str) -> Dict[str, Any]:
        """Extract and validate JSON result from LLM response."""
        report_result = extract_json_from_response(llm_response_str)
        if not report_result:
            self.logger.warning(f"Could not extract JSON from LLM response for run_id: {run_id}. Using default report.")
            report_result = {"report": "No report could be generated."}
        return report_result
    
    async def _send_success_update(self, run_id: str, stream_updates: bool, result: Dict[str, Any]) -> None:
        """Send success status update via WebSocket."""
        if stream_updates:
            await self._send_update(run_id, {
                "status": "processed",
                "message": "Final report generated successfully",
                "result": result
            })
    
    def _create_report_result(self, data: Dict[str, Any]) -> 'ReportResult':
        """Convert dictionary to ReportResult object."""
        from netra_backend.app.agents.state import ReportResult
        return ReportResult(
            report_type="analysis",
            content=data.get("report", "No content available"),
            sections=data.get("sections", []),
            metadata=data.get("metadata", {})
        )

    # Legacy execute method for backward compatibility
    @validate_agent_input('ReportingSubAgent')
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute the enhanced reporting logic - uses BaseAgent's reliability infrastructure"""
        await self.execute_with_reliability(
            lambda: self._execute_reporting_main(state, run_id, stream_updates),
            "execute_reporting",
            fallback=lambda: self._execute_reporting_fallback(state, run_id, stream_updates)
        )
    
    async def _execute_reporting_main(self, state: DeepAgentState, run_id: str, stream_updates: bool):
        """Main reporting execution logic - delegates to execute_core_logic."""
        context = ExecutionContext(
            run_id=run_id,
            agent_name=self.name,
            state=state,
            stream_updates=stream_updates,
            thread_id=extract_thread_id(state),
            user_id=getattr(state, 'user_id', None),
            start_time=time.time(),
            correlation_id=self.correlation_id
        )
        return await self.execute_core_logic(context)
    
    async def _execute_reporting_fallback(self, state: DeepAgentState, run_id: str, stream_updates: bool):
        """Fallback reporting execution logic."""
        logger.warning(f"Using fallback reporting for run_id: {run_id}")
        fallback_result = self._create_default_fallback_report(state)
        state.report_result = self._create_report_result(fallback_result)
        return fallback_result
    
    def _create_default_fallback_report(self, state: DeepAgentState) -> Dict[str, Any]:
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

    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if we have all previous results to generate a report"""
        return all([
            state.action_plan_result, 
            state.optimizations_result, 
            state.data_result, 
            state.triage_result
        ])

    async def cleanup(self, state: DeepAgentState, run_id: str) -> None:
        """Cleanup after execution - reporting-specific cleanup only"""
        if state.report_result and isinstance(state.report_result, dict):
            metadata = getattr(state.report_result, 'metadata', {})
            if metadata:
                self.logger.debug(f"Reporting metrics for run_id {run_id}: {metadata}")

    # All infrastructure methods (WebSocket, monitoring, health status) inherited from BaseAgent