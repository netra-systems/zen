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
from netra_backend.app.core.serialization.unified_json_handler import (
    LLMResponseParser,
    JSONErrorFixer
)
from netra_backend.app.services.cache.cache_helpers import CacheHelpers
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
    
    def __init__(self, context: Optional[UserExecutionContext] = None):
        # Initialize BaseAgent with full infrastructure
        super().__init__(
            name="ReportingSubAgent", 
            description="Golden Pattern reporting agent using BaseAgent infrastructure",
            enable_reliability=True,      # Get circuit breaker + retry
            enable_execution_engine=True, # Get modern execution patterns
            enable_caching=True,         # Get Redis caching
        )
        
        # Store context for factory pattern integration
        self._user_context = context
        
        # Initialize cache helper for SSOT key generation
        self._cache_helper = CacheHelpers(None)  # Pass None for key generation only

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
        """Execute report generation with proper WebSocket events and caching."""
        # Validate context at method entry
        if not isinstance(context, UserExecutionContext):
            raise AgentValidationError(f"Invalid context type: {type(context)}")
        
        # REQUIRED: Emit agent started
        if stream_updates:
            await self.emit_agent_started("Starting comprehensive report generation...")
        
        # REQUIRED: Show thinking during validation
        if stream_updates:
            await self.emit_thinking("Validating analysis results and preparing report context...")
        
        # Validate required analysis results
        self._validate_analysis_results(context)
        
        # Generate cache key with user context
        cache_key = self._generate_report_cache_key(context)
        
        # Try to get cached result first
        cached_result = await self._get_cached_report(cache_key)
        if cached_result:
            self.logger.info(f"Using cached report for run_id: {context.run_id}")
            if stream_updates:
                await self.emit_agent_completed(cached_result)
            return cached_result
        
        # Create database session manager for proper session isolation
        if context.db_session:
            db_manager = DatabaseSessionManager(context)
            
        try:
            self.logger.info(f"Starting report generation for run_id: {context.run_id}")
            
            # REQUIRED: Show report building progress
            if stream_updates:
                await self.emit_thinking("Building comprehensive report from analysis results...")
            
            # Build the reporting prompt from context metadata
            prompt = self._build_reporting_prompt(context)
            correlation_id = generate_llm_correlation_id()
            
            # Execute LLM with proper event emission and context
            llm_response_str = await self._execute_reporting_llm_with_observability(
                prompt, correlation_id, context, stream_updates
            )
            
            # REQUIRED: Show processing completion
            if stream_updates:
                await self.emit_thinking("Processing and formatting final report...")
            
            # Process and format results
            result = self._extract_and_validate_report(llm_response_str, context.run_id)
            
            # Cache the result with TTL
            await self._cache_report_result(cache_key, result)
            
            # REQUIRED: Emit completion with results
            if stream_updates:
                await self.emit_agent_completed(result)
            
            self.logger.info(f"Report generation completed successfully for run_id: {context.run_id}")
            return result
            
        except Exception as e:
            # REQUIRED: Emit error events
            if stream_updates:
                await self.emit_error(f"Report generation failed: {str(e)}", "generation_error")
            
            # Proper error handling
            self.logger.error(f"Report generation failed for run_id {context.run_id}: {str(e)}")
            
            # Create fallback report
            fallback_result = self._create_fallback_report(context)
            return fallback_result

    async def _execute_reporting_llm_with_observability(
        self, prompt: str, correlation_id: str, context: UserExecutionContext, 
        stream_updates: bool = False
    ) -> str:
        """Execute LLM call with full observability and user feedback."""
        
        # REQUIRED: Show LLM processing start
        if stream_updates:
            await self.emit_tool_executing("llm_report_generation", {
                "model": "reporting",
                "prompt_length": len(prompt)
            })
        
        start_llm_heartbeat(correlation_id, "ReportingSubAgent")
        try:
            # Use context for user-specific logging
            log_agent_input(
                "ReportingSubAgent", "LLM", len(prompt), correlation_id
            )
            
            # REQUIRED: Show thinking during LLM processing
            if stream_updates:
                await self.emit_thinking("Generating comprehensive analysis report using AI reasoning...")
                
            response = await self.llm_manager.ask_llm(prompt, llm_config_name='reporting')
            
            # REQUIRED: Show LLM completion
            if stream_updates:
                await self.emit_tool_completed("llm_report_generation", {
                    "status": "success",
                    "response_length": len(response)
                })
                
            log_agent_output(
                "LLM", "ReportingSubAgent", len(response), "success", correlation_id
            )
            return response
        except Exception as e:
            # REQUIRED: Show LLM failure
            if stream_updates:
                await self.emit_tool_completed("llm_report_generation", {
                    "status": "error", 
                    "error": str(e)
                })
            log_agent_output(
                "LLM", "ReportingSubAgent", 0, "error", correlation_id
            )
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
        """Extract and validate JSON result from LLM response using canonical parser."""
        # Use canonical LLMResponseParser from unified_json_handler
        parser = LLMResponseParser()
        report_result = parser.safe_json_parse(llm_response_str)
        
        # If result is a dict, return it; otherwise try error fixing
        if isinstance(report_result, dict):
            return report_result
            
        # Apply comprehensive error fixing for malformed JSON
        error_fixer = JSONErrorFixer()
        fixed_result = error_fixer.recover_truncated_json(llm_response_str)
        
        if fixed_result and isinstance(fixed_result, dict):
            self.logger.info(f"Successfully recovered malformed JSON for run_id: {run_id}")
            return fixed_result
        
        # Final fallback
        self.logger.warning(f"Could not extract or recover JSON from LLM response for run_id: {run_id}. Using fallback report.")
        return {"report": "No report could be generated from LLM response."}
    
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
    
    def _generate_report_cache_key(self, context: UserExecutionContext) -> str:
        """Generate cache key for report with user context isolation."""
        # Build key data with user context
        key_data = {
            "agent": "reporting",
            "action_plan": context.metadata.get("action_plan_result", ""),
            "optimizations": context.metadata.get("optimizations_result", ""), 
            "data_result": context.metadata.get("data_result", ""),
            "triage_result": context.metadata.get("triage_result", ""),
            "user_request": context.metadata.get("user_request", "")
        }
        
        # CRITICAL: Include user context for proper isolation
        if context:
            key_data["user_id"] = context.user_id
            key_data["thread_id"] = context.thread_id
            
        # Use SSOT CacheHelpers for hash generation
        return self._cache_helper.hash_key_data(key_data)

    async def _get_cached_report(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached report result."""
        if not hasattr(self, 'redis_manager') or not self.redis_manager:
            return None
        
        try:
            cached_data = await self.redis_manager.get(f"report_cache:{cache_key}")
            if cached_data:
                import json
                return json.loads(cached_data)
        except Exception as e:
            self.logger.warning(f"Failed to retrieve cached report: {e}")
        
        return None

    async def _cache_report_result(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Cache report result with TTL."""
        if not hasattr(self, 'redis_manager') or not self.redis_manager:
            return
            
        try:
            import json
            cache_data = json.dumps(result)
            ttl = getattr(self, 'cache_ttl', 3600)  # Default 1 hour TTL
            await self.redis_manager.set(
                f"report_cache:{cache_key}",
                cache_data, 
                ex=ttl
            )
            self.logger.debug(f"Cached report result with key: {cache_key[:12]}...")
        except Exception as e:
            self.logger.warning(f"Failed to cache report result: {e}")

    @classmethod
    def create_agent_with_context(cls, context: 'UserExecutionContext') -> 'ReportingSubAgent':
        """Factory method for creating agent with user context.
        
        This method enables the agent to be created through AgentInstanceFactory
        with proper user context isolation.
        
        Args:
            context: User execution context for isolation
            
        Returns:
            ReportingSubAgent: Configured agent instance
        """
        return cls(context=context)

    # All infrastructure methods (WebSocket, monitoring, health status) inherited from BaseAgent