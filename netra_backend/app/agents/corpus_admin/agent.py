"""
Modernized Corpus Admin Agent with BaseExecutionInterface pattern (<300 lines).

Business Value: Standardized execution patterns for corpus administration,
improved reliability, and comprehensive monitoring.
"""

import time
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from netra_backend.app.websocket_core import UnifiedWebSocketManager as WebSocketManager

from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.agents.base.circuit_breaker import CircuitBreakerConfig
from netra_backend.app.agents.base.errors import ValidationError
from netra_backend.app.agents.base.executor import BaseExecutionEngine
from netra_backend.app.agents.utils import extract_thread_id

# Modern execution pattern imports
from netra_backend.app.agents.base.interface import (
    BaseExecutionInterface, ExecutionContext, ExecutionResult, ExecutionStatus, WebSocketManagerProtocol
)
from netra_backend.app.core.unified_error_handler import agent_error_handler as ExecutionErrorHandler
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.agents.base.reliability_manager import ReliabilityManager
from netra_backend.app.agents.corpus_admin.models import (
    CorpusMetadata,
    CorpusOperation,
    CorpusOperationResult,
    CorpusType,
)
from netra_backend.app.agents.corpus_admin.operations import CorpusOperationHandler
from netra_backend.app.agents.corpus_admin.parsers import CorpusRequestParser
from netra_backend.app.agents.corpus_admin.validators import CorpusApprovalValidator
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.llm.observability import log_agent_communication
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.shared_types import RetryConfig

logger = central_logger.get_logger(__name__)


