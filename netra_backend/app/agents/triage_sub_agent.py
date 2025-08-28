"""Modernized TriageSubAgent with BaseExecutionInterface (<300 lines).

Modern implementation extending BaseExecutionInterface with:
- Standardized execution patterns  
- Integrated reliability management
- Comprehensive error handling
- Performance monitoring
- Circuit breaker protection

Business Value: First contact for ALL users - CRITICAL revenue impact.
BVJ: ALL segments | Customer Experience | +25% reduction in triage failures
"""

import time
from typing import Any, Dict, Optional

from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.agents.base.circuit_breaker import (
    CircuitBreakerConfig as ModernCircuitConfig,
)
from netra_backend.app.core.unified_error_handler import agent_error_handler as ExecutionErrorHandler
from netra_backend.app.agents.base.executor import BaseExecutionEngine

# Modern Base Components
from netra_backend.app.agents.base.interface import (
    BaseExecutionInterface,
    ExecutionContext,
    ExecutionResult,
    ExecutionStatus,
    WebSocketManagerProtocol,
)
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.agents.base.reliability_manager import ReliabilityManager
from netra_backend.app.agents.config import agent_config
from netra_backend.app.agents.input_validation import validate_agent_input
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.triage_sub_agent.core import TriageCore

# Import from modular structure  
from netra_backend.app.agents.triage_sub_agent.models import TriageResult
from netra_backend.app.agents.triage_sub_agent.processing import (
    TriageProcessor,
    WebSocketHandler,
)
from netra_backend.app.core.reliability import (
    CircuitBreakerConfig,
    RetryConfig,
    get_reliability_wrapper,
)
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.schemas.registry import DeepAgentState
from netra_backend.app.schemas.shared_types import RetryConfig as ModernRetryConfig

logger = central_logger.get_logger(__name__)


