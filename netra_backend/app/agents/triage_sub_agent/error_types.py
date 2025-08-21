"""Error type definitions for Triage Sub Agent operations."""

from typing import Any, Dict, List, Optional

from netra_backend.app.agents.error_handler import AgentError, ErrorContext
from netra_backend.app.core.error_codes import ErrorSeverity
from netra_backend.app.core.error_recovery import CompensationAction, RecoveryContext
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TriageError(AgentError):
    """Specific error type for triage operations."""
    
    def __init__(
        self,
        message: str,
        operation: str,
        user_input: Optional[str] = None,
        context: Optional[ErrorContext] = None
    ):
        """Initialize triage error with specific context."""
        super().__init__(
            message=message,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            recoverable=True
        )
        self.operation = operation
        self.user_input = user_input


class IntentDetectionError(TriageError):
    """Error when intent detection fails."""
    
    def __init__(self, user_input: str, context: Optional[ErrorContext] = None):
        """Initialize intent detection error."""
        super().__init__(
            message=f"Failed to detect intent from user input: {user_input[:100]}...",
            operation="intent_detection",
            user_input=user_input,
            context=context
        )


class EntityExtractionError(TriageError):
    """Error when entity extraction fails."""
    
    def __init__(self, entities: List[str], context: Optional[ErrorContext] = None):
        """Initialize entity extraction error."""
        super().__init__(
            message=f"Failed to extract entities: {', '.join(entities)}",
            operation="entity_extraction",
            context=context
        )
        self.failed_entities = entities


class ToolRecommendationError(TriageError):
    """Error when tool recommendation fails."""
    
    def __init__(self, intent: str, context: Optional[ErrorContext] = None):
        """Initialize tool recommendation error."""
        super().__init__(
            message=f"Failed to recommend tools for intent: {intent}",
            operation="tool_recommendation",
            context=context
        )
        self.intent = intent


class TriageCacheCompensation(CompensationAction):
    """Compensation action for triage cache operations."""
    
    def __init__(self, cache_manager):
        """Initialize with cache manager."""
        self.cache_manager = cache_manager
    
    async def execute(self, context: RecoveryContext) -> bool:
        """Execute cache compensation for triage operations."""
        try:
            cache_keys = context.metadata.get('triage_cache_keys', [])
            if cache_keys:
                await self.cache_manager.invalidate_keys(cache_keys)
                logger.info(f"Invalidated triage cache keys: {cache_keys}")
            return True
        except Exception as e:
            logger.error(f"Triage cache compensation failed: {e}")
            return False


class TriageStateCompensation(CompensationAction):
    """Compensation action for triage state operations."""
    
    def __init__(self, state_manager):
        """Initialize with state manager."""
        self.state_manager = state_manager
    
    async def execute(self, context: RecoveryContext) -> bool:
        """Execute state compensation for triage operations."""
        try:
            run_id = context.metadata.get('run_id')
            if run_id:
                await self.state_manager.rollback_state(run_id)
                logger.info(f"Rolled back triage state for run_id: {run_id}")
            return True
        except Exception as e:
            logger.error(f"Triage state compensation failed: {e}")
            return False