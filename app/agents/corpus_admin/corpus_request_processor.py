"""Modernized Corpus Request Processor with BaseExecutionInterface pattern (<300 lines).

Business Value: Standardized execution patterns for corpus request processing,
improved reliability, and comprehensive monitoring.
"""

from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.ws_manager import WebSocketManager

from app.agents.state import DeepAgentState
from app.logging_config import central_logger

# Modern execution pattern imports
from app.agents.base.interface import (
    BaseExecutionInterface, ExecutionContext, ExecutionResult, 
    ExecutionStatus, WebSocketManagerProtocol
)
from app.agents.base.executor import BaseExecutionEngine
from app.agents.base.monitoring import ExecutionMonitor
from app.agents.base.reliability_manager import ReliabilityManager
from app.agents.base.errors import ExecutionErrorHandler, ValidationError
from app.agents.base.circuit_breaker import CircuitBreakerConfig
from app.schemas.shared_types import RetryConfig

logger = central_logger.get_logger(__name__)


class CorpusRequestProcessor(BaseExecutionInterface):
    """Modernized corpus request processor with standardized execution patterns."""
    
    def __init__(self, websocket_manager: Optional['WebSocketManager'] = None):
        super().__init__("CorpusRequestProcessor", websocket_manager)
        self.corpus_keywords = self._initialize_corpus_keywords()
        self._init_modern_execution_infrastructure()
    
    def _init_modern_execution_infrastructure(self) -> None:
        """Initialize modern execution infrastructure."""
        self.monitor = ExecutionMonitor()
        self.reliability_manager = self._create_reliability_manager()
        self.execution_engine = BaseExecutionEngine(self.reliability_manager, self.monitor)
        self.error_handler = ExecutionErrorHandler()
    
    def _create_reliability_manager(self) -> ReliabilityManager:
        """Create reliability manager with corpus request configuration."""
        circuit_config = CircuitBreakerConfig(
            name="corpus_requests", failure_threshold=3, recovery_timeout=30
        )
        retry_config = RetryConfig(max_retries=3, base_delay=1.0, max_delay=10.0)
        return ReliabilityManager(circuit_config, retry_config)
    
    def _initialize_corpus_keywords(self) -> List[str]:
        """Initialize corpus-related keywords."""
        return ["corpus", "knowledge base", "documentation", "reference data", "embeddings"]
    
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions for corpus request processing."""
        await self._validate_state_requirements(context.state)
        await self._validate_execution_resources(context)
        await self._validate_corpus_request_dependencies()
        return True
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute core corpus request processing logic."""
        self.monitor.start_operation(f"corpus_request_processing_{context.run_id}")
        await self.send_status_update(context, "executing", "Processing corpus request...")
        
        result = await self._execute_request_processing_workflow(context)
        
        self.monitor.complete_operation(f"corpus_request_processing_{context.run_id}")
        await self.send_status_update(context, "completed", "Corpus request processing completed")
        return result
    
    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if conditions are met for corpus administration (legacy compatibility)."""
        context = self._create_execution_context(state, run_id)
        
        try:
            result = await self._execute_modern_entry_check(context)
            return self._process_entry_check_result(result, run_id)
        except Exception as e:
            logger.error(f"Modern execution failed, falling back to legacy: {e}")
            return await self._check_entry_conditions_legacy(state, run_id)
    
    def _create_execution_context(self, state: DeepAgentState, run_id: str) -> ExecutionContext:
        """Create execution context for modern pattern."""
        return ExecutionContext(
            run_id=run_id, agent_name=self.agent_name, state=state,
            stream_updates=False, thread_id=getattr(state, 'chat_thread_id', run_id),
            user_id=getattr(state, 'user_id', 'default_user')
        )
    
    async def _execute_modern_entry_check(self, context: ExecutionContext):
        """Execute with modern pattern using reliability manager."""
        return await self.reliability_manager.execute_with_reliability(
            context, lambda: self.execution_engine.execute(self, context)
        )
    
    def _process_entry_check_result(self, result, run_id: str) -> bool:
        """Process entry check result and return conditions met status."""
        if result.success and result.result:
            conditions_met = result.result.get('conditions_met', False)
            if conditions_met:
                return True
        logger.info(f"Corpus administration not required for run_id: {run_id}")
        return False
    
    async def _check_entry_conditions_legacy(self, state: DeepAgentState, run_id: str) -> bool:
        """Legacy entry conditions check for backward compatibility."""
        if self._is_admin_mode_request(state) or self._has_corpus_keywords(state):
            return True
        
        logger.info(f"Corpus administration not required for run_id: {run_id}")
        return False
    
    def _is_admin_mode_request(self, state: DeepAgentState) -> bool:
        """Check if request is admin mode or corpus-related."""
        triage_result = state.triage_result or {}
        
        if isinstance(triage_result, dict):
            return self._check_admin_indicators(triage_result)
        return False
    
    def _check_admin_indicators(self, triage_result: dict) -> bool:
        """Check if triage result indicates admin or corpus operation."""
        category = triage_result.get("category", "")
        is_admin = triage_result.get("is_admin_mode", False)
        return self._has_corpus_category(category) or self._has_admin_category(category) or is_admin
    
    def _has_corpus_category(self, category: str) -> bool:
        """Check if category contains corpus keywords."""
        return "corpus" in category.lower()
    
    def _has_admin_category(self, category: str) -> bool:
        """Check if category contains admin keywords."""
        return "admin" in category.lower()
    
    def _has_corpus_keywords(self, state: DeepAgentState) -> bool:
        """Check if user request contains corpus keywords."""
        if not state.user_request:
            return False
        return self._request_contains_keywords(state.user_request)
    
    def _request_contains_keywords(self, user_request: str) -> bool:
        """Check if request contains any corpus keywords."""
        request_lower = user_request.lower()
        return any(keyword in request_lower for keyword in self.corpus_keywords)
    
    async def _validate_state_requirements(self, state: DeepAgentState) -> None:
        """Validate required state attributes."""
        if not hasattr(state, 'user_request') or not state.user_request:
            raise ValidationError("Missing required user_request in state")
    
    async def _validate_execution_resources(self, context: ExecutionContext) -> None:
        """Validate execution resources are available."""
        if not self.corpus_keywords:
            raise ValidationError("Corpus keywords not initialized")
    
    async def _validate_corpus_request_dependencies(self) -> None:
        """Validate corpus request dependencies are healthy."""
        if not self.reliability_manager.get_health_status().get('overall_health') == 'healthy':
            logger.warning("Corpus request dependencies in degraded state")
    
    async def _execute_request_processing_workflow(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute request processing workflow with monitoring."""
        conditions_met = await self._evaluate_entry_conditions(context.state, context.run_id)
        return {
            "conditions_met": conditions_met,
            "processor_result": "completed",
            "admin_mode_detected": self._is_admin_mode_request(context.state),
            "corpus_keywords_found": self._has_corpus_keywords(context.state)
        }
    
    async def _evaluate_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Evaluate entry conditions for corpus administration."""
        return self._is_admin_mode_request(state) or self._has_corpus_keywords(state)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status from modern execution infrastructure."""
        status = self._build_base_health_status()
        self._add_reliability_status(status)
        return status
    
    def _build_base_health_status(self) -> Dict[str, Any]:
        """Build base health status information."""
        return {
            "processor_health": "healthy",
            "monitor": self.monitor.get_health_status(),
            "error_handler": self.error_handler.get_health_status(),
            "corpus_keywords_count": len(self.corpus_keywords)
        }
    
    def _add_reliability_status(self, status: Dict[str, Any]) -> None:
        """Add reliability status to health information."""
        if self.reliability_manager:
            status["reliability"] = self.reliability_manager.get_health_status()