"""
Base compensation handler and common functionality.
Provides the foundation for all compensation handler implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from netra_backend.app.core.error_recovery import RecoveryContext
from netra_backend.app.logging_config import central_logger
from netra_backend.app.compensation_types import CompensationAction, CompensationState
from netra_backend.app.compensation_helpers import (
    validate_required_keys,
    update_action_state_executing,
    update_action_state_completed,
    update_action_state_failed,
    log_preparation_failure,
    log_execution_failure,
    log_compensation_error,
    log_cleanup_error,
    build_error_context_dict,
    should_skip_retry
)

logger = central_logger.get_logger(__name__)


class BaseCompensationHandler(ABC):
    """Abstract base class for compensation handlers."""
    
    @abstractmethod
    async def can_compensate(self, context: RecoveryContext) -> bool:
        """Check if this handler can compensate the given operation."""
        pass
    
    @abstractmethod
    async def execute_compensation(
        self,
        action: CompensationAction,
        context: RecoveryContext
    ) -> bool:
        """Execute the compensation action."""
        pass
    
    @abstractmethod
    def get_priority(self) -> int:
        """Get handler priority (lower number = higher priority)."""
        pass
    
    def get_handler_type(self) -> str:
        """Get handler type identifier."""
        return self.__class__.__name__.replace('CompensationHandler', '').lower()
    
    def validate_compensation_data(
        self, 
        compensation_data: Dict[str, Any],
        required_keys: list[str]
    ) -> bool:
        """Validate compensation data contains required keys."""
        return validate_required_keys(compensation_data, required_keys)
    
    async def prepare_compensation(
        self,
        action: CompensationAction,
        context: RecoveryContext
    ) -> bool:
        """Prepare for compensation execution (optional override)."""
        # Default implementation - no preparation needed
        return True
    
    async def post_compensation(
        self,
        action: CompensationAction,
        context: RecoveryContext,
        success: bool
    ) -> None:
        """Post-compensation cleanup (optional override)."""
        # Default implementation - no cleanup needed
        pass
    
    async def _handle_preparation_failure(self, action: CompensationAction) -> bool:
        """Handle compensation preparation failure."""
        log_preparation_failure(action.action_id)
        update_action_state_failed(action, action.action_id, "Preparation failed")
        return False
    
    async def _handle_execution_result(self, action: CompensationAction, success: bool) -> None:
        """Handle compensation execution result."""
        if success:
            update_action_state_completed(action, action.action_id)
        else:
            update_action_state_failed(action, action.action_id, "Execution failed")
    
    async def _handle_execution_exception(self, action: CompensationAction, context: RecoveryContext, error: Exception) -> bool:
        """Handle compensation execution exception."""
        update_action_state_failed(action, action.action_id, str(error))
        log_compensation_error(action.action_id, error)
        
        try:
            await self.post_compensation(action, context, False)
        except Exception as cleanup_error:
            log_cleanup_error(cleanup_error)
        
        return False
    
    async def execute_with_lifecycle(
        self,
        action: CompensationAction,
        context: RecoveryContext
    ) -> bool:
        """Execute compensation with full lifecycle management."""
        try:
            update_action_state_executing(action)
            
            prepared = await self.prepare_compensation(action, context)
            if not prepared:
                return await self._handle_preparation_failure(action)
            
            success = await self.execute_compensation(action, context)
            await self._handle_execution_result(action, success)
            await self.post_compensation(action, context, success)
            return success
            
        except Exception as e:
            return await self._handle_execution_exception(action, context, e)
    
    def create_error_context(
        self,
        action: CompensationAction,
        error: Exception
    ) -> Dict[str, Any]:
        """Create error context for reporting."""
        return build_error_context_dict(action, error, self.get_handler_type())
    
    def should_retry(self, action: CompensationAction, error: Exception) -> bool:
        """Determine if compensation should be retried."""
        return not should_skip_retry(action, error)