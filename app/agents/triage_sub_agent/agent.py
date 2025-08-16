"""Triage Sub Agent

Enhanced triage agent with advanced categorization and caching capabilities.
This module provides a clean interface that uses the modular structure for backward compatibility.
"""

from typing import Optional

from app.llm.llm_manager import LLMManager
from app.agents.base import BaseSubAgent
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.redis_manager import RedisManager
from app.logging_config import central_logger
from app.core.reliability import (
    get_reliability_wrapper, CircuitBreakerConfig, RetryConfig
)
from app.llm.fallback_handler import LLMFallbackHandler, FallbackConfig

# Import from modular structure
from app.agents.triage_sub_agent.core import TriageCore
from app.agents.triage_sub_agent.executor import TriageExecutor
from app.agents.triage_sub_agent.llm_processor import TriageLLMProcessor
from app.agents.triage_sub_agent.result_processor import TriageResultProcessor
from app.agents.triage_sub_agent.prompt_builder import TriagePromptBuilder

logger = central_logger.get_logger(__name__)


class TriageSubAgent(BaseSubAgent):
    """Enhanced triage agent with advanced categorization and caching"""
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher, redis_manager: Optional[RedisManager] = None):
        self._init_base_triage_agent(llm_manager)
        self._init_core_components(tool_dispatcher, redis_manager)
        self._init_reliability_system()
        self._init_fallback_handler()
        self._init_modular_components()
        
    def _init_base_triage_agent(self, llm_manager: LLMManager) -> None:
        """Initialize base agent with core parameters."""
        super().__init__(llm_manager, name="TriageSubAgent", description="Enhanced triage agent with advanced categorization and caching.")
    
    def _init_core_components(self, tool_dispatcher: ToolDispatcher, redis_manager: Optional[RedisManager]) -> None:
        """Initialize core triage components."""
        self.tool_dispatcher = tool_dispatcher
        self.redis_manager = redis_manager
        self.cache_ttl = 3600  # Expected by tests
        self.max_retries = 3   # Expected by tests
        self.triage_core = TriageCore(redis_manager)
    
    def _init_reliability_system(self) -> None:
        """Initialize reliability wrapper with circuit breaker and retry config."""
        circuit_config = CircuitBreakerConfig(
            failure_threshold=3, recovery_timeout=30.0, name="TriageSubAgent"
        )
        retry_config = RetryConfig(max_retries=2, base_delay=1.0, max_delay=10.0)
        self.reliability = get_reliability_wrapper("TriageSubAgent", circuit_config, retry_config)

    def _init_fallback_handler(self) -> None:
        """Initialize LLM fallback handler for triage operations."""
        fallback_config = self._create_fallback_config()
        self.llm_fallback_handler = LLMFallbackHandler(fallback_config)
    
    def _create_fallback_config(self) -> FallbackConfig:
        """Create fallback configuration."""
        return FallbackConfig(
            max_retries=2,
            base_delay=0.5,
            max_delay=8.0,
            timeout=25.0,
            use_circuit_breaker=True
        )
    
    def _init_modular_components(self) -> None:
        """Initialize modular components for delegation."""
        self.executor = TriageExecutor(self)
        self.llm_processor = TriageLLMProcessor(self)
        self.result_processor = TriageResultProcessor(self)
        self.prompt_builder = TriagePromptBuilder(self)

    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if we have a user request to triage."""
        return await self.executor.check_entry_conditions(state, run_id)

    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute enhanced triage with comprehensive fallback handling."""
        await self.executor.execute_triage_workflow(state, run_id, stream_updates)

    async def cleanup(self, state: DeepAgentState, run_id: str) -> None:
        """Cleanup after execution."""
        await super().cleanup(state, run_id)
        
        # Log final metrics if available
        if state.triage_result and isinstance(state.triage_result, dict):
            metadata = state.triage_result.get("metadata", {})
            if metadata:
                self.logger.debug(f"Triage metrics for run_id {run_id}: {metadata}")
    
    def get_health_status(self) -> dict:
        """Get agent health status."""
        return self.reliability.get_health_status()
    
    def get_circuit_breaker_status(self) -> dict:
        """Get circuit breaker status."""
        return self.reliability.circuit_breaker.get_status()
    
    # Delegation methods for backward compatibility
    def _validate_request(self, request: str):
        """Validate request - delegate to triage core validator."""
        return self.triage_core.validator.validate_request(request)
    
    def _extract_entities_from_request(self, request: str):
        """Extract entities from request - delegate to entity extractor."""
        return self.triage_core.entity_extractor.extract_entities(request)
    
    def _determine_intent(self, request: str):
        """Determine user intent - delegate to intent detector."""
        return self.triage_core.intent_detector.detect_intent(request)
    
    def _recommend_tools(self, category: str, entities):
        """Recommend tools - delegate to tool recommender."""
        return self.triage_core.tool_recommender.recommend_tools(category, entities)
    
    def _fallback_categorization(self, request: str):
        """Fallback categorization - delegate to triage core."""
        return self.triage_core.create_fallback_result(request)
    
    def _extract_and_validate_json(self, response: str):
        """Extract and validate JSON - delegate to triage core."""
        return self.triage_core.extract_and_validate_json(response)
    
    def _generate_request_hash(self, request: str):
        """Generate request hash - delegate to triage core."""
        return self.triage_core.generate_request_hash(request)
    
    # Additional backward compatibility methods (delegated to modules)
    def _build_enhanced_prompt(self, user_request: str) -> str:
        """Build enhanced prompt - delegate to prompt builder."""
        return self.prompt_builder.build_enhanced_prompt(user_request)
    
    def _enrich_triage_result(self, triage_result, user_request: str):
        """Enrich triage result - delegate to result processor."""
        return self.result_processor.enrich_triage_result(triage_result, user_request)
    
    def _ensure_triage_result(self, result):
        """Ensure triage result - delegate to result processor."""
        return self.result_processor._ensure_triage_result(result)
    
    def _get_main_categories(self) -> list:
        """Get main categories - delegate to prompt builder."""
        return self.prompt_builder._get_main_categories()
    
    def _format_category_list(self, categories: list) -> str:
        """Format category list - delegate to prompt builder."""
        return self.prompt_builder._format_category_list(categories)