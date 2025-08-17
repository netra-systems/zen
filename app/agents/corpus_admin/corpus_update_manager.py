"""Corpus update management module for CorpusAdminSubAgent."""

import time
from typing import Dict, Any
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class CorpusUpdateManager:
    """Handles corpus operation WebSocket updates and notifications."""
    
    def __init__(self, websocket_manager, operations):
        self.websocket_manager = websocket_manager
        self.operations = operations
    
    async def send_initial_update(self, run_id: str, stream_updates: bool) -> None:
        """Send initial processing update."""
        if stream_updates:
            update_data = self._build_initial_update_data()
            await self._send_update(run_id, update_data)
    
    def _build_initial_update_data(self) -> dict:
        """Build initial update data."""
        return {
            "status": "starting",
            "message": "📚 Initializing corpus administration...",
            "agent": "CorpusAdminSubAgent"
        }
    
    async def send_processing_update(self, operation_request, run_id: str, stream_updates: bool) -> None:
        """Send processing update."""
        if stream_updates:
            update_data = self._build_processing_update_data(operation_request)
            await self._send_update(run_id, update_data)
    
    def _build_processing_update_data(self, operation_request) -> dict:
        """Build processing update data."""
        return {
            "status": "processing",
            "message": self._create_processing_message(operation_request),
            "operation": operation_request.operation.value
        }
    
    def _create_processing_message(self, operation_request) -> str:
        """Create processing message."""
        operation_name = operation_request.operation.value
        corpus_name = operation_request.corpus_metadata.corpus_name
        return f"🔄 Executing {operation_name} operation on corpus '{corpus_name}'..."
    
    async def send_completion_update(
        self, 
        result, 
        run_id: str, 
        stream_updates: bool, 
        start_time: float
    ) -> None:
        """Send completion update."""
        if stream_updates:
            await self._send_completion_update_data(result, run_id, start_time)
    
    async def _send_completion_update_data(self, result, run_id: str, start_time: float) -> None:
        """Send completion update data."""
        update_data = await self._build_completion_update_data(result, start_time)
        await self._send_update(run_id, update_data)
    
    async def _build_completion_update_data(self, result, start_time: float) -> dict:
        """Build completion update data."""
        duration = self._calculate_duration(start_time)
        status_emoji = self._get_status_emoji(result)
        statistics = await self._get_corpus_statistics()
        return self._create_completion_update_dict(result, duration, status_emoji, statistics)
    
    def _calculate_duration(self, start_time: float) -> int:
        """Calculate operation duration in milliseconds."""
        return int((time.time() - start_time) * 1000)
    
    def _get_status_emoji(self, result) -> str:
        """Get status emoji based on result."""
        return "✅" if result.success else "❌"
    
    async def _get_corpus_statistics(self):
        """Get corpus statistics."""
        return await self.operations.get_corpus_statistics()
    
    def _create_completion_update_dict(
        self, result, duration: int, status_emoji: str, statistics
    ) -> dict:
        """Create completion update dictionary."""
        base_data = self._create_update_base_data(result, duration, status_emoji)
        return {**base_data, "statistics": statistics}
    
    def _create_update_base_data(self, result, duration: int, status_emoji: str) -> dict:
        """Create base update data."""
        return {
            "status": self._get_completion_status(result),
            "message": f"{status_emoji} Corpus operation completed in {duration}ms",
            "result": result.model_dump()
        }
    
    def _get_completion_status(self, result) -> str:
        """Get completion status."""
        return "completed" if result.success else "failed"
    
    async def send_approval_update(
        self, 
        approval_message: str, 
        operation_request, 
        run_id: str, 
        stream_updates: bool
    ) -> None:
        """Send approval required update."""
        if stream_updates:
            await self._send_approval_update_data(approval_message, operation_request, run_id)
    
    async def _send_approval_update_data(
        self, approval_message: str, operation_request, run_id: str
    ) -> None:
        """Send approval update data."""
        update_data = self._build_approval_update_data(approval_message, operation_request)
        await self._send_update(run_id, update_data)
    
    def _build_approval_update_data(self, approval_message: str, operation_request) -> dict:
        """Build approval update data."""
        base_update = self._get_base_approval_update(approval_message)
        action_data = self._get_approval_action_data(operation_request)
        return {**base_update, **action_data}
    
    def _get_base_approval_update(self, approval_message: str) -> dict:
        """Get base approval update data."""
        return {
            "status": "approval_required",
            "message": approval_message,
            "requires_user_action": True
        }
    
    def _get_approval_action_data(self, operation_request) -> dict:
        """Get approval action data."""
        return {
            "action_type": "approve_corpus_operation",
            "operation_details": operation_request.model_dump()
        }
    
    async def send_error_update(self, run_id: str, error: Exception) -> None:
        """Send error update via WebSocket."""
        update_data = self._build_error_update_data(error)
        await self._send_update(run_id, update_data)
    
    def _build_error_update_data(self, error: Exception) -> dict:
        """Build error update data."""
        return {
            "status": "error",
            "message": f"❌ Corpus operation failed: {str(error)}",
            "error": str(error)
        }
    
    async def _send_update(self, run_id: str, update: Dict[str, Any]) -> None:
        """Send update via WebSocket manager."""
        if self.websocket_manager:
            try:
                await self._send_websocket_update(run_id, update)
            except Exception as e:
                self._log_websocket_error(e)
    
    async def _send_websocket_update(self, run_id: str, update: Dict[str, Any]) -> None:
        """Send WebSocket update."""
        await self.websocket_manager.send_agent_update(run_id, "corpus_admin", update)
    
    def _log_websocket_error(self, error: Exception) -> None:
        """Log WebSocket error."""
        logger.error(f"Failed to send WebSocket update: {error}")