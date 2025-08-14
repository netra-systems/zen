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
from app.agents.config import agent_config
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
from app.agents.triage_sub_agent.processing import TriageProcessor, WebSocketHandler

logger = central_logger.get_logger(__name__)


class TriageSubAgent(BaseSubAgent):
    """Enhanced triage agent with advanced categorization and caching"""
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher, redis_manager: Optional[RedisManager] = None):
        super().__init__(llm_manager, name="TriageSubAgent", description="Enhanced triage agent with advanced categorization and caching.")
        self.tool_dispatcher = tool_dispatcher
        self.triage_core = TriageCore(redis_manager)
        
        # Initialize processing modules
        self.processor = TriageProcessor(self.triage_core, llm_manager)
        self.websocket_handler = WebSocketHandler(self._send_update)
        
        # Initialize reliability wrapper
        self.reliability = get_reliability_wrapper(
            "TriageSubAgent",
            CircuitBreakerConfig(
                failure_threshold=agent_config.failure_threshold,
                recovery_timeout=agent_config.timeout.default_timeout,
                name="TriageSubAgent"
            ),
            RetryConfig(
                max_retries=agent_config.retry.max_retries,
                base_delay=agent_config.retry.base_delay,
                max_delay=agent_config.retry.max_delay
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
                triage_result = await self.processor.process_with_llm(state, run_id, start_time)
                # Cache the result for future use
                await self.triage_core.cache_result(request_hash, triage_result)
            
            # Enrich result with additional analysis
            triage_result = self.processor.enrich_triage_result(triage_result, state.user_request)
            
            state.triage_result = triage_result
            
            # Log performance metrics
            self.processor.log_performance_metrics(run_id, triage_result)
            
            # Update with results
            if stream_updates:
                await self.websocket_handler.send_final_update(run_id, triage_result)
            
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
            timeout=agent_config.timeout.default_timeout
        )
    
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