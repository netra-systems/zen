"""Golden Pattern ReportingSubAgent - Clean business logic only (<200 lines).

Golden Pattern Implementation:
- Inherits reliability management, execution patterns, WebSocket events from BaseAgent
- Contains ONLY report generation business logic
- Clean single inheritance pattern
- No infrastructure duplication
- Proper AgentError handling
- <200 lines total

Business Value: Final output for ALL analyses - CRITICAL revenue impact.
BVJ: ALL segments | Customer Experience | +30% reduction in report generation failures
"""

import time
from typing import Any, Dict, Optional

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.agent_error_types import AgentValidationError
from netra_backend.app.agents.prompts import reporting_prompt_template
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.agents.utils import extract_json_from_response
from netra_backend.app.database.session_manager import DatabaseSessionManager
from netra_backend.app.llm.observability import (
    generate_llm_correlation_id,
    log_agent_input,
    log_agent_output,
    start_llm_heartbeat,
    stop_llm_heartbeat,
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ReportingSubAgent(BaseAgent):
    """Golden Pattern ReportingSubAgent - Clean business logic only.
    
    Contains ONLY report generation business logic - all infrastructure 
    (reliability, execution, WebSocket events) inherited from BaseAgent.
    Follows golden pattern: <200 lines, proper error handling, WebSocket events.
    """
    
    def __init__(self):
        # Initialize BaseAgent with full infrastructure
        super().__init__(
            name="ReportingSubAgent", 
            description="Golden Pattern reporting agent using BaseAgent infrastructure",
            enable_reliability=True,      # Get circuit breaker + retry
            enable_execution_engine=True, # Get modern execution patterns
            enable_caching=True,         # Get Redis caching
        )

    def _validate_analysis_results(self, context: UserExecutionContext) -> bool:
        """Validate required analysis results are present in context metadata."""
        metadata = context.metadata
        
        # Check for required analysis results in metadata
        required_results = [
            "action_plan_result",
            "optimizations_result", 
            "data_result", 
            "triage_result"
        ]
        
        missing_results = [name for name in required_results if not metadata.get(name)]
        if missing_results:
            error_msg = f"Missing required analysis results: {', '.join(missing_results)}"
            self.logger.warning(f"{error_msg} for run_id: {context.run_id}")
            raise AgentValidationError(error_msg, context={"run_id": context.run_id, "missing": missing_results})
            
        return True

    async def execute(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
        """Execute report generation with UserExecutionContext pattern."""
        # Validate context at method entry
        if not isinstance(context, UserExecutionContext):
            raise AgentValidationError(f"Invalid context type: {type(context)}")
        
        # Validate required analysis results
        self._validate_analysis_results(context)
        
        # Create database session manager for proper session isolation
        if context.db_session:
            db_manager = DatabaseSessionManager(context)
            
        try:
            self.logger.info(f"Starting report generation for run_id: {context.run_id}")
            
            # Build the reporting prompt from context metadata
            prompt = self._build_reporting_prompt(context)
            correlation_id = generate_llm_correlation_id()
            
            # Execute LLM for report generation
            llm_response_str = await self._execute_reporting_llm_with_observability(prompt, correlation_id)
            
            # Process and format results
            result = self._extract_and_validate_report(llm_response_str, context.run_id)
            
            # Send success update if streaming
            if stream_updates:
                await self._send_success_update(context.run_id, stream_updates, result)
            
            self.logger.info(f"Report generation completed successfully for run_id: {context.run_id}")
            return result
            
        except Exception as e:
            # Proper error handling
            self.logger.error(f"Report generation failed for run_id {context.run_id}: {str(e)}")
            
            # Create fallback report
            fallback_result = self._create_fallback_report(context)
            return fallback_result

    async def _execute_reporting_llm_with_observability(self, prompt: str, correlation_id: str) -> str:
        """Execute LLM call with full observability for reporting."""
        start_llm_heartbeat(correlation_id, "ReportingSubAgent")
        try:
            log_agent_input("ReportingSubAgent", "LLM", len(prompt), correlation_id)
            response = await self.llm_manager.ask_llm(prompt, llm_config_name='reporting')
            log_agent_output("LLM", "ReportingSubAgent", len(response), "success", correlation_id)
            return response
        except Exception as e:
            log_agent_output("LLM", "ReportingSubAgent", 0, "error", correlation_id)
            raise
        finally:
            stop_llm_heartbeat(correlation_id)

    def _build_reporting_prompt(self, context: UserExecutionContext) -> str:
        """Build the reporting prompt from context metadata."""
        metadata = context.metadata
        return reporting_prompt_template.format(
            action_plan=metadata.get("action_plan_result", ""),
            optimizations=metadata.get("optimizations_result", ""),
            data=metadata.get("data_result", ""),
            triage_result=metadata.get("triage_result", ""),
            user_request=metadata.get("user_request", "")
        )
    
    def _extract_and_validate_report(self, llm_response_str: str, run_id: str) -> Dict[str, Any]:
        """Extract and validate JSON result from LLM response."""
        report_result = extract_json_from_response(llm_response_str)
        if not report_result:
            self.logger.warning(f"Could not extract JSON from LLM response for run_id: {run_id}. Using fallback report.")
            report_result = {"report": "No report could be generated from LLM response."}
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
        from netra_backend.app.agents.state import ReportResult, ReportSection
        
        # Convert sections to ReportSection objects
        sections_data = data.get("sections", [])
        sections = [
            ReportSection(
                section_id=section.get("section_id", f"section_{i}") if isinstance(section, dict) else f"section_{i}",
                title=section.get("title", f"Section {i}") if isinstance(section, dict) else section.capitalize(),
                content=section.get("content", "") if isinstance(section, dict) else f"Content for {section}",
                section_type=section.get("section_type", "standard") if isinstance(section, dict) else "standard"
            )
            for i, section in enumerate(sections_data)
        ]
        
        return ReportResult(
            report_type="analysis",
            content=data.get("report", "No content available"),
            sections=sections,
            metadata=data.get("metadata", {})
        )

    def _create_fallback_report(self, context: UserExecutionContext) -> Dict[str, Any]:
        """Create fallback report when primary generation fails."""
        metadata = context.metadata
        return {
            "report": "Report generation encountered an error. Using fallback summary.",
            "summary": {
                "status": "Analysis completed with limitations",
                "data_analyzed": bool(metadata.get("data_result")),
                "optimizations_provided": bool(metadata.get("optimizations_result")),
                "action_plan_created": bool(metadata.get("action_plan_result")),
                "fallback_used": True
            },
            "metadata": {
                "fallback_used": True,
                "reason": "Primary report generation failed",
                "timestamp": time.time(),
                "user_id": context.user_id,
                "run_id": context.run_id
            }
        }
    
    # All infrastructure methods (WebSocket, monitoring, health status) inherited from BaseAgent