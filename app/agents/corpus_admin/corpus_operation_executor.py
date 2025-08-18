"""Modernized Corpus Operation Executor with BaseExecutionInterface pattern (<300 lines).

Business Value: Standardized execution patterns for corpus operations,
improved reliability, and comprehensive monitoring.
"""

import time
from typing import Dict, Any, Optional, TYPE_CHECKING

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


class CorpusOperationExecutor(BaseExecutionInterface):
    """Modernized corpus operation executor with standardized execution patterns."""
    
    def __init__(self, parser, operations, websocket_manager: Optional['WebSocketManager'] = None):
        super().__init__("CorpusOperationExecutor", websocket_manager)
        self.parser = parser
        self.operations = operations
        self._init_modern_execution_infrastructure()
    
    def _init_modern_execution_infrastructure(self) -> None:
        """Initialize modern execution infrastructure."""
        self.monitor = ExecutionMonitor()
        self.reliability_manager = self._create_reliability_manager()
        self.execution_engine = BaseExecutionEngine(self.reliability_manager, self.monitor)
        self.error_handler = ExecutionErrorHandler()
    
    def _create_reliability_manager(self) -> ReliabilityManager:
        """Create reliability manager with corpus operation configuration."""
        circuit_config = CircuitBreakerConfig(
            name="corpus_operations", failure_threshold=3, recovery_timeout=30
        )
        retry_config = RetryConfig(max_retries=3, base_delay=1.0, max_delay=10.0)
        return ReliabilityManager(circuit_config, retry_config)
    
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions for corpus operations."""
        await self._validate_state_requirements(context.state)
        await self._validate_execution_resources(context)
        await self._validate_corpus_operation_dependencies()
        return True
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute core corpus operation logic."""
        self.monitor.start_operation(f"corpus_operation_execution_{context.run_id}")
        await self.send_status_update(context, "executing", "Starting corpus operation...")
        
        result = await self._execute_modernized_workflow(context)
        
        self.monitor.complete_operation(f"corpus_operation_execution_{context.run_id}")
        await self.send_status_update(context, "completed", "Corpus operation completed")
        return result
    
    async def execute_corpus_operation_workflow(
        self, state: DeepAgentState, run_id: str, stream_updates: bool, start_time: float,
        approval_manager, update_manager
    ) -> None:
        """Execute the complete corpus operation workflow (legacy compatibility)."""
        context = self._create_workflow_context(state, run_id, stream_updates)
        
        try:
            result = await self._execute_with_reliability(context)
            await self._handle_workflow_result(result, context)
        except Exception as e:
            await self._handle_workflow_exception(e, context, state, run_id, stream_updates, start_time, approval_manager, update_manager)
    
    def _create_workflow_context(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> ExecutionContext:
        """Create execution context for workflow."""
        return ExecutionContext(
            run_id=run_id, agent_name=self.agent_name, state=state,
            stream_updates=stream_updates, thread_id=getattr(state, 'chat_thread_id', run_id),
            user_id=getattr(state, 'user_id', 'default_user')
        )
    
    async def _execute_with_reliability(self, context: ExecutionContext):
        """Execute with modern pattern using reliability manager."""
        return await self.reliability_manager.execute_with_reliability(
            context, lambda: self.execution_engine.execute(self, context)
        )
    
    async def _handle_workflow_result(self, result, context: ExecutionContext) -> None:
        """Handle workflow result with error handler."""
        if not result.success:
            await self.error_handler.handle_execution_error(result.error, context)
    
    async def _handle_workflow_exception(
        self, e: Exception, context: ExecutionContext, state: DeepAgentState, run_id: str, 
        stream_updates: bool, start_time: float, approval_manager, update_manager
    ) -> None:
        """Handle workflow exception with error handler and fallback."""
        await self.error_handler.handle_execution_error(str(e), context)
        logger.error(f"Modern execution failed, falling back to legacy: {e}")
        await self._execute_legacy_workflow(state, run_id, stream_updates, start_time, approval_manager, update_manager)
    
    async def _parse_operation_request(self, state: DeepAgentState):
        """Parse operation request from state."""
        return await self.parser.parse_operation_request(state.user_request)
    
    async def _process_operation_with_approval(
        self, operation_request, state: DeepAgentState, run_id: str, stream_updates: bool, start_time: float,
        approval_manager, update_manager
    ) -> None:
        """Process operation with approval check."""
        approval_required = await approval_manager.handle_approval_check(
            operation_request, state, run_id, stream_updates
        )
        if not approval_required:
            await self._complete_corpus_operation(
                operation_request, state, run_id, stream_updates, start_time, update_manager
            )
    
    async def _complete_corpus_operation(
        self, operation_request, state: DeepAgentState, run_id: str, stream_updates: bool, start_time: float,
        update_manager
    ) -> None:
        """Complete the corpus operation execution."""
        await update_manager.send_processing_update(operation_request, run_id, stream_updates)
        result = await self._execute_operation(operation_request, run_id, stream_updates)
        await self._finalize_operation_result(result, state, run_id, stream_updates, start_time, update_manager)
    
    async def _execute_operation(self, operation_request, run_id: str, stream_updates: bool):
        """Execute the corpus operation."""
        return await self.operations.execute_operation(operation_request, run_id, stream_updates)
    
    async def _finalize_operation_result(
        self, result, state: DeepAgentState, run_id: str, stream_updates: bool, start_time: float, update_manager
    ) -> None:
        """Finalize operation result and send updates."""
        self._store_result_in_state(result, state)
        await update_manager.send_completion_update(result, run_id, stream_updates, start_time)
        self._log_completion(result, run_id)
    
    def _store_result_in_state(self, result, state: DeepAgentState) -> None:
        """Store operation result in state."""
        state.corpus_admin_result = result.model_dump()
    
    def _log_completion(self, result, run_id: str) -> None:
        """Log operation completion."""
        logger.info(f"Corpus operation completed for run_id {run_id}: "
                   f"operation={result.operation.value}, "
                   f"success={result.success}, "
                   f"affected={result.affected_documents}")
    
    def log_final_metrics(self, state: DeepAgentState) -> None:
        """Log final metrics."""
        if self._has_valid_result(state):
            result = state.corpus_admin_result
            metrics_message = self._build_metrics_message(result)
            logger.info(metrics_message)
    
    def _has_valid_result(self, state: DeepAgentState) -> bool:
        """Check if state has valid corpus admin result."""
        return state.corpus_admin_result and isinstance(state.corpus_admin_result, dict)
    
    def _build_metrics_message(self, result: dict) -> str:
        """Build metrics message for logging."""
        operation = result.get('operation')
        corpus_name = self._get_corpus_name(result)
        affected = result.get('affected_documents')
        return f"Corpus operation completed: operation={operation}, corpus={corpus_name}, affected={affected}"
    
    def _get_corpus_name(self, result: dict) -> str:
        """Get corpus name from result."""
        return result.get('corpus_metadata', {}).get('corpus_name')
    
    async def _validate_state_requirements(self, state: DeepAgentState) -> None:
        """Validate required state attributes."""
        if not hasattr(state, 'user_request') or not state.user_request:
            raise ValidationError("Missing required user_request in state")
    
    async def _validate_execution_resources(self, context: ExecutionContext) -> None:
        """Validate execution resources are available."""
        if not self.parser or not self.operations:
            raise ValidationError("Corpus operation components not initialized")
    
    async def _validate_corpus_operation_dependencies(self) -> None:
        """Validate corpus operation dependencies are healthy."""
        if not self.reliability_manager.get_health_status().get('overall_health') == 'healthy':
            logger.warning("Corpus operation dependencies in degraded state")
    
    async def _execute_modernized_workflow(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute modernized corpus operation workflow."""
        operation_request = await self._parse_operation_request(context.state)
        result = await self._execute_operation(operation_request, context.run_id, context.stream_updates)
        updated_state = self._update_state_with_result(result, context.state)
        return {"corpus_operation_result": "completed", "updated_state": updated_state}
    
    def _update_state_with_result(self, result, state: DeepAgentState) -> DeepAgentState:
        """Update state with operation result."""
        state.corpus_admin_result = result.model_dump()
        return state
    
    async def _execute_legacy_workflow(self, state: DeepAgentState, run_id: str, stream_updates: bool,
                                     start_time: float, approval_manager, update_manager) -> None:
        """Legacy execution workflow for backward compatibility."""
        await update_manager.send_initial_update(run_id, stream_updates)
        operation_request = await self._parse_operation_request(state)
        await self._process_operation_with_approval(
            operation_request, state, run_id, stream_updates, start_time, approval_manager, update_manager
        )
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status from modern execution infrastructure."""
        status = {
            "executor_health": "healthy",
            "monitor": self.monitor.get_health_status(),
            "error_handler": self.error_handler.get_health_status()
        }
        if self.reliability_manager:
            status["reliability"] = self.reliability_manager.get_health_status()
        return status