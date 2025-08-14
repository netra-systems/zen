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
                except ValidationError as validation_error:
                    # Try to fix validation errors and retry once
                    if "Input should be a valid dictionary" in str(validation_error):
                        self.logger.warning(f"String parameters detected, using fallback processing")
                        triage_result = await self._fallback_llm_processing(
                            enhanced_prompt, run_id, validation_error
                        )
                    else:
                        raise validation_error
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
                # Fix string parameters before validation
                fixed_json = self._fix_string_parameters(extracted_json)
                validated_result = TriageResult(**fixed_json)
                return validated_result.model_dump()
            except ValidationError as e:
                self.logger.warning(f"Validation error for run_id {run_id}: {e}")
                # Return fixed JSON even if validation fails
                return self._fix_string_parameters(extracted_json)
        
        return None
    
    def _fix_string_parameters(self, data):
        """Fix string parameters in tool recommendations - convert JSON strings to dicts"""
        if not isinstance(data, dict):
            return data
        
        # Fix tool_recommendations parameters field
        if "tool_recommendations" in data and isinstance(data["tool_recommendations"], list):
            for rec in data["tool_recommendations"]:
                if isinstance(rec, dict) and "parameters" in rec:
                    if isinstance(rec["parameters"], str):
                        try:
                            # Parse JSON string to dict
                            import json
                            rec["parameters"] = json.loads(rec["parameters"])
                        except (json.JSONDecodeError, TypeError):
                            # Fallback to empty dict if parsing fails
                            rec["parameters"] = {}
        
        return data
    
    def enrich_triage_result(self, triage_result, user_request):
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
    
    def log_performance_metrics(self, run_id, triage_result):
        """Log performance metrics"""
        self.logger.info(
            f"Triage completed for run_id {run_id}: "
            f"category={triage_result.get('category')}, "
            f"confidence={triage_result.get('confidence_score', 0)}, "
            f"duration={triage_result['metadata']['triage_duration_ms']}ms, "
            f"cache_hit={triage_result['metadata']['cache_hit']}"
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