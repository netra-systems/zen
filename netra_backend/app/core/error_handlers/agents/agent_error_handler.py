"""Centralized agent error handler.

Consolidates agent-specific error handling logic from the original
AgentErrorHandler with improved modularity and reusability.
"""

import time
from typing import Dict, Optional, Callable, Awaitable, List, Union, Any

from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.error_codes import ErrorSeverity
from netra_backend.app.schemas.core_enums import ErrorCategory
from netra_backend.app.schemas.shared_types import ErrorContext
from netra_backend.app.core.exceptions_agent import AgentError
from netra_backend.app.base_error_handler import BaseErrorHandler
from netra_backend.app.error_classification import ErrorClassifier
from netra_backend.app.error_recovery import RecoveryCoordinator

logger = central_logger.get_logger(__name__)


class AgentErrorHandler(BaseErrorHandler):
    """Centralized error handler for all agent operations."""
    
    def __init__(self, max_history: int = 100):
        """Initialize agent error handler."""
        super().__init__(max_history)
        self.classifier = ErrorClassifier()
        self.recovery_coordinator = RecoveryCoordinator()
    
    async def handle_error(
        self,
        error: Exception,
        context: ErrorContext,
        fallback_operation: Optional[Callable[[], Awaitable[Any]]] = None
    ) -> Any:
        """Handle error with appropriate recovery strategy."""
        agent_error = self._process_error(error, context)
        return await self._attempt_error_recovery(
            agent_error, context, fallback_operation
        )
    
    def _process_error(self, error: Exception, context: ErrorContext) -> AgentError:
        """Process and log error for recovery."""
        agent_error = self._convert_to_agent_error(error, context)
        self._log_error(agent_error)
        self._store_error(agent_error)
        return agent_error
    
    async def _attempt_error_recovery(
        self, 
        agent_error: AgentError, 
        context: ErrorContext, 
        fallback_operation
    ) -> Any:
        """Attempt recovery through retry or fallback."""
        classification = self.classifier.classify_error(agent_error)
        
        recovery_result = await self.recovery_coordinator.coordinate_recovery(
            agent_error, context, classification, fallback_operation
        )
        
        if recovery_result.success:
            return recovery_result.data
        
        # If recovery failed, raise the original error
        raise agent_error
    
    def _convert_to_agent_error(
        self, 
        error: Exception, 
        context: ErrorContext
    ) -> AgentError:
        """Convert generic exception to AgentError."""
        if isinstance(error, AgentError):
            return self._update_existing_agent_error(error, context)
        return self._create_new_agent_error(error, context)
    
    def _update_existing_agent_error(self, error: AgentError, context: ErrorContext) -> AgentError:
        """Update existing AgentError with new context."""
        error.context = context
        return error
    
    def _create_new_agent_error(self, error: Exception, context: ErrorContext) -> AgentError:
        """Create new AgentError from generic exception."""
        classification = self.classifier.classify_error(error)
        
        return AgentError(
            message=str(error),
            severity=classification.severity,
            category=classification.category,
            context=context,
            recoverable=classification.is_retryable
        )
    
    def cache_fallback_data(self, context: ErrorContext, data: Any) -> None:
        """Cache data for future fallback use."""
        self.recovery_coordinator.cache_fallback_data(context, data)
    
    def get_comprehensive_stats(self) -> Dict[str, Union[int, Dict[str, int], List[Dict[str, Union[str, float]]]]]:
        """Get comprehensive error statistics."""
        if not self.error_history:
            return {"total_errors": 0}
        
        recent_errors = self._get_recent_errors()
        category_counts, severity_counts = self._count_error_types(recent_errors)
        
        return {
            "total_errors": len(self.error_history),
            "recent_errors": len(recent_errors),
            "error_categories": category_counts,
            "error_severities": severity_counts,
            "last_error": self._get_last_error_info(),
            **self.get_error_stats()
        }
    
    def _count_error_types(self, errors: List[AgentError]) -> tuple:
        """Count errors by category and severity."""
        category_counts: Dict[str, int] = {}
        severity_counts: Dict[str, int] = {}
        
        for error in errors:
            self._increment_count(category_counts, error.category.value)
            self._increment_count(severity_counts, error.severity.value)
        
        return category_counts, severity_counts
    
    def _increment_count(self, count_dict: Dict[str, int], key: str) -> None:
        """Increment count for a key in dictionary."""
        count_dict[key] = count_dict.get(key, 0) + 1
    
    def _get_last_error_info(self) -> Optional[Dict[str, Union[str, float]]]:
        """Get information about the last error."""
        if not self.error_history:
            return None
        
        last_error = self.error_history[-1]
        return {
            "message": last_error.message,
            "category": last_error.category.value,
            "severity": last_error.severity.value,
            "timestamp": last_error.timestamp
        }


# Global instance for backward compatibility
global_agent_error_handler = AgentErrorHandler()