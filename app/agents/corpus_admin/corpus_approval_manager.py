"""Corpus approval management module for CorpusAdminSubAgent."""

from app.agents.state import DeepAgentState
from .models import CorpusOperationResult
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class CorpusApprovalManager:
    """Handles corpus operation approval workflows."""
    
    def __init__(self, validator):
        self.validator = validator
    
    async def handle_approval_check(
        self, 
        operation_request, 
        state: DeepAgentState, 
        run_id: str, 
        stream_updates: bool,
        update_manager
    ) -> bool:
        """Handle approval requirements check."""
        requires_approval = await self._check_approval_requirements(operation_request, state)
        await self._process_approval_if_required(
            operation_request, state, run_id, stream_updates, requires_approval, update_manager
        )
        return requires_approval
    
    async def _check_approval_requirements(self, operation_request, state: DeepAgentState) -> bool:
        """Check if approval is required."""
        return await self.validator.check_approval_requirements(operation_request, state)
    
    async def _process_approval_if_required(
        self, operation_request, state: DeepAgentState, run_id: str, stream_updates: bool, 
        requires_approval: bool, update_manager
    ) -> None:
        """Process approval if required."""
        if requires_approval:
            await self._process_approval_requirement(operation_request, state, run_id, stream_updates, update_manager)
    
    async def _process_approval_requirement(
        self, operation_request, state: DeepAgentState, run_id: str, stream_updates: bool, update_manager
    ) -> None:
        """Process approval requirement workflow."""
        approval_message = self._generate_approval_message(operation_request)
        await self._store_approval_result(operation_request, approval_message, state)
        await update_manager.send_approval_update(approval_message, operation_request, run_id, stream_updates)
    
    def _generate_approval_message(self, operation_request) -> str:
        """Generate approval message."""
        return self.validator.generate_approval_message(operation_request)
    
    async def _store_approval_result(
        self, 
        operation_request, 
        approval_message: str, 
        state: DeepAgentState
    ) -> None:
        """Store approval result in state."""
        approval_result = self._create_approval_result(operation_request, approval_message)
        self._update_state_with_approval(state, approval_result)
    
    def _update_state_with_approval(self, state: DeepAgentState, approval_result) -> None:
        """Update state with approval result."""
        state.corpus_admin_result = approval_result.model_dump()
    
    def _create_approval_result(self, operation_request, approval_message: str) -> CorpusOperationResult:
        """Create approval result for pending operation."""
        approval_params = self._build_approval_result_params(operation_request, approval_message)
        return CorpusOperationResult(**approval_params)
    
    def _build_approval_result_params(self, operation_request, approval_message: str) -> dict:
        """Build parameters for approval result."""
        base_params = self._get_base_approval_params(operation_request)
        approval_params = self._get_approval_specific_params(approval_message)
        return {**base_params, **approval_params}
    
    def _get_base_approval_params(self, operation_request) -> dict:
        """Get base approval parameters."""
        return {
            "success": False,
            "operation": operation_request.operation,
            "corpus_metadata": operation_request.corpus_metadata
        }
    
    def _get_approval_specific_params(self, approval_message: str) -> dict:
        """Get approval-specific parameters."""
        return {
            "requires_approval": True,
            "approval_message": approval_message
        }