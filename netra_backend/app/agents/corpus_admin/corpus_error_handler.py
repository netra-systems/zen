"""Corpus error handling module for CorpusAdminSubAgent."""

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.models import CorpusOperationResult, CorpusOperation, CorpusMetadata, CorpusType
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class CorpusErrorHandler:
    """Handles corpus operation errors and recovery."""
    
    def __init__(self):
        pass
    
    async def handle_execution_error(
        self, 
        error: Exception, 
        state: DeepAgentState, 
        run_id: str, 
        stream_updates: bool,
        update_manager
    ) -> None:
        """Handle execution errors."""
        self._log_execution_error(error, run_id)
        await self._process_error_result(error, state, run_id, stream_updates, update_manager)
    
    def _log_execution_error(self, error: Exception, run_id: str) -> None:
        """Log execution error."""
        logger.error(f"Corpus operation failed for run_id {run_id}: {error}")
    
    async def _process_error_result(
        self, error: Exception, state: DeepAgentState, run_id: str, stream_updates: bool, update_manager
    ) -> None:
        """Process error result."""
        await self._store_error_result(error, state)
        await self._send_error_notification(run_id, error, stream_updates, update_manager)
    
    async def _store_error_result(self, error: Exception, state: DeepAgentState) -> None:
        """Store error result in state."""
        error_result = self._create_error_result(error)
        state.corpus_admin_result = error_result.model_dump()
    
    async def _send_error_notification(self, run_id: str, error: Exception, stream_updates: bool, update_manager) -> None:
        """Send error notification if streaming enabled."""
        if stream_updates:
            await update_manager.send_error_update(run_id, error)
    
    def _create_error_result(self, error: Exception) -> CorpusOperationResult:
        """Create error result for failed operation."""
        error_metadata = self._create_error_metadata()
        return CorpusOperationResult(
            success=False,
            operation=CorpusOperation.SEARCH,
            corpus_metadata=error_metadata,
            errors=[str(error)]
        )
    
    def _create_error_metadata(self) -> CorpusMetadata:
        """Create error corpus metadata."""
        return CorpusMetadata(
            corpus_name="unknown",
            corpus_type=CorpusType.REFERENCE_DATA
        )