class CorpusAdminSubAgent(BaseSubAgent):
    """Modernized corpus admin agent with standardized execution patterns."""
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher,
                 websocket_manager: Optional['WebSocketManager'] = None):
        self._init_base_agents(llm_manager, websocket_manager)
        self._initialize_components(tool_dispatcher, llm_manager)
        self._init_modern_execution_infrastructure()
    
    def _init_base_agents(self, llm_manager: LLMManager, websocket_manager: Optional['WebSocketManager']) -> None:
        """Initialize base agent components."""
        BaseSubAgent.__init__(self, llm_manager, name="CorpusAdminSubAgent",
                            description="Agent specialized in corpus management and administration")
        # Store agent name for BaseExecutionInterface compatibility
        self.agent_name = "CorpusAdminSubAgent"
        self.websocket_manager = websocket_manager
    
    def _initialize_components(self, tool_dispatcher: ToolDispatcher, llm_manager: LLMManager) -> None:
        """Initialize agent components"""
        self.tool_dispatcher = tool_dispatcher
        self.parser = CorpusRequestParser(llm_manager)
        self.validator = CorpusApprovalValidator()
        self.operations = CorpusOperationHandler(tool_dispatcher)
    
    def _init_modern_execution_infrastructure(self) -> None:
        """Initialize modern execution infrastructure."""
        self.monitor = ExecutionMonitor()
        self.reliability_manager = self._create_reliability_manager()
        self.execution_engine = BaseExecutionEngine(self.reliability_manager, self.monitor)
        self.error_handler = ExecutionErrorHandler
    
    def _create_reliability_manager(self) -> ReliabilityManager:
        """Create reliability manager with corpus admin configuration."""
        circuit_config = CircuitBreakerConfig(
            name="corpus_admin", failure_threshold=3, recovery_timeout=30
        )
        retry_config = RetryConfig(max_retries=3, base_delay=1.0, max_delay=10.0)
        return ReliabilityManager(circuit_config, retry_config)
    
    async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:
        """Check if conditions are met for corpus administration"""
        if self._is_admin_mode_request(state) or self._has_corpus_keywords(state):
            return True
        
        logger.info(f"Corpus administration not required for run_id: {run_id}")
        return False
    
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions for corpus administration."""
        await self._validate_state_requirements(context.state)
        await self._validate_execution_resources(context)
        await self._validate_corpus_admin_dependencies()
        return True
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute core corpus administration logic."""
        self.monitor.start_operation(f"corpus_admin_execution_{context.run_id}")
        await self.send_status_update(context, "executing", "Starting corpus administration...")
        
        result = await self._execute_corpus_administration_workflow(context)
        
        self.monitor.complete_operation(f"corpus_admin_execution_{context.run_id}")
        await self.send_status_update(context, "completed", "Corpus administration completed")
        return result
    
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Modernized execute using BaseExecutionEngine for backward compatibility."""
        log_agent_communication("Supervisor", "CorpusAdminSubAgent", run_id, "execute_request")
        context = self._create_execution_context(state, run_id, stream_updates)
        
        try:
            result = await self._execute_with_reliability_manager(context)
            await self._handle_execution_result(result, context)
        except Exception as e:
            await self._handle_execution_exception(e, context, state, run_id, stream_updates)
    
    def _create_execution_context(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> ExecutionContext:
        """Create execution context for modern pattern."""
        return ExecutionContext(
            run_id=run_id, agent_name=self.name, state=state,
            stream_updates=stream_updates, thread_id=extract_thread_id(state, run_id),
            user_id=getattr(state, 'user_id', 'default_user')
        )
    
    async def _execute_with_reliability_manager(self, context: ExecutionContext):
        """Execute with modern pattern using reliability manager."""
        # Create async wrapper to avoid coroutine warning
        async def execute_wrapper():
            return await self.execution_engine.execute(self, context)
        
        return await self.reliability_manager.execute_with_reliability(
            context, execute_wrapper
        )
    
    async def _handle_execution_result(self, result, context: ExecutionContext) -> None:
        """Handle result with error handler."""
        if not result.success:
            await self.error_handler.handle_execution_error(result.error, context)
    
    async def _handle_execution_exception(
        self, e: Exception, context: ExecutionContext, state: DeepAgentState, run_id: str, stream_updates: bool
    ) -> None:
        """Handle execution exception with error handler and fallback."""
        await self.error_handler.handle_execution_error(e, context)
        logger.error(f"Modern execution failed, falling back to legacy: {e}")
        await self._execute_legacy_workflow(state, run_id, stream_updates)
    
    async def _execute_with_error_handling(
        self, state: DeepAgentState, run_id: str, stream_updates: bool, start_time: float
    ) -> None:
        """Execute with error handling wrapper"""
        try:
            await self._execute_corpus_operation_workflow(state, run_id, stream_updates, start_time)
        except Exception as e:
            await self._handle_execution_error(e, state, run_id, stream_updates)
            raise
    
    async def _execute_corpus_operation_workflow(
        self, state: DeepAgentState, run_id: str, stream_updates: bool, start_time: float
    ) -> None:
        """Execute the complete corpus operation workflow."""
        await self._send_initial_update(run_id, stream_updates)
        operation_request = await self.parser.parse_operation_request(state.user_request)
        await self._process_operation_with_approval(operation_request, state, run_id, stream_updates, start_time)
        log_agent_communication("CorpusAdminSubAgent", "Supervisor", run_id, "execute_response")
    
    async def _process_operation_with_approval(
        self, operation_request, state: DeepAgentState, run_id: str, stream_updates: bool, start_time: float
    ) -> None:
        """Process operation with approval check"""
        approval_required = await self._handle_approval_check(operation_request, state, run_id, stream_updates)
        if not approval_required:
            await self._complete_corpus_operation(operation_request, state, run_id, stream_updates, start_time)
    
    async def _complete_corpus_operation(
        self, operation_request, state: DeepAgentState, run_id: str, stream_updates: bool, start_time: float
    ) -> None:
        """Complete the corpus operation execution."""
        await self._send_processing_update(operation_request, run_id, stream_updates)
        result = await self.operations.execute_operation(operation_request, run_id, stream_updates)
        
        await self._finalize_operation_result(result, state, run_id, stream_updates, start_time)
    
    async def _finalize_operation_result(
        self, result, state: DeepAgentState, run_id: str, stream_updates: bool, start_time: float
    ) -> None:
        """Finalize operation result and send updates"""
        state.corpus_admin_result = result.model_dump()
        await self._send_completion_update(result, run_id, stream_updates, start_time)
        self._log_completion(result, run_id)
    
    async def _validate_state_requirements(self, state: DeepAgentState) -> None:
        """Validate required state attributes."""
        if not hasattr(state, 'user_request') or not state.user_request:
            raise ValidationError("Missing required user_request in state")
    
    async def _validate_execution_resources(self, context: ExecutionContext) -> None:
        """Validate execution resources are available."""
        if not self.parser or not self.operations:
            raise ValidationError("Corpus admin components not initialized")
    
    async def _validate_corpus_admin_dependencies(self) -> None:
        """Validate corpus admin dependencies are healthy."""
        if not self.reliability_manager.get_health_status().get('overall_health') == 'healthy':
            logger.warning("Corpus admin dependencies in degraded state")
    
    async def _execute_corpus_administration_workflow(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute corpus administration workflow with monitoring."""
        updated_state = await self._run_corpus_admin_workflow(context.state, context.run_id, context.stream_updates)
        return {"corpus_admin_result": "completed", "updated_state": updated_state}
    
    async def _run_corpus_admin_workflow(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> DeepAgentState:
        """Run corpus admin workflow using legacy methods."""
        start_time = time.time()
        await self._execute_corpus_operation_workflow(state, run_id, stream_updates, start_time)
        return state
    
    async def _execute_legacy_workflow(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Legacy execution workflow for backward compatibility."""
        start_time = time.time()
        await self._execute_with_error_handling(state, run_id, stream_updates, start_time)
    
    async def cleanup(self, state: DeepAgentState, run_id: str) -> None:
        """Cleanup after execution"""
        await super().cleanup(state, run_id)
        self._log_final_metrics(state)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status from modern execution infrastructure."""
        status = {
            "agent_health": "healthy",
            "monitor": self.monitor.get_health_status(),
            "error_handler": self.error_handler.get_health_status()
        }
        if self.reliability_manager:
            status["reliability"] = self.reliability_manager.get_health_status()
        return status
    
    async def _handle_execution_error(self, e: Exception, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Handle execution error with proper error handling."""
        logger.error(f"Corpus admin execution error: {e}")
        # Store error in state for supervisor handling
        state.corpus_admin_error = str(e)
    
    async def _handle_approval_check(
        self, operation_request, state: DeepAgentState, run_id: str, stream_updates: bool
    ) -> bool:
        """Handle approval check for corpus operation"""
        return await self.validator.validate_approval_required(
            operation_request, state, run_id, stream_updates
        )
    
    async def _send_initial_update(self, run_id: str, stream_updates: bool) -> None:
        """Send initial status update via WebSocket."""
        # Implementation moved to BaseExecutionInterface
        pass
    
    async def _send_processing_update(self, operation_request, run_id: str, stream_updates: bool) -> None:
        """Send processing status update via WebSocket."""
        # Implementation moved to BaseExecutionInterface
        pass
    
    async def _send_completion_update(self, result, run_id: str, stream_updates: bool, start_time: float) -> None:
        """Send completion status update via WebSocket."""
        # Implementation moved to BaseExecutionInterface
        pass
    
    def _log_completion(self, result, run_id: str) -> None:
        """Log operation completion."""
        logger.info(f"Corpus operation completed for run_id {run_id}: "
                   f"operation={result.operation.value}, "
                   f"success={result.success}, "
                   f"affected={result.affected_documents}")
    
    def _log_final_metrics(self, state: DeepAgentState) -> None:
        """Log final metrics."""
        if self._has_valid_result(state):
            result = state.corpus_admin_result
            metrics_message = self._build_metrics_message(result)
            logger.info(metrics_message)
    
    def _has_valid_result(self, state: DeepAgentState) -> bool:
        """Check if state has valid corpus admin result."""
        return hasattr(state, 'corpus_admin_result') and bool(state.corpus_admin_result)
    
    def _build_metrics_message(self, result: dict) -> str:
        """Build metrics message for logging."""
        operation = result.get('operation')
        corpus_name = self._get_corpus_name(result)
        affected = result.get('affected_documents')
        return f"Corpus operation completed: operation={operation}, corpus={corpus_name}, affected={affected}"
    
    def _get_corpus_name(self, result: dict) -> str:
        """Get corpus name from result."""
        return result.get('corpus_metadata', {}).get('corpus_name')
    
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
        return "corpus" in category.lower() or "admin" in category.lower() or is_admin
    
    def _has_corpus_keywords(self, state: DeepAgentState) -> bool:
        """Check if user request contains corpus keywords."""
        if not state.user_request:
            return False
        
        corpus_keywords = ["corpus", "knowledge base", "documentation", "reference data", "embeddings"]
        request_lower = state.user_request.lower()
        return any(keyword in request_lower for keyword in corpus_keywords)
