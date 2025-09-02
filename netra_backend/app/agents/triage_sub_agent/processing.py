"""Triage Processing Module aligned with UserExecutionContext pattern.

Refactored to eliminate SSOT violations by delegating to BaseAgent's built-in
monitoring, error handling, and WebSocket capabilities.
"""

import asyncio
import time
from typing import TYPE_CHECKING, Any, Dict, Optional

from pydantic import ValidationError

if TYPE_CHECKING:
    from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent
    from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext

from netra_backend.app.agents.config import agent_config
from netra_backend.app.agents.prompts import triage_prompt_template
from netra_backend.app.agents.triage_sub_agent.models import (
    ExtractedEntities, TriageResult
)
from netra_backend.app.agents.triage_sub_agent.processing_monitoring import (
    TriageProcessingErrorHelper,
    TriageProcessingMonitor,
)
from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.serialization.unified_json_handler import safe_json_loads

logger = central_logger.get_logger(__name__)


class TriageProcessor:
    """Triage processor aligned with SSOT principles.
    
    Delegates monitoring, error handling, and WebSocket to the parent agent.
    """
    
    def __init__(self, triage_core, llm_manager, agent: 'TriageSubAgent' = None):
        self.triage_core = triage_core
        self.llm_manager = llm_manager
        self.agent = agent  # Store reference to parent agent for SSOT access
        self.logger = logger
        self._init_components()
    
    def _init_components(self) -> None:
        """Initialize components, using agent's SSOT implementations."""
        # Use agent's monitor if available, following SSOT principle
        self.monitor = getattr(self.agent, '_execution_monitor', None) if self.agent else None
        # Use agent's error handler through unified infrastructure
        self.error_handler = getattr(self.agent, 'agent_error_handler', None) if self.agent else None
        # Keep processing-specific helpers
        self.processing_monitor = TriageProcessingMonitor(self.monitor) if self.monitor else None
        self.error_helper = TriageProcessingErrorHelper()
    
    async def process_with_llm(self, state, run_id, start_time, user_context: 'UserExecutionContext'):
        """Process request with LLM using UserExecutionContext pattern.
        
        Args:
            state: Agent state
            run_id: Execution run ID
            start_time: Processing start time
            user_context: UserExecutionContext for request isolation (REQUIRED)
        """
        if not user_context:
            raise ValueError("UserExecutionContext is required for processing")
        return await self._process_with_user_context(user_context, state, start_time)
    
    async def _process_with_user_context(self, user_context: 'UserExecutionContext', state, start_time: float):
        """Process with UserExecutionContext for proper isolation."""
        # Use agent's monitoring if available (SSOT)
        if self.monitor and hasattr(self.monitor, 'start_execution'):
            # Create lightweight context wrapper for monitor compatibility
            from netra_backend.app.agents.base.interface import ExecutionContext
            monitor_context = ExecutionContext(
                run_id=user_context.run_id,
                agent_name=self.agent.name if self.agent else "TriageProcessor",
                state=state,
                user_id=user_context.user_id,
                thread_id=user_context.thread_id
            )
            self.monitor.start_execution(monitor_context)
        
        try:
            return await self._execute_llm_processing_with_context(user_context, state, start_time)
        except Exception as e:
            return await self._handle_processing_error_with_context(user_context, e, start_time)
        finally:
            self._update_processing_metrics()
    
    
    async def _execute_llm_processing_with_context(self, user_context: 'UserExecutionContext', state, start_time: float):
        """Execute LLM processing with UserExecutionContext."""
        retry_count = 0
        triage_result = await self._retry_llm_processing(state, user_context.run_id, retry_count)
        return self._finalize_processing_result_with_context(triage_result, user_context, state, start_time, retry_count)
    
    
    def _finalize_processing_result_with_context(self, triage_result, user_context: 'UserExecutionContext',
                                                state, start_time: float, retry_count: int):
        """Finalize processing result using UserExecutionContext."""
        if not triage_result:
            triage_result = self._create_fallback_triage_result(state, user_context.run_id)
        return self._add_metadata(triage_result, start_time, retry_count)
    
    
    def _build_enhanced_prompt(self, user_request):
        """Build enhanced prompt for LLM processing."""
        base_prompt = triage_prompt_template.format(user_request=user_request)
        # Delegate to triage_core's prompt builder if available
        if hasattr(self.triage_core, 'prompt_builder'):
            analysis_instructions = self.triage_core.prompt_builder._get_analysis_instructions()
            category_options = self.triage_core.prompt_builder._get_category_options()
        else:
            # Minimal fallback
            analysis_instructions = "Analyze the request carefully."
            category_options = "Choose the most appropriate category."
        return f"{base_prompt}\n\n{analysis_instructions}\n\n{category_options}"
    
    async def _handle_processing_error_with_context(self, user_context: 'UserExecutionContext',
                                                  error: Exception, start_time: float):
        """Handle processing error using UserExecutionContext and agent's error handler."""
        # Use agent's error handling if available (SSOT)
        if self.agent and hasattr(self.agent, '_handle_error'):
            await self.agent._handle_error(error, user_context)
        
        # Log error with helper
        self.error_helper.log_processing_error(error, user_context.run_id)
        
        # Create fallback result
        # Note: We need state from somewhere - might need to pass it
        return self.error_helper.create_error_fallback_result({}, start_time)
    
    
    async def _fallback_llm_processing(self, enhanced_prompt, run_id, struct_error):
        """Fallback to regular LLM with JSON extraction and monitoring."""
        self._log_fallback_warning(struct_error)
        self.processing_monitor.record_fallback_metrics()
        llm_response = await self._get_fallback_llm_response(enhanced_prompt)
        extracted_json = self.triage_core.extract_and_validate_json(llm_response)
        return self._process_fallback_result(extracted_json, run_id)
    
    def _fix_string_parameters(self, data):
        """Fix string parameters in tool recommendations - convert JSON strings to dicts"""
        if not isinstance(data, dict):
            return data
        
        self._fix_tool_recommendation_parameters(data)
        return data
    
    def _fix_tool_recommendation_parameters(self, data):
        """Fix parameters field in tool recommendations."""
        if not self._has_tool_recommendations(data):
            return
        
        for rec in data["tool_recommendations"]:
            self._fix_recommendation_parameters(rec)
    
    def _has_tool_recommendations(self, data):
        """Check if data has tool recommendations."""
        return ("tool_recommendations" in data and 
                isinstance(data["tool_recommendations"], list))
    
    def _fix_recommendation_parameters(self, rec):
        """Fix parameters field in a single recommendation."""
        if not (isinstance(rec, dict) and "parameters" in rec):
            return
        
        if isinstance(rec["parameters"], str):
            rec["parameters"] = self._parse_json_parameters(rec["parameters"])
    
    def _parse_json_parameters(self, parameters_str):
        """Parse JSON string parameters with fallback."""
        try:
            return safe_json_loads(parameters_str, {})
        except (TypeError, ValueError):
            return {}
    
    def enrich_triage_result(self, triage_result, user_request):
        """Enrich triage result with additional analysis"""
        self._ensure_entities_extracted(triage_result, user_request)
        self._ensure_intent_detected(triage_result, user_request)
        self._handle_admin_mode_detection(triage_result, user_request)
        self._ensure_tool_recommendations(triage_result)
        return triage_result
    
    def _ensure_entities_extracted(self, triage_result, user_request):
        """Ensure entities are extracted from request."""
        if not triage_result.get("extracted_entities"):
            entities = self.triage_core.entity_extractor.extract_entities(user_request)
            triage_result["extracted_entities"] = entities.model_dump()
    
    def _ensure_intent_detected(self, triage_result, user_request):
        """Ensure user intent is detected."""
        if not triage_result.get("user_intent"):
            intent = self.triage_core.intent_detector.detect_intent(user_request)
            triage_result["user_intent"] = intent.model_dump()
    
    def _handle_admin_mode_detection(self, triage_result, user_request):
        """Handle admin mode detection and category adjustment."""
        is_admin = self.triage_core.intent_detector.detect_admin_mode(user_request)
        triage_result["is_admin_mode"] = is_admin
        
        if is_admin:
            triage_result = self._adjust_admin_category(triage_result, user_request)
    
    def _ensure_tool_recommendations(self, triage_result):
        """Ensure tool recommendations are present."""
        if not triage_result.get("tool_recommendations"):
            tools = self.triage_core.tool_recommender.recommend_tools(
                triage_result.get("category", "General Inquiry"),
                ExtractedEntities(**triage_result.get("extracted_entities", {}))
            )
            triage_result["tool_recommendations"] = [t.model_dump() for t in tools]
    
    def _adjust_admin_category(self, triage_result, user_request):
        """Adjust category for admin mode requests"""
        if triage_result.get("category") not in ["Synthetic Data Generation", "Corpus Management"]:
            if "synthetic" in user_request.lower() or "generate data" in user_request.lower():
                triage_result["category"] = "Synthetic Data Generation"
            elif "corpus" in user_request.lower():
                triage_result["category"] = "Corpus Management"
        return triage_result
    
    def _add_metadata(self, triage_result, start_time, retry_count):
        """Add metadata to triage result.
        
        Simplified to avoid duplication with BaseAgent's metadata handling.
        """
        if not triage_result.get("metadata"):
            triage_result["metadata"] = {}
        
        # Add minimal processing-specific metadata
        triage_result["metadata"].update({
            "triage_duration_ms": (time.time() - start_time) * 1000,
            "retry_count": retry_count,
            "processor": "TriageProcessor"
        })
        
        # Record success if monitor available
        if self.processing_monitor:
            self.processing_monitor.record_success_metrics(triage_result)
        
        return triage_result
    
    def log_performance_metrics(self, run_id, triage_result):
        """Log performance metrics.
        
        Delegates to agent's monitoring if available (SSOT).
        """
        if self.processing_monitor:
            metrics = self.processing_monitor.extract_enhanced_performance_metrics(triage_result)
            log_message = self.processing_monitor.format_enhanced_performance_log_message(run_id, metrics)
            self.logger.info(log_message)
            self.processing_monitor.record_performance_metrics(metrics)
        elif self.agent and hasattr(self.agent, 'timing_collector'):
            # Use agent's timing collector (SSOT)
            metadata = triage_result.get('metadata', {})
            if 'triage_duration_ms' in metadata:
                self.agent.timing_collector.record_operation(
                    operation="triage_processing",
                    duration_ms=metadata['triage_duration_ms']
                )
    
    def _update_processing_metrics(self) -> None:
        """Update processing metrics.
        
        Delegates to agent's monitor if available (SSOT).
        """
        # Metrics are automatically tracked by the agent's monitor
        pass
    
    async def _retry_llm_processing(self, state, run_id, retry_count):
        """Retry LLM processing with structured output.
        
        Delegates to triage_core's LLM processor or provides minimal fallback.
        """
        # Extract user request from state
        user_request = getattr(state, 'user_request', '') if hasattr(state, 'user_request') else str(state)
        
        # Build enhanced prompt
        enhanced_prompt = self._build_enhanced_prompt(user_request)
        
        # Try to use triage_core's LLM processor if available
        if hasattr(self.triage_core, 'llm_processor'):
            try:
                result = await self.triage_core.llm_processor.process_with_structured_llm(
                    user_request=user_request,
                    run_id=run_id
                )
                return result
            except Exception as e:
                self.logger.warning(f"LLM processor failed: {e}, using fallback")
        
        # Fallback: basic LLM call
        if self.llm_manager:
            try:
                from netra_backend.app.agents.triage_sub_agent.models import TriageResult
                response = await self.llm_manager.generate_response(
                    prompt=enhanced_prompt,
                    correlation_id=run_id
                )
                # Try to parse as TriageResult
                if isinstance(response, dict):
                    return response
                # Extract JSON from string response
                if hasattr(self.triage_core, 'extract_and_validate_json'):
                    return self.triage_core.extract_and_validate_json(response)
            except Exception as e:
                self.logger.error(f"Fallback LLM processing failed: {e}")
        
        return None
    
    def _create_fallback_triage_result(self, state, run_id):
        """Create a fallback triage result when processing fails."""
        # Try to use triage_core's result processor if available
        if hasattr(self.triage_core, 'result_processor'):
            return self.triage_core.result_processor._create_fallback_triage_result()
        
        # Minimal fallback
        return {
            "category": "General Inquiry",
            "confidence_score": 0.5,
            "user_intent": {"intent_type": "unknown"},
            "extracted_entities": {},
            "tool_recommendations": [],
            "is_admin_mode": False,
            "metadata": {
                "fallback_used": True,
                "run_id": run_id
            }
        }
    
    def _process_fallback_result(self, extracted_json, run_id):
        """Process fallback result with monitoring."""
        if extracted_json:
            return self._process_extracted_fallback_json(extracted_json, run_id)
        return None
    
    def _process_extracted_fallback_json(self, extracted_json, run_id):
        """Process extracted JSON from fallback path."""
        # Add minimal metadata
        if isinstance(extracted_json, dict):
            if "metadata" not in extracted_json:
                extracted_json["metadata"] = {}
            extracted_json["metadata"]["fallback_json_extraction"] = True
            extracted_json["metadata"]["run_id"] = run_id
        return extracted_json
    
    def _log_fallback_warning(self, struct_error):
        """Log warning when falling back to regular LLM."""
        self.logger.warning(f"Structured LLM failed, using fallback: {struct_error}")
    
    async def _get_fallback_llm_response(self, enhanced_prompt):
        """Get fallback LLM response when structured output fails."""
        if self.llm_manager:
            return await self.llm_manager.generate_response(
                prompt=enhanced_prompt,
                correlation_id=getattr(self, 'correlation_id', 'fallback')
            )
        return None


# WebSocketHandler class removed - use agent's built-in WebSocket methods:
# - agent.emit_agent_completed()
# - agent.emit_progress()
# - agent.emit_thinking()