class TriageSubAgent(BaseSubAgent, BaseExecutionInterface):
    """Modernized triage agent with BaseExecutionInterface compliance."""
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher,
                 redis_manager: Optional[RedisManager] = None,
                 websocket_manager: Optional[WebSocketManagerProtocol] = None,
                 reliability_manager: Optional[ReliabilityManager] = None):
        self._init_base_agents(llm_manager, websocket_manager, tool_dispatcher, redis_manager)
        self._init_modern_execution_engine(reliability_manager)
        self._init_processing_components(llm_manager)
    
    def _init_base_agents(self, llm_manager: LLMManager, websocket_manager: Optional[WebSocketManagerProtocol],
                         tool_dispatcher: ToolDispatcher, redis_manager: Optional[RedisManager]) -> None:
        """Initialize base agent components."""
        super().__init__(llm_manager, name="TriageSubAgent", description="Enhanced triage agent with modern execution.")
        BaseExecutionInterface.__init__(self, "TriageSubAgent", websocket_manager)
        self._setup_core_properties(tool_dispatcher, redis_manager)
        
    def _setup_core_properties(self, tool_dispatcher: ToolDispatcher, redis_manager: Optional[RedisManager]) -> None:
        """Setup core properties."""
        self.tool_dispatcher = tool_dispatcher
        self.redis_manager = redis_manager
        self.cache_ttl = 3600
        self.max_retries = 3
        self.triage_core = TriageCore(redis_manager)
        self._init_legacy_reliability()
        
    def _init_legacy_reliability(self) -> None:
        """Initialize legacy reliability for backward compatibility."""
        circuit_config = CircuitBreakerConfig(
            failure_threshold=agent_config.failure_threshold,
            recovery_timeout=agent_config.timeout.default_timeout,
            name="TriageSubAgent"
        )
        retry_config = RetryConfig(
            max_retries=agent_config.retry.max_retries,
            base_delay=agent_config.retry.base_delay,
            max_delay=agent_config.retry.max_delay
        )
        self.reliability = get_reliability_wrapper("TriageSubAgent", circuit_config, retry_config)
        
    def _init_modern_execution_engine(self, reliability_manager: Optional[ReliabilityManager]) -> None:
        """Initialize modern execution engine."""
        if not reliability_manager:
            reliability_manager = self._create_modern_reliability_manager()
        monitor = ExecutionMonitor(max_history_size=1000)
        self.execution_engine = BaseExecutionEngine(reliability_manager, monitor)
        self.execution_monitor = monitor
        self.execution_error_handler = ExecutionErrorHandler()
        self.modern_reliability = reliability_manager
        
    def _create_modern_reliability_manager(self) -> ReliabilityManager:
        """Create modern reliability manager."""
        circuit_config = ModernCircuitConfig(
            name="TriageSubAgent",
            failure_threshold=agent_config.failure_threshold,
            recovery_timeout=agent_config.timeout.default_timeout
        )
        retry_config = ModernRetryConfig(
            max_retries=agent_config.retry.max_retries,
            base_delay=agent_config.retry.base_delay,
            max_delay=agent_config.retry.max_delay
        )
        return ReliabilityManager(circuit_config, retry_config)
        
    def _init_processing_components(self, llm_manager: LLMManager) -> None:
        """Initialize processing components."""
        self.processor = TriageProcessor(self.triage_core, llm_manager)
        self.websocket_handler = WebSocketHandler(self._send_update)

    # BaseExecutionInterface implementation
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions for triage."""
        if not context.state.user_request:
            self.logger.warning(f"No user request provided for triage in run_id: {context.run_id}")
            return False
        validation = self.triage_core.validator.validate_request(context.state.user_request)
        if not validation.is_valid:
            self._set_validation_error_result(context.state, context.run_id, validation)
            return False
        return True
        
    def _set_validation_error_result(self, state: DeepAgentState, run_id: str, validation) -> None:
        """Set validation error result."""
        self.logger.error(f"Invalid request for run_id {run_id}: {validation.validation_errors}")
        state.triage_result = TriageResult(category="Validation Error", confidence_score=0.0, validation_status=validation)
        
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute core triage logic with modern patterns."""
        start_time = time.time()
        await self._send_processing_update(context.run_id, context.stream_updates)
        triage_result = await self._get_or_compute_triage_result(context.state, context.run_id, start_time)
        return await self._finalize_triage_result(context.state, context.run_id, context.stream_updates, triage_result)
        
    async def _send_processing_update(self, run_id: str, stream_updates: bool) -> None:
        """Send processing status update."""
        if stream_updates:
            await self._send_update(run_id, {"status": "processing", "message": "Analyzing user request with enhanced categorization..."})
            
    async def _get_or_compute_triage_result(self, state: DeepAgentState, run_id: str, start_time: float):
        """Get cached result or compute new one."""
        request_hash = self.triage_core.generate_request_hash(state.user_request)
        cached_result = await self.triage_core.get_cached_result(request_hash)
        if cached_result:
            cached_result["metadata"]["cache_hit"] = True
            cached_result["metadata"]["triage_duration_ms"] = int((time.time() - start_time) * 1000)
            return cached_result
        triage_result = await self.processor.process_with_llm(state, run_id, start_time)
        await self.triage_core.cache_result(request_hash, triage_result)
        return triage_result
        
    async def _finalize_triage_result(self, state: DeepAgentState, run_id: str, stream_updates: bool, triage_result):
        """Finalize and send triage result."""
        triage_result = self.processor.enrich_triage_result(triage_result, state.user_request)
        state.triage_result = triage_result
        self.processor.log_performance_metrics(run_id, triage_result)
        if stream_updates:
            await self.websocket_handler.send_final_update(run_id, triage_result)
        return triage_result

    # Modern execution method using BaseExecutionEngine
    async def execute_modern(self, state: DeepAgentState, run_id: str, 
                           stream_updates: bool = False) -> ExecutionResult:
        """Execute using modern BaseExecutionEngine patterns."""
        context = ExecutionContext(
            run_id=run_id, agent_name="TriageSubAgent", state=state, stream_updates=stream_updates,
            thread_id=getattr(state, 'chat_thread_id', None), user_id=getattr(state, 'user_id', None),
            start_time=time.time(), correlation_id=getattr(self, 'correlation_id', None)
        )
        return await self.execution_engine.execute(self, context)
        
    # Legacy execute method for backward compatibility
    @validate_agent_input('TriageSubAgent')
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute the enhanced triage logic with structured generation"""
        await self.reliability.execute_safely(
            lambda: self._execute_triage_main(state, run_id, stream_updates),
            "execute_triage",
            fallback=lambda: self._execute_triage_fallback(state, run_id, stream_updates),
            timeout=agent_config.timeout.default_timeout
        )
    
    async def _execute_triage_main(self, state: DeepAgentState, run_id: str, stream_updates: bool):
        """Main triage execution logic."""
        start_time = time.time()
        await self._send_processing_update(run_id, stream_updates)
        triage_result = await self._get_or_compute_triage_result(state, run_id, start_time)
        return await self._finalize_triage_result(state, run_id, stream_updates, triage_result)
    
    async def _execute_triage_fallback(self, state: DeepAgentState, run_id: str, stream_updates: bool):
        """Fallback triage when main operation fails"""
        logger.warning(f"Using fallback triage for run_id: {run_id}")
        fallback_result = self.triage_core.create_fallback_result(state.user_request)
        triage_result = fallback_result.model_dump()
        triage_result["metadata"] = {"fallback_used": True, "triage_duration_ms": 100, "cache_hit": False}
        state.triage_result = triage_result
        if stream_updates:
            await self._send_update(run_id, {"status": "completed_with_fallback", "message": "Triage completed with fallback method", "result": triage_result})
        return triage_result

    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if we have a user request to triage"""
        return bool(state.user_request)

    async def cleanup(self, state: DeepAgentState, run_id: str) -> None:
        """Cleanup after execution"""
        await super().cleanup(state, run_id)
        if state.triage_result and isinstance(state.triage_result, dict):
            metadata = state.triage_result.get("metadata", {})
            if metadata:
                self.logger.debug(f"Triage metrics for run_id {run_id}: {metadata}")
    
    def get_health_status(self) -> dict:
        """Get comprehensive agent health status"""
        legacy_health = self.reliability.get_health_status()
        modern_health = self.execution_engine.get_health_status()
        monitor_health = self.execution_monitor.get_health_status()
        
        return {
            "legacy_reliability": legacy_health,
            "modern_execution": modern_health,
            "monitoring": monitor_health,
            "overall_status": self._determine_overall_health_status(legacy_health, modern_health)
        }
    
    def get_circuit_breaker_status(self) -> dict:
        """Get circuit breaker status"""
        return self.reliability.circuit_breaker.get_status()
        
    def _determine_overall_health_status(self, legacy_health: Dict[str, Any], modern_health: Dict[str, Any]) -> str:
        """Determine overall health status from components."""
        legacy_status = legacy_health.get("overall_health", "unknown")
        modern_status = modern_health.get("monitor", {}).get("status", "unknown")
        return "healthy" if legacy_status == "healthy" and modern_status == "healthy" else "degraded"

    # Compact delegate methods to triage core
    def _validate_request(self, request: str): return self.triage_core.validator.validate_request(request)
    def _extract_entities_from_request(self, request: str): return self.triage_core.entity_extractor.extract_entities(request)
    def _determine_intent(self, request: str): return self.triage_core.intent_detector.detect_intent(request)
    def _recommend_tools(self, category: str, entities): return self.triage_core.tool_recommender.recommend_tools(category, entities)
    def _fallback_categorization(self, request: str): return self.triage_core.create_fallback_result(request)
    def _extract_and_validate_json(self, response: str): return self.triage_core.extract_and_validate_json(response)
    def _generate_request_hash(self, request: str): return self.triage_core.generate_request_hash(request)
    
    # Modern execution monitoring helpers (compact)
    def get_execution_metrics(self) -> Dict[str, Any]: return self.execution_monitor.get_agent_performance_stats("TriageSubAgent")
    def reset_execution_metrics(self) -> None: self.execution_monitor.reset_metrics("TriageSubAgent")
    def get_modern_reliability_status(self) -> Dict[str, Any]: return self.modern_reliability.get_health_status()

    # Send update method for WebSocket communication
    async def _send_update(self, run_id: str, update: Dict[str, Any]) -> None:
        """Send update via WebSocket."""
        try:
            if hasattr(self, 'websocket_manager') and self.websocket_manager:
                await self.websocket_manager.send_agent_update(run_id, "TriageSubAgent", update)
        except Exception as e:
            logger.debug(f"Failed to send WebSocket update: {e}")