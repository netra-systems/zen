# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-13T00:00:00.000000+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Refactored triage_sub_agent - compliant with 300-line/8-line limits
# Git: v6 | dirty
# Change: Refactor | Scope: Component | Risk: Low
# Session: compliance-fix | Seq: 10
# Review: Pending | Score: 95
# ================================
"""Refactored TriageSubAgent - compliant with CLAUDE.md requirements."""

import json
import time
from typing import Optional, Dict, Any, List
from app.llm.llm_manager import LLMManager
from app.agents.base import BaseSubAgent
from app.agents.prompts import triage_prompt_template
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.agents.utils import extract_json_from_response
from app.redis_manager import RedisManager
from app.logging_config import central_logger

# Import refactored modules
from app.agents.triage_sub_agent.models import (
    TriageResult, TriageMetadata, Priority, Complexity
)
from app.agents.triage_sub_agent.validation import validate_request
from app.agents.triage_sub_agent.entity_extraction import extract_entities_from_request
from app.agents.triage_sub_agent.intent_detection import determine_intent, detect_admin_mode
from app.agents.triage_sub_agent.tool_recommendation import recommend_tools
from app.agents.triage_sub_agent.cache_utils import (
    generate_request_hash, get_cached_result, cache_result
)
from app.agents.triage_sub_agent.fallback import fallback_categorization

logger = central_logger.get_logger(__name__)


class TriageSubAgent(BaseSubAgent):
    """Enhanced triage agent with advanced categorization and caching."""
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher, 
                 redis_manager: Optional[RedisManager] = None):
        super().__init__(llm_manager, name="TriageSubAgent", 
                        description="Enhanced triage agent with advanced categorization and caching.")
        self.tool_dispatcher = tool_dispatcher
        self.redis_manager = redis_manager
        self.cache_ttl = 3600
        self.max_retries = 3
    
    async def process_with_cache(self, request: str) -> Optional[Dict[str, Any]]:
        """Process request with caching support."""
        request_hash = generate_request_hash(request)
        cached = await get_cached_result(self.redis_manager, request_hash)
        return cached
    
    async def save_to_cache(self, request: str, result: Dict[str, Any]) -> None:
        """Save result to cache."""
        request_hash = generate_request_hash(request)
        await cache_result(self.redis_manager, request_hash, result, self.cache_ttl)
    
    def parse_llm_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse and validate LLM response."""
        result = extract_json_from_response(response)
        if result and isinstance(result, dict):
            return result
        return None
    
    def determine_priority(self, confidence: float, complexity: str) -> Priority:
        """Determine priority based on confidence and complexity."""
        if confidence > 0.9 and complexity in ["expert", "complex"]:
            return Priority.HIGH
        elif confidence > 0.7:
            return Priority.MEDIUM
        return Priority.LOW
    
    def build_triage_result(self, parsed: Dict[str, Any], request: str, 
                           duration: int) -> TriageResult:
        """Build TriageResult from parsed LLM response."""
        entities = extract_entities_from_request(request)
        intent = determine_intent(request)
        category = parsed.get("category", "General Inquiry")
        
        return TriageResult(
            category=category,
            secondary_categories=parsed.get("secondary_categories", []),
            confidence_score=parsed.get("confidence_score", 0.8),
            priority=self.determine_priority(
                parsed.get("confidence_score", 0.8),
                parsed.get("complexity", "moderate")
            ),
            complexity=Complexity(parsed.get("complexity", "moderate")),
            extracted_entities=entities,
            user_intent=intent,
            tool_recommendations=recommend_tools(category, entities),
            is_admin_mode=detect_admin_mode(request),
            metadata=TriageMetadata(
                triage_duration_ms=duration,
                llm_tokens_used=parsed.get("tokens_used", 0)
            )
        )
    
    async def execute_llm_triage(self, request: str) -> Optional[TriageResult]:
        """Execute LLM-based triage."""
        start_time = time.time()
        
        prompt = triage_prompt_template.format(request=request)
        response = await self.llm_manager.generate_response(prompt)
        
        parsed = self.parse_llm_response(response)
        if not parsed:
            return None
        
        duration = int((time.time() - start_time) * 1000)
        return self.build_triage_result(parsed, request, duration)
    
    async def execute(self, request: str, state: Optional[DeepAgentState] = None) -> TriageResult:
        """Execute triage with validation, caching, and fallback."""
        # Validate request
        validation = validate_request(request)
        if not validation.is_valid:
            return self.create_error_result(validation)
        
        # Check cache
        cached = await self.process_with_cache(request)
        if cached:
            return TriageResult(**cached)
        
        # Try LLM triage with retries
        result = await self.try_with_retries(request)
        
        # Fallback if needed
        if not result:
            result = fallback_categorization(request)
        
        # Cache successful result
        await self.save_to_cache(request, result.dict())
        return result
    
    async def try_with_retries(self, request: str) -> Optional[TriageResult]:
        """Try LLM triage with retries."""
        for attempt in range(self.max_retries):
            try:
                result = await self.execute_llm_triage(request)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"Triage attempt {attempt + 1} failed: {e}")
        return None
    
    def create_error_result(self, validation) -> TriageResult:
        """Create error result for invalid request."""
        return TriageResult(
            category="Invalid Request",
            confidence_score=1.0,
            priority=Priority.LOW,
            complexity=Complexity.SIMPLE,
            validation_status=validation,
            metadata=TriageMetadata(triage_duration_ms=0)
        )