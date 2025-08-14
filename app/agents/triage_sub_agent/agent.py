"""Triage Sub Agent

Enhanced triage agent with advanced categorization and caching capabilities.
This module provides a clean interface that uses the modular structure for backward compatibility.
"""

import time
import asyncio
from typing import Optional
from pydantic import ValidationError

from app.llm.llm_manager import LLMManager
from app.agents.base import BaseSubAgent
from app.agents.prompts import triage_prompt_template
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.redis_manager import RedisManager
from app.logging_config import central_logger
from app.core.reliability import (
    get_reliability_wrapper, CircuitBreakerConfig, RetryConfig
)

# Import from modular structure
from app.agents.triage_sub_agent.models import (
    TriageResult,
    TriageMetadata,
    ExtractedEntities
)
from app.agents.triage_sub_agent.core import TriageCore

logger = central_logger.get_logger(__name__)


class TriageSubAgent(BaseSubAgent):
    """Enhanced triage agent with advanced categorization and caching"""
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher, redis_manager: Optional[RedisManager] = None):
        super().__init__(llm_manager, name="TriageSubAgent", description="Enhanced triage agent with advanced categorization and caching.")
        self.tool_dispatcher = tool_dispatcher
        self.triage_core = TriageCore(redis_manager)
        
        # Initialize reliability wrapper
        self.reliability = get_reliability_wrapper(
            "TriageSubAgent",
            CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=30.0,
                name="TriageSubAgent"
            ),
            RetryConfig(
                max_retries=2,
                base_delay=1.0,
                max_delay=10.0
            )
        )

    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if we have a user request to triage"""
        if not state.user_request:
            self.logger.warning(f"No user request provided for triage in run_id: {run_id}")
            return False
        
        # Validate request using triage core
        validation = self.triage_core.validator.validate_request(state.user_request)
        if not validation.is_valid:
            self.logger.error(f"Invalid request for run_id {run_id}: {validation.validation_errors}")
            # Create a proper TriageResult for error case
            error_result = TriageResult(
                category="Validation Error",
                confidence_score=0.0,
                validation_status=validation
            )
            state.triage_result = error_result
            return False
        
        return True

    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute the enhanced triage logic with structured generation"""
        async def _execute_triage():
            start_time = time.time()
            
            # Update status via WebSocket
            if stream_updates:
                await self._send_update(run_id, {
                    "status": "processing",
                    "message": "Analyzing user request with enhanced categorization..."
                })
            
            # Check cache first using triage core
            request_hash = self.triage_core.generate_request_hash(state.user_request)
            cached_result = await self.triage_core.get_cached_result(request_hash)
            
            if cached_result:
                # Use cached result
                triage_result = cached_result
                triage_result["metadata"]["cache_hit"] = True
                triage_result["metadata"]["triage_duration_ms"] = int((time.time() - start_time) * 1000)
            else:
                triage_result = await self._process_with_llm(state, run_id, start_time)
                # Cache the result for future use
                await self.triage_core.cache_result(request_hash, triage_result)
            
            # Enrich result with additional analysis
            triage_result = self._enrich_triage_result(triage_result, state.user_request)
            
            state.triage_result = triage_result
            
            # Log performance metrics
            self._log_performance_metrics(run_id, triage_result)
            
            # Update with results
            if stream_updates:
                await self._send_final_update(run_id, triage_result)
            
            return triage_result
        
        async def _fallback_triage():
            """Fallback triage when main operation fails"""
            logger.warning(f"Using fallback triage for run_id: {run_id}")
            fallback_result = self.triage_core.create_fallback_result(state.user_request)
            triage_result = fallback_result.model_dump()
            triage_result["metadata"] = {
                "fallback_used": True,
                "triage_duration_ms": 100,
                "cache_hit": False
            }
            state.triage_result = triage_result
            
            if stream_updates:
                await self._send_update(run_id, {
                    "status": "completed_with_fallback",
                    "message": "Triage completed with fallback method",
                    "result": triage_result
                })
            
            return triage_result
        
        # Execute with reliability protection
        await self.reliability.execute_safely(
            _execute_triage,
            "execute_triage",
            fallback=_fallback_triage,
            timeout=30.0
        )
    
    async def _process_with_llm(self, state, run_id, start_time):
        """Process request with LLM using structured generation"""
        retry_count = 0
        triage_result = None
        
        while retry_count < self.triage_core.max_retries and not triage_result:
            try:
                enhanced_prompt = self._build_enhanced_prompt(state.user_request)
                
                # Try structured generation first
                try:
                    validated_result = await self.llm_manager.ask_structured_llm(
                        enhanced_prompt,
                        llm_config_name='triage',
                        schema=TriageResult,
                        use_cache=False
                    )
                    triage_result = validated_result.model_dump()
                except Exception as struct_error:
                    triage_result = await self._fallback_llm_processing(
                        enhanced_prompt, run_id, struct_error
                    )
                
            except Exception as e:
                self.logger.warning(f"Triage attempt {retry_count + 1} failed for run_id {run_id}: {e}")
                retry_count += 1
                
                if retry_count < self.triage_core.max_retries:
                    await asyncio.sleep(2 ** retry_count)
        
        # Use fallback if all retries failed
        if not triage_result:
            self.logger.warning(f"Using fallback categorization for run_id: {run_id}")
            fallback = self.triage_core.create_fallback_result(state.user_request)
            triage_result = fallback.model_dump()
        
        # Add metadata
        triage_result = self._add_metadata(triage_result, start_time, retry_count)
        
        return triage_result
    
    def _build_enhanced_prompt(self, user_request):
        """Build enhanced prompt for LLM processing"""
        return f"""
{triage_prompt_template.format(user_request=user_request)}

Consider the following in your analysis:
1. Extract all mentioned models, metrics, and time ranges
2. Determine the urgency and complexity of the request
3. Suggest specific tools that would be helpful
4. Identify any constraints or requirements mentioned

Categorize into one of these main categories:
- Cost Optimization
- Performance Optimization
- Workload Analysis
- Configuration & Settings
- Monitoring & Reporting
- Model Selection
- Supply Catalog Management
- Quality Optimization
"""
    
    async def _fallback_llm_processing(self, enhanced_prompt, run_id, struct_error):
        """Fallback to regular LLM with JSON extraction"""
        self.logger.warning(f"Structured generation failed, falling back to JSON extraction: {struct_error}")
        
        llm_response_str = await self.llm_manager.ask_llm(
            enhanced_prompt + "\n\nIMPORTANT: Return a properly formatted JSON object with all required fields.",
            llm_config_name='triage'
        )
        
        # Extract and validate JSON
        extracted_json = self.triage_core.extract_and_validate_json(llm_response_str)
        
        if extracted_json:
            try:
                validated_result = TriageResult(**extracted_json)
                return validated_result.model_dump()
            except ValidationError as e:
                self.logger.warning(f"Validation error for run_id {run_id}: {e}")
                return extracted_json
        
        return None
    
    def _enrich_triage_result(self, triage_result, user_request):
        """Enrich triage result with additional analysis"""
        # Extract entities and intent if not already done
        if not triage_result.get("extracted_entities"):
            entities = self.triage_core.entity_extractor.extract_entities(user_request)
            triage_result["extracted_entities"] = entities.model_dump()
        
        if not triage_result.get("user_intent"):
            intent = self.triage_core.intent_detector.detect_intent(user_request)
            triage_result["user_intent"] = intent.model_dump()
        
        # Detect admin mode
        is_admin = self.triage_core.intent_detector.detect_admin_mode(user_request)
        triage_result["is_admin_mode"] = is_admin
        
        # Adjust category for admin mode
        if is_admin:
            triage_result = self._adjust_admin_category(triage_result, user_request)
        
        # Add tool recommendations if not present
        if not triage_result.get("tool_recommendations"):
            tools = self.triage_core.tool_recommender.recommend_tools(
                triage_result.get("category", "General Inquiry"),
                ExtractedEntities(**triage_result.get("extracted_entities", {}))
            )
            triage_result["tool_recommendations"] = [t.model_dump() for t in tools]
        
        return triage_result
    
    def _adjust_admin_category(self, triage_result, user_request):
        """Adjust category for admin mode requests"""
        if triage_result.get("category") not in ["Synthetic Data Generation", "Corpus Management"]:
            if "synthetic" in user_request.lower() or "generate data" in user_request.lower():
                triage_result["category"] = "Synthetic Data Generation"
            elif "corpus" in user_request.lower():
                triage_result["category"] = "Corpus Management"
        return triage_result
    
    def _add_metadata(self, triage_result, start_time, retry_count):
        """Add metadata to triage result"""
        if not triage_result.get("metadata"):
            triage_result["metadata"] = {}
        
        triage_result["metadata"].update({
            "triage_duration_ms": int((time.time() - start_time) * 1000),
            "cache_hit": False,
            "retry_count": retry_count,
            "fallback_used": retry_count >= self.triage_core.max_retries
        })
        
        return triage_result
    
    def _log_performance_metrics(self, run_id, triage_result):
        """Log performance metrics"""
        self.logger.info(
            f"Triage completed for run_id {run_id}: "
            f"category={triage_result.get('category')}, "
            f"confidence={triage_result.get('confidence_score', 0)}, "
            f"duration={triage_result['metadata']['triage_duration_ms']}ms, "
            f"cache_hit={triage_result['metadata']['cache_hit']}"
        )
    
    async def _send_final_update(self, run_id, triage_result):
        """Send final update via WebSocket"""
        await self._send_update(run_id, {
            "status": "processed",
            "message": f"Request categorized as: {triage_result.get('category', 'Unknown')} "
                      f"with confidence {triage_result.get('confidence_score', 0):.2f}",
            "result": triage_result
        })

    async def cleanup(self, state: DeepAgentState, run_id: str) -> None:
        """Cleanup after execution"""
        await super().cleanup(state, run_id)
        
        # Log final metrics if available
        if state.triage_result and isinstance(state.triage_result, dict):
            metadata = state.triage_result.get("metadata", {})
            if metadata:
                self.logger.debug(f"Triage metrics for run_id {run_id}: {metadata}")
    
    def get_health_status(self) -> dict:
        """Get agent health status"""
        return self.reliability.get_health_status()
    
    def get_circuit_breaker_status(self) -> dict:
        """Get circuit breaker status"""
        return self.reliability.circuit_breaker.get_status()