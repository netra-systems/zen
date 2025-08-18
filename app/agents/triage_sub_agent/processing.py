"""Modernized Triage Processing Module with ExecutionMonitor integration.

Integrates modern execution patterns: ExecutionMonitor, ExecutionErrorHandler,
and modern LLM processing with comprehensive metrics tracking.
"""

import time
import asyncio
from typing import Dict, Any, TYPE_CHECKING
from pydantic import ValidationError

if TYPE_CHECKING:
    from app.agents.triage_sub_agent.agent import TriageSubAgent

from app.agents.prompts import triage_prompt_template
from app.agents.config import agent_config
from app.logging_config import central_logger
from app.agents.base.interface import ExecutionContext
from app.agents.base.monitoring import ExecutionMonitor, ExecutionMetrics
from app.agents.base.errors import ExecutionErrorHandler
from .processing_monitoring import (
    TriageProcessingMonitor, TriageWebSocketMonitor, TriageProcessingErrorHelper
)

from .models import TriageResult, ExtractedEntities

logger = central_logger.get_logger(__name__)


class TriageProcessor:
    """Modernized triage processor with ExecutionMonitor integration."""
    
    def __init__(self, triage_core, llm_manager, agent: 'TriageSubAgent' = None):
        self.triage_core = triage_core
        self.llm_manager = llm_manager
        self.logger = logger
        self._init_modern_components(agent)
    
    def _init_modern_components(self, agent: 'TriageSubAgent') -> None:
        """Initialize modern execution monitoring components."""
        self.monitor = getattr(agent, 'monitor', ExecutionMonitor()) if agent else ExecutionMonitor()
        self.error_handler = ExecutionErrorHandler()
        self.processing_monitor = TriageProcessingMonitor(self.monitor)
        self.error_helper = TriageProcessingErrorHelper()
    
    async def process_with_llm(self, state, run_id, start_time):
        """Process request with LLM using modern monitoring patterns."""
        context = self._create_execution_context(state, run_id)
        return await self._process_with_monitoring(context, start_time)
    
    def _create_execution_context(self, state, run_id):
        """Create execution context for monitoring."""
        return ExecutionContext(
            run_id=run_id,
            agent_name="TriageProcessor",
            state=state
        )
    
    async def _process_with_monitoring(self, context: ExecutionContext, start_time: float):
        """Process with comprehensive monitoring."""
        self.monitor.start_execution(context)
        try:
            return await self._execute_llm_processing(context, start_time)
        except Exception as e:
            return await self._handle_processing_error(context, e, start_time)
        finally:
            self._update_processing_metrics()
    
    async def _execute_llm_processing(self, context: ExecutionContext, start_time: float):
        """Execute LLM processing with retry logic."""
        retry_count = 0
        triage_result = await self._retry_llm_processing(context.state, context.run_id, retry_count)
        return self._finalize_processing_result(triage_result, context, start_time, retry_count)
    
    def _finalize_processing_result(self, triage_result, context: ExecutionContext, 
                                  start_time: float, retry_count: int):
        """Finalize processing result with metadata and monitoring."""
        if not triage_result:
            triage_result = self._create_fallback_triage_result(context.state, context.run_id)
        return self._add_metadata(triage_result, start_time, retry_count)
    
    def _build_enhanced_prompt(self, user_request):
        """Build enhanced prompt for LLM processing."""
        base_prompt = triage_prompt_template.format(user_request=user_request)
        analysis_instructions = self._get_analysis_instructions()
        category_options = self._get_category_options()
        return f"{base_prompt}\n\n{analysis_instructions}\n\n{category_options}"
    
    async def _handle_processing_error(self, context: ExecutionContext, 
                                     error: Exception, start_time: float):
        """Handle processing error with modern error handling."""
        self.monitor.record_error(context, error)
        self.error_helper.log_processing_error(error, context.run_id)
        error_result = await self.error_handler.handle_execution_error(context, error)
        return self.error_helper.create_error_fallback_result(context.state, start_time)
    
    async def _fallback_llm_processing(self, enhanced_prompt, run_id, struct_error):
        """Fallback to regular LLM with JSON extraction and monitoring."""
        self._log_fallback_warning(struct_error)
        self.processing_monitor.record_fallback_metrics()
        llm_response = await self._get_fallback_llm_response(enhanced_prompt)
        extracted_json = self.triage_core.extract_and_validate_json(llm_response)
        return self._process_fallback_result(extracted_json, run_id)
    
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
        """Add metadata to triage result with monitoring metrics."""
        self._ensure_metadata_section(triage_result)
        metadata_updates = self._build_enhanced_metadata_updates(start_time, retry_count)
        triage_result["metadata"].update(metadata_updates)
        self.processing_monitor.record_success_metrics(triage_result)
        return triage_result
    
    def _ensure_metadata_section(self, triage_result):
        """Ensure metadata section exists in triage result."""
        if not triage_result.get("metadata"):
            triage_result["metadata"] = {}
    
    def _build_enhanced_metadata_updates(self, start_time, retry_count):
        """Build enhanced metadata updates with monitoring data - delegated to monitor."""
        max_retries = getattr(self.triage_core, 'max_retries', 3)
        return self.processing_monitor.build_enhanced_metadata_updates(
            start_time, retry_count, max_retries
        )
    
    def log_performance_metrics(self, run_id, triage_result):
        """Log performance metrics with enhanced monitoring data."""
        metrics = self.processing_monitor.extract_enhanced_performance_metrics(triage_result)
        log_message = self.processing_monitor.format_enhanced_performance_log_message(run_id, metrics)
        self.logger.info(log_message)
        self.processing_monitor.record_performance_metrics(metrics)
    
    def _extract_performance_metrics(self, triage_result):
        """Extract performance metrics from triage result."""
        metadata = triage_result.get('metadata', {})
        return {
            'category': triage_result.get('category'),
            'confidence': triage_result.get('confidence_score', 0),
            'duration_ms': metadata.get('triage_duration_ms'),
            'cache_hit': metadata.get('cache_hit')
        }
    
    # Modern monitoring helper methods - delegated to processing monitor
    def _update_processing_metrics(self) -> None:
        """Update processing metrics in monitor."""
        # Metrics are automatically tracked by the monitor
        pass
    
    def _process_fallback_result(self, extracted_json, run_id):
        """Process fallback result with monitoring."""
        if extracted_json:
            return self._process_extracted_fallback_json(extracted_json, run_id)
        return None


class WebSocketHandler:
    """Modernized WebSocket handler with execution monitoring integration."""
    
    def __init__(self, send_update_func, monitor: ExecutionMonitor = None):
        self._send_update = send_update_func
        self.logger = logger
        self.monitor = monitor or ExecutionMonitor()
        self.websocket_monitor = TriageWebSocketMonitor()
    
    async def send_final_update(self, run_id, triage_result):
        """Send final update via WebSocket with monitoring metrics."""
        self.websocket_monitor.record_websocket_metrics()
        update_message = self.websocket_monitor.build_final_update_message(triage_result)
        await self._send_update(run_id, update_message)
    
    def get_websocket_metrics(self) -> Dict[str, int]:
        """Get WebSocket-specific metrics."""
        return self.websocket_monitor.get_websocket_metrics()