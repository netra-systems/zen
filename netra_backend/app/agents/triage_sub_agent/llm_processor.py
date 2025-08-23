"""Triage LLM Processing Module

Handles all LLM interactions, structured calls, and fallback processing.
Keeps functions under 8 lines and module under 300 lines.
"""

import time
from typing import Any, Dict, Optional

from pydantic import ValidationError

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.llm.observability import (
    generate_llm_correlation_id,
    log_agent_input,
    log_agent_output,
    start_llm_heartbeat,
    stop_llm_heartbeat,
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TriageLLMProcessor:
    """Handles LLM processing operations for triage."""
    
    def __init__(self, agent):
        """Initialize with reference to main agent."""
        self.agent = agent
        self.logger = logger
    
    async def execute_triage_with_llm(
        self, state: DeepAgentState, run_id: str, stream_updates: bool
    ) -> dict:
        """Main triage execution with LLM processing."""
        start_time = time.time()
        await self._send_processing_status_update(run_id, stream_updates)
        triage_result = await self._get_or_generate_triage_result(state, run_id, start_time)
        return self._complete_triage_execution(triage_result, state.user_request, run_id)
    
    def _complete_triage_execution(self, triage_result: dict, user_request: str, run_id: str) -> dict:
        """Complete triage execution with finalization."""
        result = self._finalize_triage_result(triage_result, user_request, run_id)
        self._log_agent_completion(run_id)
        return result
    
    async def _send_processing_status_update(self, run_id: str, stream_updates: bool) -> None:
        """Send processing status update via WebSocket."""
        if stream_updates:
            await self.agent._send_update(run_id, {
                "status": "processing",
                "message": "Analyzing user request with enhanced categorization..."
            })
    
    async def _get_or_generate_triage_result(
        self, state: DeepAgentState, run_id: str, start_time: float
    ) -> dict:
        """Get cached result or generate new triage result."""
        request_hash = self.agent.triage_core.generate_request_hash(state.user_request)
        cached_result = await self.agent.triage_core.get_cached_result(request_hash)
        
        if cached_result:
            return self._prepare_cached_result(cached_result, start_time)
        return await self._generate_new_triage_result(state, run_id, start_time, request_hash)
    
    async def _generate_new_triage_result(
        self, state: DeepAgentState, run_id: str, start_time: float, request_hash: str
    ) -> dict:
        """Generate new triage result and cache it."""
        triage_result = await self._process_with_enhanced_llm(state, run_id, start_time)
        await self.agent.triage_core.cache_result(request_hash, triage_result)
        return triage_result
    
    def _finalize_triage_result(self, triage_result: dict, user_request: str, run_id: str) -> dict:
        """Enrich and finalize triage result."""
        enriched_result = self.agent.result_processor.enrich_triage_result(triage_result, user_request)
        self._log_performance_metrics(run_id, enriched_result)
        return enriched_result
    
    def _log_agent_completion(self, run_id: str, status: str = "completed") -> None:
        """Log agent communication completion."""
        from netra_backend.app.llm.observability import log_agent_communication
        log_agent_communication("TriageSubAgent", "Supervisor", run_id, "execute_response")
    
    def _prepare_cached_result(self, cached_result: dict, start_time: float) -> dict:
        """Prepare cached result with updated metadata."""
        triage_result = cached_result.copy()
        self._ensure_metadata_exists(triage_result)
        cache_metadata = self._build_cache_metadata(start_time)
        triage_result["metadata"].update(cache_metadata)
        return triage_result
    
    async def _process_with_enhanced_llm(
        self, state: DeepAgentState, run_id: str, start_time: float
    ) -> dict:
        """Process with LLM using enhanced error handling."""
        enhanced_prompt = self.agent.prompt_builder.build_enhanced_prompt(state.user_request)
        llm_operation = self._create_llm_operation(enhanced_prompt, run_id)
        result = await self._execute_llm_with_fallback_protection(llm_operation)
        return self._finalize_llm_result(result, start_time)
    
    def _finalize_llm_result(self, result: Any, start_time: float) -> dict:
        """Finalize LLM result with metadata."""
        triage_result = self._convert_result_to_dict(result)
        return self._add_metadata(triage_result, start_time, 0)
    
    def _create_llm_operation(self, enhanced_prompt: str, run_id: str):
        """Create LLM operation function."""
        async def _llm_operation():
            return await self._try_structured_then_fallback_llm(enhanced_prompt, run_id)
        return _llm_operation
    
    async def _execute_llm_with_fallback_protection(self, _llm_operation) -> Any:
        """Execute LLM operation with fallback protection."""
        from netra_backend.app.agents.triage_sub_agent.models import TriageResult
        return await self.agent.llm_fallback_handler.execute_structured_with_fallback(
            _llm_operation, TriageResult, "triage_llm_call", "triage"
        )
    
    def _convert_result_to_dict(self, result: Any) -> dict:
        """Convert result to dictionary format."""
        from netra_backend.app.agents.triage_sub_agent.models import TriageResult
        if isinstance(result, TriageResult):
            return result.model_dump()
        else:
            return result
    
    async def _try_structured_then_fallback_llm(self, enhanced_prompt: str, run_id: str) -> dict:
        """Try structured LLM first with retry for ValidationError, then fallback to regular LLM."""
        correlation_id = self._init_llm_correlation()
        return await self._execute_llm_with_heartbeat_protection(
            enhanced_prompt, run_id, correlation_id
        )
    
    def _init_llm_correlation(self) -> str:
        """Initialize LLM correlation and heartbeat."""
        correlation_id = generate_llm_correlation_id()
        start_llm_heartbeat(correlation_id, "TriageSubAgent")
        return correlation_id
    
    async def _execute_llm_with_heartbeat_protection(
        self, enhanced_prompt: str, run_id: str, correlation_id: str
    ) -> dict:
        """Execute LLM with heartbeat protection and error handling."""
        try:
            return await self._execute_structured_llm_with_retries(enhanced_prompt, correlation_id)
        except Exception as e:
            return await self._handle_llm_execution_error(enhanced_prompt, run_id, correlation_id)
        finally:
            stop_llm_heartbeat(correlation_id)
    
    async def _execute_structured_llm_with_retries(self, enhanced_prompt: str, correlation_id: str) -> dict:
        """Execute structured LLM with retry mechanism."""
        self._log_llm_input(enhanced_prompt, correlation_id)
        max_retries = 2
        return await self._retry_structured_llm_attempts(enhanced_prompt, correlation_id, max_retries)
    
    def _log_llm_input(self, enhanced_prompt: str, correlation_id: str) -> None:
        """Log LLM input for tracking."""
        log_agent_input("TriageSubAgent", "LLM", len(enhanced_prompt), correlation_id)
    
    async def _retry_structured_llm_attempts(
        self, enhanced_prompt: str, correlation_id: str, max_retries: int
    ) -> dict:
        """Retry structured LLM attempts until success."""
        for attempt in range(max_retries):
            result = await self._try_structured_llm_attempt(enhanced_prompt, correlation_id, attempt, max_retries)
            if result:
                return result
    
    async def _try_structured_llm_attempt(self, enhanced_prompt: str, correlation_id: str, 
                                        attempt: int, max_retries: int):
        """Try a single structured LLM attempt."""
        try:
            return await self._attempt_structured_llm_call(enhanced_prompt, correlation_id)
        except ValidationError as ve:
            return self._handle_validation_error_in_attempt(attempt, max_retries, ve)
    
    def _handle_validation_error_in_attempt(
        self, attempt: int, max_retries: int, ve: ValidationError
    ):
        """Handle validation error during LLM attempt."""
        if not self._should_retry_validation_error(attempt, max_retries, ve):
            raise ve
        return None
    
    async def _attempt_structured_llm_call(self, enhanced_prompt: str, correlation_id: str) -> dict:
        """Attempt a single structured LLM call."""
        from netra_backend.app.agents.triage_sub_agent.models import TriageResult
        validated_result = await self._call_structured_llm(enhanced_prompt)
        self._log_llm_success(validated_result, correlation_id)
        return validated_result.model_dump()
    
    async def _call_structured_llm(self, enhanced_prompt: str):
        """Call structured LLM with triage schema."""
        from netra_backend.app.agents.triage_sub_agent.models import TriageResult
        return await self.agent.llm_manager.ask_structured_llm(
            enhanced_prompt, llm_config_name='triage', schema=TriageResult, use_cache=False
        )
    
    def _log_llm_success(self, validated_result, correlation_id: str) -> None:
        """Log successful LLM output."""
        log_agent_output("LLM", "TriageSubAgent", 
                       len(str(validated_result)), "success", correlation_id)
    
    def _should_retry_validation_error(self, attempt: int, max_retries: int, ve: ValidationError) -> bool:
        """Determine if validation error should be retried."""
        if attempt < max_retries - 1:
            logger.warning(f"ValidationError on attempt {attempt + 1}, retrying: {ve}")
            return True
        else:
            logger.error(f"ValidationError after {max_retries} attempts: {ve}")
            return False
    
    async def _handle_llm_execution_error(
        self, enhanced_prompt: str, run_id: str, correlation_id: str
    ) -> dict:
        """Handle LLM execution error and fallback."""
        log_agent_output("LLM", "TriageSubAgent", 0, "error", correlation_id)
        return await self._fallback_llm_processing(enhanced_prompt, run_id)
    
    async def _fallback_llm_processing(self, enhanced_prompt: str, run_id: str) -> dict:
        """Enhanced fallback LLM processing with better error handling."""
        try:
            llm_response_str = await self._get_llm_response_with_json_instruction(enhanced_prompt)
            extracted_json = self.agent.triage_core.extract_and_validate_json(llm_response_str)
            return self._process_extracted_json(extracted_json)
        except Exception as e:
            return self._handle_fallback_error(run_id, e)
    
    def _handle_fallback_error(self, run_id: str, error: Exception) -> dict:
        """Handle fallback processing error."""
        logger.error(f"LLM fallback processing failed for {run_id}: {error}")
        return self._create_basic_triage_fallback()
    
    async def _get_llm_response_with_json_instruction(self, enhanced_prompt: str) -> str:
        """Get LLM response with JSON formatting instruction."""
        correlation_id = generate_llm_correlation_id()
        start_llm_heartbeat(correlation_id, "TriageSubAgent-Fallback")
        try:
            return await self._execute_llm_call_with_json_instruction(enhanced_prompt, correlation_id)
        finally:
            stop_llm_heartbeat(correlation_id)
    
    async def _execute_llm_call_with_json_instruction(self, enhanced_prompt: str, correlation_id: str) -> str:
        """Execute LLM call with JSON formatting instruction."""
        prompt = enhanced_prompt + "\n\nIMPORTANT: Return a properly formatted JSON object."
        log_agent_input("TriageSubAgent-Fallback", "LLM", len(prompt), correlation_id)
        response = await self.agent.llm_manager.ask_llm(prompt, llm_config_name='triage')
        log_agent_output("LLM", "TriageSubAgent-Fallback", len(response), "success", correlation_id)
        return response
    
    def _process_extracted_json(self, extracted_json: Optional[dict]) -> dict:
        """Process extracted JSON with validation attempt."""
        if extracted_json:
            return self._validate_or_return_raw(extracted_json)
        return self._create_basic_triage_fallback()
    
    def _validate_or_return_raw(self, extracted_json: dict) -> dict:
        """Validate JSON or return raw data."""
        try:
            from netra_backend.app.agents.triage_sub_agent.models import TriageResult
            # Ensure metadata exists and has required fields
            if "metadata" not in extracted_json or extracted_json["metadata"] is None:
                extracted_json["metadata"] = self._create_fallback_metadata()
            elif "triage_duration_ms" not in extracted_json["metadata"]:
                extracted_json["metadata"]["triage_duration_ms"] = 0
                
            validated_result = TriageResult(**extracted_json)
            return validated_result.model_dump()
        except ValidationError:
            # Ensure raw JSON has proper metadata structure for later use
            if "metadata" not in extracted_json or extracted_json["metadata"] is None:
                extracted_json["metadata"] = self._create_fallback_metadata()
            elif "triage_duration_ms" not in extracted_json["metadata"]:
                extracted_json["metadata"]["triage_duration_ms"] = 0
            return extracted_json
    
    def _create_basic_triage_fallback(self) -> dict:
        """Create basic triage fallback response."""
        base_result = self._create_basic_fallback_structure()
        base_result["metadata"] = self._create_fallback_metadata()
        return base_result
    
    def _create_basic_fallback_structure(self) -> dict:
        """Create basic fallback structure."""
        return {
            "category": "General Inquiry", "confidence_score": 0.3, "priority": "medium",
            "extracted_entities": {}, "tool_recommendations": []
        }
    
    def _create_fallback_metadata(self) -> dict:
        """Create fallback metadata."""
        return {
            "triage_duration_ms": 0,
            "fallback_used": True,
            "fallback_type": "basic_triage",
            "cache_hit": False,
            "retry_count": 0
        }
    
    def _add_metadata(self, triage_result: dict, start_time: float, retry_count: int) -> dict:
        """Add metadata to triage result."""
        self._ensure_metadata_section(triage_result)
        metadata_updates = self._build_metadata_updates(start_time, retry_count)
        triage_result["metadata"].update(metadata_updates)
        return triage_result
    
    def _ensure_metadata_section(self, triage_result: dict) -> None:
        """Ensure metadata section exists in triage result."""
        if not triage_result.get("metadata"):
            triage_result["metadata"] = {}
    
    def _build_metadata_updates(self, start_time: float, retry_count: int) -> dict:
        """Build metadata updates dictionary."""
        return {
            "triage_duration_ms": int((time.time() - start_time) * 1000),
            "cache_hit": False,
            "retry_count": retry_count,
            "fallback_used": retry_count >= self.agent.triage_core.max_retries
        }
    
    def _log_performance_metrics(self, run_id: str, triage_result: dict) -> None:
        """Log performance metrics."""
        metrics = self._extract_performance_metrics(triage_result)
        log_message = self._format_performance_log_message(run_id, metrics)
        self.logger.info(log_message)
    
    def _extract_performance_metrics(self, triage_result: dict) -> dict:
        """Extract performance metrics from triage result."""
        metadata = triage_result.get('metadata', {})
        return {
            'category': triage_result.get('category'), 'confidence': triage_result.get('confidence_score', 0),
            'duration_ms': metadata.get('triage_duration_ms'), 'cache_hit': metadata.get('cache_hit')
        }
    
    def _format_performance_log_message(self, run_id: str, metrics: dict) -> str:
        """Format performance log message."""
        return (
            f"Triage completed for run_id {run_id}: "
            f"category={metrics['category']}, confidence={metrics['confidence']}, "
            f"duration={metrics['duration_ms']}ms, cache_hit={metrics['cache_hit']}"
        )
    
    def _ensure_metadata_exists(self, triage_result: dict) -> None:
        """Ensure metadata section exists in triage result."""
        if "metadata" not in triage_result:
            triage_result["metadata"] = {}
    
    def _build_cache_metadata(self, start_time: float) -> dict:
        """Build cache metadata dictionary."""
        return {
            "cache_hit": True,
            "triage_duration_ms": int((time.time() - start_time) * 1000),
            "fallback_used": False
        }