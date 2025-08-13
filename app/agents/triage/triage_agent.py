# Refactored Triage Sub Agent - Modular and compliant with 8-line functions
import json
import time
import asyncio
from typing import Optional, Dict, Any
from pydantic import ValidationError

from app.llm.llm_manager import LLMManager
from app.agents.base import BaseSubAgent
from app.agents.prompts import triage_prompt_template
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.agents.utils import extract_json_from_response
from app.redis_manager import RedisManager
from app.logging_config import central_logger

# Import modular components
from app.agents.triage.models import (
    TriageResult, TriageMetadata, Priority, Complexity
)
from app.agents.triage.validators import RequestValidator
from app.agents.triage.extractors import EntityExtractor, IntentDetector
from app.agents.triage.cache_manager import TriageCacheManager
from app.agents.triage.tool_recommender import ToolRecommender

logger = central_logger.get_logger(__name__)

class TriageSubAgent(BaseSubAgent):
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher, 
                 redis_manager: Optional[RedisManager] = None):
        super().__init__(llm_manager, name="TriageSubAgent", 
                        description="Enhanced modular triage agent.")
        self.tool_dispatcher = tool_dispatcher
        self.cache_manager = TriageCacheManager(redis_manager)
        self.max_retries = 3
        self.fallback_categories = self._init_fallback_categories()
    
    def _init_fallback_categories(self) -> Dict[str, str]:
        """Initialize fallback category mappings."""
        return {
            "optimize": "Cost Optimization",
            "performance": "Performance Optimization",
            "analyze": "Workload Analysis",
            "configure": "Configuration & Settings",
            "report": "Monitoring & Reporting",
            "model": "Model Selection",
            "supply": "Supply Catalog Management",
            "quality": "Quality Optimization"
        }
    
    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if we have a valid user request to triage."""
        if not state.user_request:
            logger.warning(f"No user request for run_id: {run_id}")
            return False
        return self._validate_and_set_error(state, run_id)
    
    def _validate_and_set_error(self, state: DeepAgentState, run_id: str) -> bool:
        """Validate request and set error state if invalid."""
        validation = RequestValidator.validate(state.user_request)
        if not validation.is_valid:
            logger.error(f"Invalid request for {run_id}: {validation.validation_errors}")
            state.triage_result = {"error": "Invalid request", 
                                  "validation_errors": validation.validation_errors}
            return False
        return True
    
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute the enhanced triage logic."""
        start_time = time.time()
        await self._send_initial_update(run_id, stream_updates)
        
        request_hash = self.cache_manager.generate_hash(state.user_request)
        cached = await self.cache_manager.get_cached(request_hash)
        
        if cached:
            result = self._handle_cached_result(cached, start_time)
        else:
            result = await self._process_with_llm(state, run_id, start_time)
            await self.cache_manager.cache_result(request_hash, result)
        
        await self._finalize_result(state, result, run_id, stream_updates)
    
    async def _send_initial_update(self, run_id: str, stream_updates: bool) -> None:
        """Send initial processing update."""
        if stream_updates:
            await self._send_update(run_id, {
                "status": "processing",
                "message": "Analyzing user request..."
            })
    
    def _handle_cached_result(self, cached: Dict, start_time: float) -> Dict:
        """Handle cached result with updated metadata."""
        cached["metadata"]["cache_hit"] = True
        cached["metadata"]["triage_duration_ms"] = int((time.time() - start_time) * 1000)
        return cached
    
    async def _process_with_llm(self, state: DeepAgentState, run_id: str, 
                                start_time: float) -> Dict:
        """Process request with LLM."""
        for retry in range(self.max_retries):
            result = await self._try_llm_processing(state.user_request)
            if result:
                return self._add_metadata(result, start_time, retry)
            if retry < self.max_retries - 1:
                await asyncio.sleep(2 ** retry)
        
        return self._create_fallback_result(state.user_request, start_time)
    
    async def _try_llm_processing(self, request: str) -> Optional[Dict]:
        """Try to process request with LLM."""
        try:
            prompt = self._build_enhanced_prompt(request)
            return await self._get_structured_response(prompt)
        except Exception as e:
            logger.warning(f"LLM processing failed: {e}")
            return None
    
    def _build_enhanced_prompt(self, request: str) -> str:
        """Build enhanced prompt for LLM."""
        categories = "\n- ".join([
            "Cost Optimization", "Performance Optimization",
            "Workload Analysis", "Configuration & Settings",
            "Monitoring & Reporting", "Model Selection",
            "Supply Catalog Management", "Quality Optimization"
        ])
        return f"{triage_prompt_template.format(user_request=request)}\n\nCategories:\n- {categories}"
    
    async def _get_structured_response(self, prompt: str) -> Dict:
        """Get structured response from LLM."""
        try:
            result = await self.llm_manager.ask_structured_llm(
                prompt, llm_config_name='triage',
                schema=TriageResult, use_cache=False
            )
            return result.model_dump()
        except:
            return await self._get_json_response(prompt)
    
    async def _get_json_response(self, prompt: str) -> Optional[Dict]:
        """Get JSON response from LLM with fallback extraction."""
        response = await self.llm_manager.ask_llm(
            prompt + "\n\nReturn a properly formatted JSON object.",
            llm_config_name='triage'
        )
        extracted = extract_json_from_response(response)
        return self._validate_extracted_json(extracted)
    
    def _validate_extracted_json(self, extracted: Any) -> Optional[Dict]:
        """Validate extracted JSON with Pydantic."""
        if not extracted or not isinstance(extracted, dict):
            return None
        try:
            validated = TriageResult(**extracted)
            return validated.model_dump()
        except ValidationError:
            return extracted
    
    def _add_metadata(self, result: Dict, start_time: float, retry_count: int) -> Dict:
        """Add metadata to result."""
        if "metadata" not in result:
            result["metadata"] = {}
        result["metadata"].update({
            "triage_duration_ms": int((time.time() - start_time) * 1000),
            "cache_hit": False,
            "retry_count": retry_count,
            "fallback_used": False
        })
        return result
    
    def _create_fallback_result(self, request: str, start_time: float) -> Dict:
        """Create fallback result when LLM fails."""
        category = self._determine_fallback_category(request)
        entities = EntityExtractor.extract_entities(request)
        intent = IntentDetector.detect_intent(request)
        
        return TriageResult(
            category=category,
            confidence_score=0.5,
            priority=Priority.MEDIUM,
            complexity=Complexity.MODERATE,
            extracted_entities=entities,
            user_intent=intent,
            tool_recommendations=ToolRecommender.recommend(category, entities),
            metadata=TriageMetadata(
                triage_duration_ms=int((time.time() - start_time) * 1000),
                fallback_used=True,
                retry_count=self.max_retries
            )
        ).model_dump()
    
    def _determine_fallback_category(self, request: str) -> str:
        """Determine fallback category from request."""
        request_lower = request.lower()
        for keyword, category in self.fallback_categories.items():
            if keyword in request_lower:
                return category
        return "General Inquiry"
    
    async def _finalize_result(self, state: DeepAgentState, result: Dict,
                               run_id: str, stream_updates: bool) -> None:
        """Finalize and set triage result."""
        self._enhance_result(state, result)
        state.triage_result = result
        self._log_metrics(result, run_id)
        if stream_updates:
            await self._send_final_update(run_id, result)
    
    def _enhance_result(self, state: DeepAgentState, result: Dict) -> None:
        """Enhance result with missing components."""
        if not result.get("extracted_entities"):
            entities = EntityExtractor.extract_entities(state.user_request)
            result["extracted_entities"] = entities.model_dump()
        
        if not result.get("user_intent"):
            intent = IntentDetector.detect_intent(state.user_request)
            result["user_intent"] = intent.model_dump()
        
        result["is_admin_mode"] = IntentDetector.detect_admin_mode(state.user_request)
        self._adjust_admin_category(state.user_request, result)
        self._add_tool_recommendations(result)
    
    def _adjust_admin_category(self, request: str, result: Dict) -> None:
        """Adjust category for admin mode requests."""
        if not result.get("is_admin_mode"):
            return
        
        request_lower = request.lower()
        if "synthetic" in request_lower or "generate data" in request_lower:
            result["category"] = "Synthetic Data Generation"
        elif "corpus" in request_lower:
            result["category"] = "Corpus Management"
    
    def _add_tool_recommendations(self, result: Dict) -> None:
        """Add tool recommendations if missing."""
        if result.get("tool_recommendations"):
            return
        
        from app.agents.triage.models import ExtractedEntities
        entities = ExtractedEntities(**result.get("extracted_entities", {}))
        tools = ToolRecommender.recommend(result.get("category", "General"), entities)
        result["tool_recommendations"] = [t.model_dump() for t in tools]
    
    def _log_metrics(self, result: Dict, run_id: str) -> None:
        """Log performance metrics."""
        metadata = result.get("metadata", {})
        logger.info(
            f"Triage completed for {run_id}: "
            f"category={result.get('category')}, "
            f"confidence={result.get('confidence_score', 0)}, "
            f"duration={metadata.get('triage_duration_ms')}ms, "
            f"cache_hit={metadata.get('cache_hit')}"
        )
    
    async def _send_final_update(self, run_id: str, result: Dict) -> None:
        """Send final update with results."""
        await self._send_update(run_id, {
            "status": "processed",
            "message": f"Categorized as: {result.get('category', 'Unknown')}",
            "result": result
        })
    
    async def cleanup(self, state: DeepAgentState, run_id: str) -> None:
        """Cleanup after execution."""
        await super().cleanup(state, run_id)
        if state.triage_result and isinstance(state.triage_result, dict):
            metadata = state.triage_result.get("metadata", {})
            if metadata:
                logger.debug(f"Triage metrics for {run_id}: {metadata}")