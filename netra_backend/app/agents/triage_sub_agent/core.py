"""Triage Sub Agent Core Logic

This module contains the core triage agent implementation.
"""

import asyncio
import json
import re
import time
from typing import Any, Dict, Optional, TYPE_CHECKING

from pydantic import ValidationError

from netra_backend.app.agents.config import agent_config
from netra_backend.app.agents.triage_sub_agent.entity_extractor import EntityExtractor
from netra_backend.app.agents.triage_sub_agent.intent_detector import IntentDetector
from netra_backend.app.agents.triage_sub_agent.models import (
    Complexity,
    Priority,
    TriageMetadata,
    TriageResult,
)
from netra_backend.app.agents.triage_sub_agent.tool_recommender import ToolRecommender
from netra_backend.app.agents.triage_sub_agent.validator import RequestValidator
from netra_backend.app.core.serialization.unified_json_handler import (
    LLMResponseParser,
    JSONErrorFixer,
    safe_json_loads
)
from netra_backend.app.services.cache.cache_helpers import CacheHelpers
from netra_backend.app.logging_config import central_logger

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext

logger = central_logger.get_logger(__name__)


class TriageCore:
    """Core triage processing logic aligned with UserExecutionContext pattern.
    
    This class provides core triage functionality that can work both:
    1. With UserExecutionContext (new pattern) - preferred
    2. Standalone (legacy compatibility) - deprecated
    """
    
    def __init__(self, context: Optional['UserExecutionContext'] = None):
        """Initialize the triage core.
        
        Args:
            context: Optional UserExecutionContext for request isolation
        """
        self.context = context  # Store for request-scoped operations
        self._init_core_components()
        self._init_fallback_categories()
        
        # Initialize cache helper for key generation (SSOT)
        # Pass None for cache_manager since we only need the key generation
        self._cache_helper = CacheHelpers(None)
    
    def _init_core_config(self) -> None:
        """Initialize core configuration settings."""
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
        """Generate a hash for caching similar requests.
        
        Uses canonical cache key generation from CacheHelpers for SSOT.
        """
        # Normalize the request for better cache hits
        normalized = request.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Use canonical hash_key_data method from CacheHelpers
        key_data = {"request": normalized}
        if self.context:
            # Include user context for proper isolation
            key_data["user_id"] = self.context.user_id
            key_data["thread_id"] = self.context.thread_id
        
        return self._cache_helper.hash_key_data(key_data)

    
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
        # Use canonical LLMResponseParser from unified_json_handler
        parser = LLMResponseParser()
        result = parser.safe_json_parse(response)
        
        # If result is a dict, return it; otherwise try error fixing
        if isinstance(result, dict):
            return result
        
        # Try error fixing if parsing failed
        if isinstance(result, str):
            fixer = JSONErrorFixer()
            fixed = fixer.fix_common_json_errors(result)
            try:
                parsed = safe_json_loads(fixed)
                return parsed if isinstance(parsed, dict) else None
            except json.JSONDecodeError:
                # Try recovery as last resort
                return fixer.recover_truncated_json(result)
        
        # Fallback to manual extraction if all else fails
        return self._extract_key_value_pairs(response)
    
    def _extract_key_value_pairs(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract key-value pairs manually as fallback"""
        try:
            # Try regex pattern extraction
            pattern = r'"([^"]+)"\s*:\s*"([^"]*)"'
            matches = re.findall(pattern, response)
            if matches:
                return {key: value for key, value in matches}
            
            # Try line-based extraction
            lines = response.split('\n')
            result = {}
            for line in lines:
                if ':' not in line:
                    continue
                match = re.match(r'^\s*"?(\w+)"?\s*:\s*"([^"]*)"', line)
                if match:
                    result[match.group(1)] = match.group(2)
            
            return result if result else None
        except Exception as e:
            logger.debug(f"Manual extraction failed: {e}")
            return None