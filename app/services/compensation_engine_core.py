"""Core compensation engine for executing compensation actions.

Provides centralized compensation execution with handler registration and management.
All functions strictly adhere to 25-line limit.
"""

import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.core.error_recovery import RecoveryContext
from app.logging_config import central_logger

from .compensation_models import (
    BaseCompensationHandler,
    CompensationAction,
    CompensationState
)
from .compensation_handlers_core import (
    DatabaseCompensationHandler,
    FileSystemCompensationHandler,
    CacheCompensationHandler,
    ExternalServiceCompensationHandler
)

logger = central_logger.get_logger(__name__)


class CompensationEngine:
    """Engine for executing compensation actions."""
    
    def __init__(self):
        """Initialize compensation engine."""
        self.handlers: List[BaseCompensationHandler] = []
        self.active_compensations: Dict[str, CompensationAction] = {}
        self._register_default_handlers()
    
    def _register_default_handlers(self) -> None:
        """Register default compensation handlers."""
        self.handlers = [
            DatabaseCompensationHandler(),
            FileSystemCompensationHandler(),
            CacheCompensationHandler(),
            ExternalServiceCompensationHandler(),
        ]
        self.handlers.sort(key=lambda h: h.get_priority())
    
    def register_handler(self, handler: BaseCompensationHandler) -> None:
        """Register a new compensation handler."""
        self.handlers.append(handler)
        self.handlers.sort(key=lambda h: h.get_priority())
    
    async def _find_compatible_handler(self, context: RecoveryContext) -> Optional[BaseCompensationHandler]:
        """Find handler that can compensate the given context."""
        for handler in self.handlers:
            if await handler.can_compensate(context):
                return handler
        return None
    
    def _create_compensation_action(
        self,
        action_id: str,
        operation_id: str,
        context: RecoveryContext,
        compensation_data: Dict[str, Any],
        handler: BaseCompensationHandler
    ) -> CompensationAction:
        """Create compensation action with handler."""
        return CompensationAction(
            action_id=action_id,
            operation_id=operation_id,
            action_type=context.operation_type.value,
            compensation_data=compensation_data,
            handler=handler.execute_compensation,
            metadata={
                'context': context,
                'handler_class': type(handler).__name__
            }
        )
    
    async def create_compensation_action(
        self,
        operation_id: str,
        context: RecoveryContext,
        compensation_data: Dict[str, Any]
    ) -> str:
        """Create a new compensation action."""
        action_id = str(uuid.uuid4())
        handler = await self._find_compatible_handler(context)
        
        if not handler:
            logger.warning(f"No compensation handler found for operation: {operation_id}")
            return action_id
        
        action = self._create_compensation_action(
            action_id, operation_id, context, compensation_data, handler
        )
        self.active_compensations[action_id] = action
        logger.debug(f"Created compensation action: {action_id}")
        return action_id
    
    def _update_action_state_executing(self, action: CompensationAction) -> None:
        """Update action state to executing."""
        action.state = CompensationState.EXECUTING
        action.executed_at = datetime.now()
    
    def _update_action_state_completed(self, action: CompensationAction) -> None:
        """Update action state to completed."""
        action.state = CompensationState.COMPLETED
        logger.info(f"Compensation completed: {action.action_id}")
    
    def _update_action_state_failed(self, action: CompensationAction, error: str) -> None:
        """Update action state to failed."""
        action.state = CompensationState.FAILED
        action.error = error
        logger.error(f"Compensation failed: {action.action_id}: {error}")
    
    async def _execute_compensation_action(self, action: CompensationAction) -> bool:
        """Execute compensation action with handler."""
        context = action.metadata.get('context')
        return await action.handler(action, context)
    
    async def execute_compensation(self, action_id: str) -> bool:
        """Execute compensation action by ID."""
        action = self.active_compensations.get(action_id)
        if not action:
            logger.error(f"Compensation action not found: {action_id}")
            return False
        
        self._update_action_state_executing(action)
        
        try:
            success = await self._execute_compensation_action(action)
            if success:
                self._update_action_state_completed(action)
            else:
                self._update_action_state_failed(action, "Handler returned False")
            return success
        except Exception as e:
            self._update_action_state_failed(action, str(e))
            return False
    
    def get_compensation_status(self, action_id: str) -> Optional[Dict[str, Any]]:
        """Get status of compensation action."""
        action = self.active_compensations.get(action_id)
        if not action:
            return None
        
        return {
            'action_id': action_id,
            'operation_id': action.operation_id,
            'action_type': action.action_type,
            'state': action.state.value,
            'created_at': action.created_at.isoformat(),
            'executed_at': action.executed_at.isoformat() if action.executed_at else None,
            'error': action.error
        }
    
    def _cleanup_completed_actions(self) -> int:
        """Clean up completed compensation actions."""
        completed_ids = [
            action_id for action_id, action in self.active_compensations.items()
            if action.state in [CompensationState.COMPLETED, CompensationState.FAILED]
        ]
        for action_id in completed_ids:
            del self.active_compensations[action_id]
        return len(completed_ids)
    
    def cleanup_compensations(self) -> int:
        """Clean up completed compensations and return count."""
        cleaned_count = self._cleanup_completed_actions()
        if cleaned_count > 0:
            logger.debug(f"Cleaned up {cleaned_count} completed compensation actions")
        return cleaned_count
    
    def get_active_compensations(self) -> List[Dict[str, Any]]:
        """Get list of all active compensation actions."""
        return [
            self.get_compensation_status(action_id)
            for action_id in self.active_compensations.keys()
        ]