"""Triage Sub Agent Core Logic

This module contains the core triage agent implementation.
"""

import json
import time
import hashlib
import re
import asyncio
from typing import Optional, Dict, Any

from pydantic import ValidationError
from netra_backend.app.agents.utils import extract_json_from_response
from netra_backend.app.agents.config import agent_config
from netra_backend.app.logging_config import central_logger

from netra_backend.app.services.apex_optimizer_agent.models import TriageResult, TriageMetadata, Priority, Complexity
from netra_backend.app.agents.triage_sub_agent.entity_extractor import EntityExtractor
from netra_backend.app.core.configuration.validator import RequestValidator
from netra_backend.app.agents.triage_sub_agent.intent_detector import IntentDetector
from netra_backend.app.agents.triage_sub_agent.tool_recommender import ToolRecommender

logger = central_logger.get_logger(__name__)


class TriageCore:
    """Core triage processing logic"""
    
    def __init__(self, redis_manager=None):
        """Initialize the triage core"""
        self._init_core_config(redis_manager)
        self._init_core_components()
        self._init_fallback_categories()
    
    def _init_core_config(self, redis_manager) -> None:
        """Initialize core configuration settings."""
        self.redis_manager = redis_manager
        self.cache_ttl = agent_config.cache.redis_ttl
        self.max_retries = agent_config.retry.max_retries
    
    def _init_core_components(self) -> None:
        """Initialize core triage components."""
        self.entity_extractor = EntityExtractor()
        self.validator = RequestValidator()
        self.intent_detector = IntentDetector()
        self.tool_recommender = ToolRecommender()
    
    def _init_fallback_categories(self) -> None:
        """Initialize fallback categories for simple classification."""
        core_categories = self._get_core_categories()
        extended_categories = self._get_extended_categories()
        self.fallback_categories = {**core_categories, **extended_categories}

    def _get_core_categories(self) -> Dict[str, str]:
        """Get core optimization categories."""
        return {
            "optimize": "Cost Optimization",
            "performance": "Performance Optimization",
            "analyze": "Workload Analysis",
            "configure": "Configuration & Settings"
        }

    def _get_extended_categories(self) -> Dict[str, str]:
        """Get extended category mappings."""
        return {
            "report": "Monitoring & Reporting",
            "model": "Model Selection",
            "supply": "Supply Catalog Management",
            "quality": "Quality Optimization"
        }
    
    def generate_request_hash(self, request: str) -> str:
        """Generate a hash for caching similar requests"""
        # Normalize the request for better cache hits
        normalized = request.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    async def get_cached_result(self, request_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached triage result if available"""
        if not self._is_cache_available():
            return None
        return await self._safe_cache_retrieval(request_hash)

    def _is_cache_available(self) -> bool:
        """Check if cache is available for use."""
        return self.redis_manager is not None

    async def _safe_cache_retrieval(self, request_hash: str) -> Optional[Dict[str, Any]]:
        """Safely retrieve from cache with error handling."""
        try:
            return await self._retrieve_from_redis_cache(request_hash)
        except Exception as e:
            logger.warning(f"Failed to retrieve from cache: {e}")
            return None
    
    async def _retrieve_from_redis_cache(self, request_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve data from Redis cache."""
        cache_key = self._build_cache_key(request_hash)
        cached = await self.redis_manager.get(cache_key)
        return self._process_cached_data(cached, request_hash)

    def _build_cache_key(self, request_hash: str) -> str:
        """Build cache key for request hash."""
        return f"triage:cache:{request_hash}"

    def _process_cached_data(self, cached: str, request_hash: str) -> Optional[Dict[str, Any]]:
        """Process cached data if available."""
        if cached:
            logger.info(f"Cache hit for request hash: {request_hash}")
            return json.loads(cached)
        return None
    
    async def cache_result(self, request_hash: str, result: Dict[str, Any]) -> None:
        """Cache triage result for future use"""
        if not self._is_cache_available():
            return
        await self._safe_cache_storage(request_hash, result)

    async def _safe_cache_storage(self, request_hash: str, result: Dict[str, Any]) -> None:
        """Safely store result in cache with error handling."""
        try:
            await self._store_in_redis_cache(request_hash, result)
        except Exception as e:
            logger.warning(f"Failed to cache result: {e}")

    async def _store_in_redis_cache(self, request_hash: str, result: Dict[str, Any]) -> None:
        """Store result in Redis cache."""
        cache_key = self._build_cache_key(request_hash)
        serialized = json.dumps(result)
        await self.redis_manager.set(cache_key, serialized, ex=self.cache_ttl)
        logger.debug(f"Cached result for request hash: {request_hash}")
    
    def create_fallback_result(self, request: str) -> TriageResult:
        """Simple fallback categorization when LLM fails"""
        category = self._categorize_request(request)
        components = self._extract_triage_components(request, category)
        return self._build_fallback_triage_result(category, *components)

    def _categorize_request(self, request: str) -> str:
        """Categorize request using fallback logic."""
        request_lower = request.lower()
        return self._find_best_matching_category(request_lower)

    def _extract_triage_components(self, request: str, category: str) -> tuple:
        """Extract entities, intent, and tools for triage."""
        entities = self.entity_extractor.extract_entities(request)
        intent = self.intent_detector.detect_intent(request)
        tools = self.tool_recommender.recommend_tools(category, entities)
        return entities, intent, tools
    
    def _find_best_matching_category(self, request_lower: str) -> str:
        """Find best matching category based on keywords."""
        for keyword, cat in self.fallback_categories.items():
            if keyword in request_lower:
                return cat
        return "General Inquiry"
    
    def _build_fallback_triage_result(
        self, category: str, entities, intent, tools
    ) -> TriageResult:
        """Build fallback triage result with all components."""
        base_fields = self._get_fallback_base_fields(category)
        component_fields = self._get_fallback_component_fields(entities, intent, tools)
        return TriageResult(**{**base_fields, **component_fields})

    def _get_fallback_base_fields(self, category: str) -> Dict[str, Any]:
        """Get base fields for fallback result."""
        core_fields = {"category": category, "confidence_score": 0.5}
        level_fields = {"priority": Priority.MEDIUM, "complexity": Complexity.MODERATE}
        metadata_field = {"metadata": self._create_fallback_metadata()}
        return {**core_fields, **level_fields, **metadata_field}

    def _get_fallback_component_fields(self, entities, intent, tools) -> Dict[str, Any]:
        """Get component fields for fallback result."""
        return {
            "extracted_entities": entities,
            "user_intent": intent,
            "tool_recommendations": tools
        }
    
    def _create_fallback_metadata(self) -> TriageMetadata:
        """Create metadata for fallback result."""
        return TriageMetadata(
            triage_duration_ms=0,
            fallback_used=True,
            retry_count=0
        )
    
    def extract_and_validate_json(self, response: str) -> Optional[Dict[str, Any]]:
        """Enhanced JSON extraction with multiple strategies and validation"""
        strategies = [self._try_standard_extraction, self._extract_with_regex, self._extract_key_value_pairs]
        return self._apply_extraction_strategies(response, strategies)

    def _apply_extraction_strategies(self, response: str, strategies: list) -> Optional[Dict[str, Any]]:
        """Apply extraction strategies in sequence."""
        for strategy in strategies:
            result = strategy(response)
            if result:
                return result
        return None

    def _try_standard_extraction(self, response: str) -> Optional[Dict[str, Any]]:
        """Try standard JSON extraction method."""
        result = extract_json_from_response(response)
        return result if result and isinstance(result, dict) else None
    
    def _extract_with_regex(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract JSON using regex patterns"""
        brace_match = self._find_json_braces(response)
        if not brace_match:
            return None
        return self._parse_json_match(brace_match.group())

    def _find_json_braces(self, response: str):
        """Find JSON brace structure in response."""
        return re.search(r'\{.*\}', response, re.DOTALL)

    def _parse_json_match(self, match: str) -> Optional[Dict[str, Any]]:
        """Parse matched JSON string."""
        try:
            repaired = self._repair_json(match)
            result = json.loads(repaired)
            return result if isinstance(result, dict) else None
        except json.JSONDecodeError:
            return None
    
    def _repair_json(self, json_str: str) -> str:
        """Repair common JSON formatting issues"""
        repaired = json_str
        repaired = re.sub(r',\s*}', '}', repaired)  # Remove trailing commas
        repaired = re.sub(r',\s*]', ']', repaired)  # Remove trailing commas in arrays
        repaired = repaired.replace("'", '"')  # Replace single quotes
        return repaired
    
    def _extract_key_value_pairs(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract key-value pairs manually"""
        try:
            regex_result = self._extract_with_regex_pattern(response)
            return regex_result if regex_result else self._extract_from_lines(response)
        except Exception as e:
            logger.debug(f"Manual extraction failed: {e}")
            return None

    def _extract_with_regex_pattern(self, response: str) -> Optional[Dict[str, str]]:
        """Extract key-value pairs using regex pattern."""
        pattern = r'"([^"]+)"\s*:\s*"([^"]*)"'
        matches = re.findall(pattern, response)
        return {key: value for key, value in matches} if matches else None
    
    def _extract_from_lines(self, response: str) -> Dict[str, str]:
        """Extract key-value pairs from lines"""
        lines = response.split('\n')
        result = {}
        self._process_lines_for_key_values(lines, result)
        return result if result else {}

    def _process_lines_for_key_values(self, lines: list, result: dict) -> None:
        """Process all lines for key-value extraction."""
        for line in lines:
            self._process_line_for_key_value(line, result)
    
    def _process_line_for_key_value(self, line: str, result: dict) -> None:
        """Process a single line for key-value extraction."""
        if ':' not in line:
            return
        key_match = self._extract_key_value_match(line)
        if key_match:
            self._store_key_value_pair(key_match, result)
    
    def _extract_key_value_match(self, line: str):
        """Extract key-value match from line."""
        return re.match(r'^\s*"?(\w+)"?\s*:\s*"([^"]*)"', line)
    
    def _store_key_value_pair(self, key_match, result: dict) -> None:
        """Store extracted key-value pair in result."""
        key = key_match.group(1)
        value = key_match.group(2)
        result[key] = value