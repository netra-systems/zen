"""Base error handler interface and common functionality.

Provides the foundation for all error handlers in the system.
Ensures consistent error processing patterns across domains.
"""

import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union

from app.logging_config import central_logger
from app.core.error_codes import ErrorSeverity
from app.schemas.core_enums import ErrorCategory
from app.schemas.shared_types import ErrorContext
from app.core.exceptions_agent import AgentError

logger = central_logger.get_logger(__name__)


class BaseErrorHandler(ABC):
    """Abstract base class for all error handlers."""
    
    def __init__(self, max_history: int = 100):
        """Initialize base error handler."""
        self.error_history: List[AgentError] = []
        self.max_history = max_history
        self._error_metrics = self._init_error_metrics()
    
    def _init_error_metrics(self) -> Dict[str, int]:
        """Initialize error metrics tracking."""
        return {
            'total_errors': 0,
            'recovery_attempts': 0,
            'recovery_successes': 0,
            'fallback_uses': 0
        }
    
    @abstractmethod
    async def handle_error(
        self, 
        error: Exception, 
        context: ErrorContext,
        **kwargs
    ) -> Any:
        """Handle error with domain-specific logic."""
        pass
    
    def _store_error(self, error: AgentError) -> None:
        """Store error in history with size management."""
        self.error_history.append(error)
        self._update_error_metrics()
        self._manage_history_size()
    
    def _update_error_metrics(self) -> None:
        """Update error metrics tracking."""
        self._error_metrics['total_errors'] += 1
    
    def _manage_history_size(self) -> None:
        """Keep error history within size limits."""
        if len(self.error_history) > self.max_history:
            self.error_history = self.error_history[-self.max_history:]
    
    def _log_error(self, error: AgentError) -> None:
        """Log error with appropriate severity level."""
        context = error.context
        operation_name = getattr(context, 'operation_name', 'unknown')
        log_message = f"{context.agent_name}.{operation_name}: {error.message}"
        
        severity_map = {
            ErrorSeverity.CRITICAL: logger.critical,
            ErrorSeverity.HIGH: logger.error,
            ErrorSeverity.MEDIUM: logger.warning,
            ErrorSeverity.LOW: logger.info
        }
        
        log_func = severity_map.get(error.severity, logger.info)
        log_func(log_message)
    
    def get_error_stats(self) -> Dict[str, Union[int, float]]:
        """Get comprehensive error statistics."""
        return {
            **self._error_metrics,
            'success_rate': self._calculate_success_rate(),
            'recent_errors': len(self._get_recent_errors()),
            'last_updated': time.time()
        }
    
    def _calculate_success_rate(self) -> float:
        """Calculate error recovery success rate."""
        total = self._error_metrics['recovery_attempts']
        successes = self._error_metrics['recovery_successes']
        return (successes / total * 100) if total > 0 else 0.0
    
    def _get_recent_errors(self) -> List[AgentError]:
        """Get errors from the last hour."""
        cutoff_time = time.time() - 3600
        return [e for e in self.error_history if time.time() - e.timestamp < 3600]