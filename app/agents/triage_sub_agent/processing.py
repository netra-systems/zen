"""Triage Sub Agent Processing Module
Split from main agent to comply with 300-line limit.
Contains LLM processing and WebSocket methods.
"""

import time
import asyncio
from typing import Dict, Any
from pydantic import ValidationError

from app.agents.prompts import triage_prompt_template
from app.agents.config import agent_config
from app.logging_config import central_logger

from .models import TriageResult, ExtractedEntities

logger = central_logger.get_logger(__name__)


class TriageProcessor:
    """Handles LLM processing and WebSocket updates for triage."""
    
    def __init__(self, triage_core, llm_manager):
        self.triage_core = triage_core
        self.llm_manager = llm_manager
        self.logger = logger
    
    async def process_with_llm(self, state, run_id, start_time):
        """Process request with LLM using structured generation"""
        retry_count = 0
        triage_result = await self._retry_llm_processing(state, run_id, retry_count)
        
        if not triage_result:
            triage_result = self._create_fallback_triage_result(state, run_id)
        
        return self._add_metadata(triage_result, start_time, retry_count)
    
    def _build_enhanced_prompt(self, user_request):
        """Build enhanced prompt for LLM processing"""
        base_prompt = triage_prompt_template.format(user_request=user_request)
        analysis_instructions = self._get_analysis_instructions()
        category_options = self._get_category_options()
        
        return f"{base_prompt}\n\n{analysis_instructions}\n\n{category_options}"
    
    async def _fallback_llm_processing(self, enhanced_prompt, run_id, struct_error):
        """Fallback to regular LLM with JSON extraction"""
        self._log_fallback_warning(struct_error)
        llm_response = await self._get_fallback_llm_response(enhanced_prompt)
        extracted_json = self.triage_core.extract_and_validate_json(llm_response)
        
        if extracted_json:
            return self._process_extracted_fallback_json(extracted_json, run_id)
        return None
    
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
            import json
            return json.loads(parameters_str)
        except (json.JSONDecodeError, TypeError):
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
        """Add metadata to triage result"""
        self._ensure_metadata_section(triage_result)
        metadata_updates = self._build_metadata_updates(start_time, retry_count)
        triage_result["metadata"].update(metadata_updates)
        return triage_result
    
    def _ensure_metadata_section(self, triage_result):
        """Ensure metadata section exists in triage result."""
        if not triage_result.get("metadata"):
            triage_result["metadata"] = {}
    
    def _build_metadata_updates(self, start_time, retry_count):
        """Build metadata updates dictionary."""
        return {
            "triage_duration_ms": int((time.time() - start_time) * 1000),
            "cache_hit": False,
            "retry_count": retry_count,
            "fallback_used": retry_count >= self.triage_core.max_retries
        }
    
    def log_performance_metrics(self, run_id, triage_result):
        """Log performance metrics"""
        metrics = self._extract_performance_metrics(triage_result)
        log_message = self._format_performance_log_message(run_id, metrics)
        self.logger.info(log_message)
    
    def _extract_performance_metrics(self, triage_result):
        """Extract performance metrics from triage result."""
        metadata = triage_result.get('metadata', {})
        return {
            'category': triage_result.get('category'),
            'confidence': triage_result.get('confidence_score', 0),
            'duration_ms': metadata.get('triage_duration_ms'),
            'cache_hit': metadata.get('cache_hit')
        }
    
    def _format_performance_log_message(self, run_id, metrics):
        """Format performance log message."""
        return (
            f"Triage completed for run_id {run_id}: "
            f"category={metrics['category']}, confidence={metrics['confidence']}, "
            f"duration={metrics['duration_ms']}ms, cache_hit={metrics['cache_hit']}"
        )


class WebSocketHandler:
    """Handles WebSocket communication for triage agent."""
    
    def __init__(self, send_update_func):
        self._send_update = send_update_func
        self.logger = logger
    
    async def send_final_update(self, run_id, triage_result):
        """Send final update via WebSocket"""
        await self._send_update(run_id, {
            "status": "processed",
            "message": f"Request categorized as: {triage_result.get('category', 'Unknown')} "
                      f"with confidence {triage_result.get('confidence_score', 0):.2f}",
            "result": triage_result
        })