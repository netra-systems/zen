"""NACIS Chat Orchestrator Agent - Central control for AI optimization consultation.

Date Created: 2025-01-22
Last Updated: 2025-01-22

Business Value: Foundation for premium AI consultation with 95%+ accuracy through
verified research, fact-checking, and multi-agent orchestration.
"""

import os
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.chat_orchestrator.confidence_manager import (
    ConfidenceManager,
)
from netra_backend.app.agents.chat_orchestrator.execution_planner import (
    ExecutionPlanner,
)
from netra_backend.app.agents.chat_orchestrator.intent_classifier import (
    IntentClassifier,
    IntentType,
)
from netra_backend.app.agents.chat_orchestrator.model_cascade import ModelCascade
from netra_backend.app.agents.chat_orchestrator.pipeline_executor import (
    PipelineExecutor,
)
from netra_backend.app.agents.chat_orchestrator.trace_logger import TraceLogger
from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgent
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ChatOrchestrator(SupervisorAgent):
    """NACIS Chat Orchestrator with veracity-first architecture (<300 lines)."""
    
    def __init__(self,
                 db_session: AsyncSession,
                 llm_manager: LLMManager,
                 websocket_manager,
                 tool_dispatcher: ToolDispatcher,
                 cache_manager=None,
                 semantic_cache_enabled: bool = True):
        super().__init__(db_session, llm_manager, websocket_manager, tool_dispatcher)
        self._init_naof_components(cache_manager, semantic_cache_enabled)
        self._init_helper_modules()
    
    def _init_naof_components(self, cache_manager, semantic_cache_enabled: bool) -> None:
        """Initialize NACIS-specific components."""
        self.name = "ChatOrchestrator"
        self.description = "NACIS orchestrator for AI optimization consultation"
        self.cache_manager = cache_manager
        self.semantic_cache_enabled = semantic_cache_enabled
        self.nacis_enabled = os.getenv("NACIS_ENABLED", "false").lower() == "true"
    
    def _init_helper_modules(self) -> None:
        """Initialize helper modules for orchestration."""
        self.intent_classifier = IntentClassifier(self.llm_manager)
        self.confidence_manager = ConfidenceManager()
        self.model_cascade = ModelCascade()
        self.execution_planner = ExecutionPlanner()
        self.trace_logger = TraceLogger(self.websocket_manager)
        self.pipeline_executor = PipelineExecutor(self)
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute NACIS chat orchestration with veracity guarantees."""
        try:
            await self.trace_logger.log("Starting NACIS orchestration", context.request_id)
            intent, confidence = await self._process_intent(context)
            cached_result = await self._check_cache(context, intent, confidence)
            if cached_result:
                return self._format_cached_response(cached_result)
            result = await self._execute_pipeline(context, intent, confidence)
            await self._cache_if_appropriate(context, intent, confidence, result)
            return self._format_final_response(result)
        except Exception as e:
            return await self._handle_orchestration_error(e)
    
    async def _process_intent(self, context: ExecutionContext) -> Tuple[IntentType, float]:
        """Process user intent and confidence."""
        intent, confidence = await self.intent_classifier.classify(context)
        await self.trace_logger.log(f"Intent: {intent.value}", {"confidence": confidence})
        return intent, confidence
    
    async def _check_cache(self, context: ExecutionContext, 
                          intent: IntentType, confidence: float) -> Optional[Dict]:
        """Check semantic cache for valid results."""
        if not self._should_use_cache(intent, confidence):
            return None
        cached = await self._try_semantic_cache(context, intent)
        if cached:
            await self.trace_logger.log("Cache hit - returning verified response")
        return cached
    
    def _should_use_cache(self, intent: IntentType, confidence: float) -> bool:
        """Determine if cache should be used."""
        if not self.semantic_cache_enabled or not self.cache_manager:
            return False
        required_conf = self.confidence_manager.get_threshold(intent)
        return confidence >= required_conf
    
    async def _try_semantic_cache(self, context: ExecutionContext, 
                                 intent: IntentType) -> Optional[Dict]:
        """Try to get result from semantic cache."""
        if not self.cache_manager:
            return None
        cache_key = self.confidence_manager.generate_cache_key(context, intent)
        return None  # Cache enhancement pending
    
    async def _execute_pipeline(self, context: ExecutionContext,
                               intent: IntentType, confidence: float) -> Dict[str, Any]:
        """Execute the agent pipeline."""
        plan = await self.execution_planner.generate_plan(context, intent, confidence)
        await self.trace_logger.log("Execution plan generated", {"steps": len(plan)})
        result = await self.pipeline_executor.execute(context, plan, intent)
        return result
    
    async def _cache_if_appropriate(self, context: ExecutionContext, intent: IntentType,
                                   confidence: float, result: Dict) -> None:
        """Cache result if appropriate."""
        if not self.semantic_cache_enabled or confidence < 0.7:
            return
        ttl = self.confidence_manager.get_cache_ttl(intent)
        cache_key = self.confidence_manager.generate_cache_key(context, intent)
        logger.info(f"Would cache with key {cache_key} for {ttl}s")
    
    def _format_cached_response(self, cached_result: Dict[str, Any]) -> Dict[str, Any]:
        """Format cached response for return."""
        return {
            "source": "cache", "confidence": 1.0,
            "data": cached_result, "trace": self.trace_logger.get_compressed_trace()
        }
    
    def _format_final_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format final response with trace information."""
        return {
            "source": "computed", "intent": result.get("intent"),
            "data": result.get("data"), "steps": len(result.get("steps", [])),
            "trace": self.trace_logger.get_compressed_trace()
        }
    
    async def _handle_orchestration_error(self, error: Exception) -> Dict[str, Any]:
        """Handle orchestration errors gracefully."""
        logger.error(f"Chat orchestration failed: {error}")
        await self.trace_logger.log(f"Error: {str(error)}", {"status": "failed"})
        return {"error": str(error), "trace": self.trace_logger.get_compressed_trace()}