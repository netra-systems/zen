"""Corpus operation execution module for CorpusAdminSubAgent."""

import time
from app.agents.state import DeepAgentState
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class CorpusOperationExecutor:
    """Handles corpus operation execution workflows."""
    
    def __init__(self, parser, operations):
        self.parser = parser
        self.operations = operations
    
    async def execute_corpus_operation_workflow(
        self, state: DeepAgentState, run_id: str, stream_updates: bool, start_time: float,
        approval_manager, update_manager
    ) -> None:
        """Execute the complete corpus operation workflow."""
        await update_manager.send_initial_update(run_id, stream_updates)
        operation_request = await self._parse_operation_request(state)
        await self._process_operation_with_approval(
            operation_request, state, run_id, stream_updates, start_time, approval_manager, update_manager
        )
    
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