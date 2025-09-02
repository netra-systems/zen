"""Clean TriageSubAgent using BaseAgent infrastructure (<200 lines).

Simplified implementation using BaseAgent's SSOT infrastructure:
- Inherits reliability management, execution patterns, WebSocket events
- Contains ONLY triage-specific business logic
- Clean single inheritance pattern
- No infrastructure duplication

Business Value: First contact for ALL users - CRITICAL revenue impact.
BVJ: ALL segments | Customer Experience | +25% reduction in triage failures
"""

import time
from typing import Any, Dict, Optional

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.input_validation import validate_agent_input
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.triage_sub_agent.core import TriageCore
from netra_backend.app.agents.triage_sub_agent.models import TriageResult
from netra_backend.app.agents.triage_sub_agent.processing import TriageProcessor
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.registry import DeepAgentState

logger = central_logger.get_logger(__name__)


class TriageSubAgent(BaseAgent):
    """Clean triage agent using BaseAgent infrastructure.
    
    Contains ONLY triage-specific business logic - all infrastructure 
    (reliability, execution, WebSocket events) inherited from BaseAgent.
    """
    
    def __init__(self):
        # Initialize BaseAgent with full infrastructure
        super().__init__(
            name="TriageSubAgent", 
            description="Enhanced triage agent using BaseAgent infrastructure",
            enable_reliability=True,      # Get circuit breaker + retry
            enable_execution_engine=True, # Get modern execution patterns
            enable_caching=True,
        )   
        self.triage_core = TriageCore(self.redis_manager)
        self.processor = TriageProcessor(self.triage_core, self.llm_manager)

    # Implement BaseAgent's abstract methods for triage-specific logic
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions for triage."""
        if not context.state.user_request:
            self.logger.warning(f"No user request provided for triage in run_id: {context.run_id}")
            return False
        validation = self.triage_core.validator.validate_request(context.state.user_request)
        if not validation.is_valid:
            self._set_validation_error_result(context.state, context.run_id, validation)
            return False
        return True
        
    def _set_validation_error_result(self, state: DeepAgentState, run_id: str, validation) -> None:
        """Set validation error result."""
        self.logger.error(f"Invalid request for run_id {run_id}: {validation.validation_errors}")
        state.triage_result = TriageResult(category="Validation Error", confidence_score=0.0, validation_status=validation)
        
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute core triage logic with modern patterns and WebSocket events."""
        start_time = time.time()
        
        # Emit thinking event (agent_started is handled by orchestrator)
        await self.emit_thinking("Starting triage analysis for user request")
        
        # Emit thinking event
        await self.emit_thinking("Analyzing user request and determining category...")
        
        await self._send_processing_update(context.run_id, context.stream_updates)
        
        # Emit progress during triage computation
        await self.emit_progress("Extracting entities and determining intent...")
        triage_result = await self._get_or_compute_triage_result(context.state, context.run_id, start_time)
        
        await self.emit_progress("Finalizing triage results and recommendations...")
        result = await self._finalize_triage_result(context.state, context.run_id, context.stream_updates, triage_result)
        
        # Emit completion event using mixin methods
        await self.emit_progress("Triage analysis completed successfully", is_complete=True)
        
        return result
        
    async def _send_processing_update(self, run_id: str, stream_updates: bool) -> None:
        """Send processing status update."""
        if stream_updates:
            await self._send_update(run_id, {"status": "processing", "message": "Analyzing user request with enhanced categorization..."})
            
    async def _get_or_compute_triage_result(self, state: DeepAgentState, run_id: str, start_time: float):
        """Get cached result or compute new one."""
        request_hash = self.triage_core.generate_request_hash(state.user_request)
        cached_result = await self.triage_core.get_cached_result(request_hash)
        if cached_result:
            cached_result["metadata"]["cache_hit"] = True
            cached_result["metadata"]["triage_duration_ms"] = int((time.time() - start_time) * 1000)
            return cached_result
        triage_result = await self.processor.process_with_llm(state, run_id, start_time)
        await self.triage_core.cache_result(request_hash, triage_result)
        return triage_result
        
    async def _finalize_triage_result(self, state: DeepAgentState, run_id: str, stream_updates: bool, triage_result):
        """Finalize and send triage result."""
        triage_result = self.processor.enrich_triage_result(triage_result, state.user_request)
        state.triage_result = triage_result
        self.processor.log_performance_metrics(run_id, triage_result)
        if stream_updates:
            await self.websocket_handler.send_final_update(run_id, triage_result)
        return triage_result

    # Legacy execute method for backward compatibility
    @validate_agent_input('TriageSubAgent')
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute the enhanced triage logic - uses BaseAgent's reliability infrastructure"""
        await self.execute_with_reliability(
            lambda: self._execute_triage_main(state, run_id, stream_updates),
            "execute_triage",
            fallback=lambda: self._execute_triage_fallback(state, run_id, stream_updates)
        )
    
    async def _execute_triage_main(self, state: DeepAgentState, run_id: str, stream_updates: bool):
        """Main triage execution logic - delegates to execute_core_logic."""
        from netra_backend.app.agents.utils import extract_thread_id
        
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

    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if we have a user request to triage"""
        return bool(state.user_request)

    async def cleanup(self, state: DeepAgentState, run_id: str) -> None:
        """Cleanup after execution - triage-specific cleanup only"""
        if state.triage_result and isinstance(state.triage_result, dict):
            metadata = state.triage_result.get("metadata", {})
            if metadata:
                self.logger.debug(f"Triage metrics for run_id {run_id}: {metadata}")

    # Triage-specific helper methods (business logic only)
    def _validate_request(self, request: str): 
        return self.triage_core.validator.validate_request(request)
    
    def _extract_entities_from_request(self, request: str): 
        return self.triage_core.entity_extractor.extract_entities(request)
    
    def _determine_intent(self, request: str): 
        return self.triage_core.intent_detector.detect_intent(request)
    
    def _recommend_tools(self, category: str, entities): 
        return self.triage_core.tool_recommender.recommend_tools(category, entities)
    
    def _fallback_categorization(self, request: str): 
        return self.triage_core.create_fallback_result(request)
    
    def _extract_and_validate_json(self, response: str): 
        return self.triage_core.extract_and_validate_json(response)
    
    def _generate_request_hash(self, request: str): 
        return self.triage_core.generate_request_hash(request)
    
    # All infrastructure methods (WebSocket, monitoring, health status) inherited from BaseAgent