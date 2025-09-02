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
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.agents.base.circuit_breaker import CircuitBreakerConfig
from netra_backend.app.agents.base.interface import (
    ExecutionContext, ExecutionResult, WebSocketManagerProtocol
)
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.core.unified_error_handler import agent_error_handler as ExecutionErrorHandler
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.agents.base.reliability_manager import ReliabilityManager
from netra_backend.app.agents.input_validation import validate_agent_input
from netra_backend.app.agents.prompts import reporting_prompt_template
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


class ReportingSubAgent(BaseSubAgent):
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher,
                 websocket_manager: Optional[WebSocketManagerProtocol] = None):
        super().__init__(llm_manager, name="ReportingSubAgent", description="This agent generates a final report.")
        # Using single inheritance with standardized execution patterns
        self.tool_dispatcher = tool_dispatcher
        self._initialize_modern_components()
    
    
    def _initialize_modern_components(self) -> None:
        """Initialize modern execution components."""
        self._init_reliability_manager()
        self._init_monitoring()
        self._init_error_handler()
    
    def _init_reliability_manager(self) -> None:
        """Initialize modern reliability manager."""
        circuit_config = self._create_modern_circuit_config()
        retry_config = self._create_modern_retry_config()
        self.reliability_manager = ReliabilityManager(circuit_config, retry_config)
    
    def _init_monitoring(self) -> None:
        """Initialize execution monitoring."""
        self.execution_monitor = ExecutionMonitor()
    
    def _init_error_handler(self) -> None:
        """Initialize modern error handling."""
        self.error_handler = ExecutionErrorHandler
    
    
    def _create_modern_circuit_config(self) -> CircuitBreakerConfig:
        """Create modern circuit breaker configuration."""
        return CircuitBreakerConfig(
            name="ReportingSubAgent_Modern",
            failure_threshold=3,
            recovery_timeout=30
        )
    
    
    def _create_modern_retry_config(self) -> RetryConfig:
        """Create modern retry configuration."""
        return RetryConfig(
            max_retries=2,
            base_delay=1.0,
            max_delay=10.0
        )

    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if we have all previous results to generate a report."""
        return (state.action_plan_result is not None and 
                state.optimizations_result is not None and 
                state.data_result is not None and 
                state.triage_result is not None)
    
    @validate_agent_input('ReportingSubAgent')
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute the reporting logic with WebSocket notifications."""
        import time
        
        # Log agent communication start
        log_agent_communication("Supervisor", "ReportingSubAgent", run_id, "execute_request")
        
        # Send agent started notification using mixin methods
        await self.emit_thinking("Compiling analysis results into comprehensive report...")
        
        start_time = time.time()
        try:
            main_operation = self._create_main_reporting_operation(state, run_id, stream_updates)
            fallback_operation = self._create_fallback_reporting_operation(state, run_id, stream_updates)
            
            await self.reliability.execute_safely(
                main_operation,
                "execute_reporting",
                fallback=fallback_operation,
                timeout=30.0
            )
            
            # Send agent completed notification using mixin methods
            await self.emit_progress("Final report generation completed", is_complete=True)
                
        except Exception as e:
            # Send agent error notification using mixin methods
            await self.emit_error(str(e), type(e).__name__)
            raise
        
        # Log agent communication completion
        log_agent_communication("ReportingSubAgent", "Supervisor", run_id, "execute_response")
    
    
    
    def _extract_completion_result(self, state: DeepAgentState) -> Dict[str, Any]:
        """Extract completion result for WebSocket notification."""
        if hasattr(state, 'final_report') and state.final_report:
            return {
                "status": "success",
                "report_generated": True,
                "analysis_type": "comprehensive_report"
            }
        return {"status": "completed"}
    
    def _create_main_reporting_operation(self, state: DeepAgentState, run_id: str, stream_updates: bool):
        """Create the main reporting operation function."""
        async def _execute_reporting():
            await self._send_processing_update(run_id, stream_updates)
            
            # Send thinking notification using mixin methods
            await self.emit_thinking("Building comprehensive analysis prompt...")
            
            prompt = self._build_reporting_prompt(state)
            correlation_id = generate_llm_correlation_id()
            
            # Send LLM execution notification using mixin methods
            await self.emit_thinking("Generating final report with AI model...")
            
            llm_response_str = await self._execute_reporting_llm_with_observability(prompt, correlation_id)
            
            # Send processing notification using mixin methods
            await self.emit_thinking("Processing and formatting report results...")
            
            return await self._process_reporting_response(llm_response_str, run_id, stream_updates, state)
        return _execute_reporting
    
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
    
    async def _process_reporting_response(
        self, llm_response_str: str, run_id: str, stream_updates: bool, state: DeepAgentState
    ) -> dict:
        """Process LLM response and update state for reporting."""
        report_result = self._extract_and_validate_report(llm_response_str, run_id)
        state.report_result = self._create_report_result(report_result)
        await self._send_success_update(run_id, stream_updates, report_result)
        return report_result
    
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
            "summary": self._create_fallback_summary(state),
            "metadata": self._create_fallback_metadata()
        }
    
    def _create_fallback_summary(self, state: DeepAgentState) -> dict:
        """Create fallback summary from state."""
        return {
            "status": "Analysis completed with limitations",
            "data_analyzed": bool(state.data_result),
            "optimizations_provided": bool(state.optimizations_result),
            "action_plan_created": bool(state.action_plan_result),
            "fallback_used": True
        }
    
    def _create_fallback_metadata(self) -> dict:
        """Create fallback metadata dictionary."""
        return {
            "fallback_used": True,
            "reason": "Primary report generation failed"
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
        """Get comprehensive agent health status"""
        legacy_health = self.reliability.get_health_status()
        modern_health = self._get_modern_health_status()
        return {**legacy_health, "modern_components": modern_health}
    
    def _get_modern_health_status(self) -> Dict[str, Any]:
        """Get modern component health status."""
        return {
            "reliability_manager": self.reliability_manager.get_health_status(),
            "execution_monitor": self.execution_monitor.get_health_status(),
            "error_handler": self.error_handler.get_health_status()
        }
    
    def get_circuit_breaker_status(self) -> dict:
        """Get circuit breaker status"""
        return self.reliability.circuit_breaker.get_status()
    
    def _create_report_result(self, data: dict) -> 'ReportResult':
        """Convert dictionary to ReportResult object."""
        from netra_backend.app.agents.state import ReportResult
        return ReportResult(
            report_type="analysis",
            content=data.get("report", "No content available"),
            sections=data.get("sections", []),
            metadata=data.get("metadata", {})
        )
    
    # Standardized execution patterns implementation
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions for reporting."""
        return self._validate_state_has_results(context.state)
    
    def _validate_state_has_results(self, state: DeepAgentState) -> bool:
        """Check if state has all required analysis results."""
        required_results = [state.action_plan_result, state.optimizations_result, 
                          state.data_result, state.triage_result]
        return all(result is not None for result in required_results)
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute core reporting logic with modern patterns."""
        await self.send_status_update(context, "processing", 
                                    "Generating final report with all analysis results...")
        
        prompt = self._build_reporting_prompt(context.state)
        correlation_id = generate_llm_correlation_id()
        
        llm_response_str = await self._execute_reporting_llm_with_observability(
            prompt, correlation_id)
        return await self._process_reporting_response_modern(llm_response_str, context)
    
    async def _process_reporting_response_modern(self, llm_response_str: str, 
                                               context: ExecutionContext) -> Dict[str, Any]:
        """Process LLM response with modern context handling."""
        report_result = self._extract_and_validate_report(llm_response_str, context.run_id)
        context.state.report_result = self._create_report_result(report_result)
        
        await self.send_status_update(context, "processed", 
                                    "Final report generated successfully")
        return report_result
    
    async def execute_modern(self, state: DeepAgentState, run_id: str, 
                           stream_updates: bool = False) -> ExecutionResult:
        """Modern execute method using standardized execution patterns."""
        context = self._create_execution_context(state, run_id, stream_updates)
        
        try:
            return await self._execute_with_reliability(context)
        except Exception as e:
            return await self.error_handler.handle_execution_error(e, context)
    
    def _create_execution_context(self, state: DeepAgentState, run_id: str, 
                                stream_updates: bool) -> ExecutionContext:
        """Create execution context for modern interface."""
        return ExecutionContext(
            run_id=run_id,
            agent_name=self.agent_name,
            state=state,
            stream_updates=stream_updates,
            start_time=datetime.now(timezone.utc),
            correlation_id=generate_llm_correlation_id()
        )
    
    async def _execute_with_reliability(self, context: ExecutionContext) -> ExecutionResult:
        """Execute with reliability manager patterns."""
        if not await self.validate_preconditions(context):
            error_msg = "Missing required analysis results for reporting"
            return self._create_precondition_error_result(error_msg)
        
        return await self.reliability_manager.execute_with_reliability(
            context, self._core_execution_wrapper
        )
    
    def _create_precondition_error_result(self, error_msg: str) -> ExecutionResult:
        """Create error result for precondition failures."""
        return ExecutionResult(
            success=False,
            status=ExecutionStatus.FAILED,
            error=error_msg,
            execution_time_ms=0.0
        )
    
    async def _core_execution_wrapper(self, context: ExecutionContext) -> ExecutionResult:
        """Wrapper for core execution logic."""
        start_time = datetime.now(timezone.utc)
        try:
            result = await self.execute_core_logic(context)
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            return self._create_success_execution_result(result, execution_time)
        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            return self._create_error_execution_result(str(e), execution_time)
    
    def _create_success_execution_result(self, result: Dict[str, Any], 
                                       execution_time_ms: float) -> ExecutionResult:
        """Create successful execution result."""
        return ExecutionResult(
            success=True,
            status=ExecutionStatus.COMPLETED,
            result=result,
            execution_time_ms=execution_time_ms
        )
    
    def _create_error_execution_result(self, error: str, 
                                     execution_time_ms: float) -> ExecutionResult:
        """Create error execution result."""
        return ExecutionResult(
            success=False,
            status=ExecutionStatus.FAILED,
            error=error,
            execution_time_ms=execution_time_ms
        )