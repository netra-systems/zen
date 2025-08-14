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
from app.agents.utils import extract_json_from_response
from app.agents.config import agent_config
from app.logging_config import central_logger

from .models import TriageResult, TriageMetadata, Priority, Complexity
from .entity_extractor import EntityExtractor
from .validator import RequestValidator
from .intent_detector import IntentDetector
from .tool_recommender import ToolRecommender

logger = central_logger.get_logger(__name__)


class TriageCore:
    """Core triage processing logic"""
    
    def __init__(self, redis_manager=None):
        """Initialize the triage core"""
        self.redis_manager = redis_manager
        self.cache_ttl = agent_config.cache.redis_ttl
        self.max_retries = agent_config.retry.max_retries
        
        # Initialize components
        self.entity_extractor = EntityExtractor()
        self.validator = RequestValidator()
        self.intent_detector = IntentDetector()
        self.tool_recommender = ToolRecommender()
        
        # Fallback categories for simple classification
        self.fallback_categories = {
            "optimize": "Cost Optimization",
            "performance": "Performance Optimization",
            "analyze": "Workload Analysis",
            "configure": "Configuration & Settings",
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
        return hashlib.md5(normalized.encode()).hexdigest()
    
    async def get_cached_result(self, request_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached triage result if available"""
        if not self.redis_manager:
            return None
        
        try:
            cache_key = f"triage:cache:{request_hash}"
            cached = await self.redis_manager.get(cache_key)
            if cached:
                logger.info(f"Cache hit for request hash: {request_hash}")
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Failed to retrieve from cache: {e}")
        
        return None
    
    async def cache_result(self, request_hash: str, result: Dict[str, Any]) -> None:
        """Cache triage result for future use"""
        if not self.redis_manager:
            return
        
        try:
            cache_key = f"triage:cache:{request_hash}"
            await self.redis_manager.set(cache_key, json.dumps(result), ex=self.cache_ttl)
            logger.debug(f"Cached result for request hash: {request_hash}")
        except Exception as e:
            logger.warning(f"Failed to cache result: {e}")
    
    def create_fallback_result(self, request: str) -> TriageResult:
        """Simple fallback categorization when LLM fails"""
        request_lower = request.lower()
        
        # Find best matching category based on keywords
        category = "General Inquiry"
        for keyword, cat in self.fallback_categories.items():
            if keyword in request_lower:
                category = cat
                break
        
        entities = self.entity_extractor.extract_entities(request)
        intent = self.intent_detector.detect_intent(request)
        tools = self.tool_recommender.recommend_tools(category, entities)
        
        return TriageResult(
            category=category,
            confidence_score=0.5,  # Lower confidence for fallback
            priority=Priority.MEDIUM,
            complexity=Complexity.MODERATE,
            extracted_entities=entities,
            user_intent=intent,
            tool_recommendations=tools,
            metadata=TriageMetadata(
                triage_duration_ms=0,
                fallback_used=True,
                retry_count=0
            )
        )
    
    def extract_and_validate_json(self, response: str) -> Optional[Dict[str, Any]]:
        """Enhanced JSON extraction with multiple strategies and validation"""
        # Strategy 1: Standard extraction
        result = extract_json_from_response(response)
        if result and isinstance(result, dict):
            return result
        
        # Strategy 2: Find JSON-like structure with regex
        result = self._extract_with_regex(response)
        if result:
            return result
        
        # Strategy 3: Extract key-value pairs manually
        return self._extract_key_value_pairs(response)
    
    def _extract_with_regex(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract JSON using regex patterns"""
        brace_match = re.search(r'\{.*\}', response, re.DOTALL)
        if not brace_match:
            return None
        
        match = brace_match.group()
        try:
            # Try to repair common JSON issues
            repaired = self._repair_json(match)
            result = json.loads(repaired)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass
        
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
            # Try to extract individual key-value pairs using regex
            pattern = r'"([^"]+)"\s*:\s*"([^"]*)"'
            matches = re.findall(pattern, response)
            
            if matches:
                return {key: value for key, value in matches}
            
            # Fallback to line-by-line extraction
            return self._extract_from_lines(response)
        except Exception as e:
            logger.debug(f"Manual extraction failed: {e}")
        
        return None
    
    def _extract_from_lines(self, response: str) -> Dict[str, str]:
        """Extract key-value pairs from lines"""
        lines = response.split('\n')
        result = {}
        
        for line in lines:
            if ':' in line:
                key_match = re.match(r'^\s*"?(\w+)"?\s*:\s*"([^"]*)"', line)
                if key_match:
                    key = key_match.group(1)
                    value = key_match.group(2)
                    result[key] = value
        
        return result if result else {}