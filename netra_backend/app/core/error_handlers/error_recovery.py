"""Error recovery strategies and execution.

Provides unified error recovery mechanisms including retry logic,
fallback strategies, and compensation actions.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Optional

from netra_backend.app.core.error_codes import ErrorSeverity
from netra_backend.app.core.error_handlers.error_classification import (
    ErrorClassification,
)
from netra_backend.app.core.exceptions_agent import AgentError
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.core_enums import ErrorCategory
from netra_backend.app.schemas.shared_types import ErrorContext

logger = central_logger.get_logger(__name__)


@dataclass
class RecoveryResult:
    """Result of error recovery attempt."""
    success: bool
    data: Optional[Any] = None
    strategy_used: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ErrorRecoveryStrategy:
    """Unified error recovery strategy execution."""
    
    # Strategy constants
    RETRY = "retry"
    ABORT = "abort"
    FALLBACK = "fallback"
    
    def __init__(self):
        """Initialize recovery strategy with configuration."""
        self._retry_config = self._build_retry_config()
        self._delay_config = self._build_delay_config()
    
    def _build_retry_config(self) -> Dict[ErrorCategory, int]:
        """Build retry configuration by error category."""
        return {
            ErrorCategory.NETWORK: 3,
            ErrorCategory.TIMEOUT: 2,
            ErrorCategory.WEBSOCKET: 3,
            ErrorCategory.RESOURCE: 1,
            ErrorCategory.DATABASE: 2,
            ErrorCategory.PROCESSING: 1
        }
    
    def _build_delay_config(self) -> Dict[ErrorCategory, float]:
        """Build delay configuration by error category."""
        return {
            ErrorCategory.NETWORK: 1.0,
            ErrorCategory.TIMEOUT: 2.0,
            ErrorCategory.WEBSOCKET: 0.5,
            ErrorCategory.RESOURCE: 5.0,
            ErrorCategory.DATABASE: 1.5,
            ErrorCategory.PROCESSING: 0.5
        }
    
    def should_retry(self, error: AgentError) -> bool:
        """Determine if error should be retried."""
        if not error.recoverable:
            return False
        
        # Check context for explicit max_retries limit first
        context = getattr(error, 'context', None)
        if context and hasattr(context, 'max_retries') and hasattr(context, 'retry_count'):
            return context.retry_count < context.max_retries
        
        # Fallback to category-based config
        max_retries = self._retry_config.get(error.category, 0)
        current_retries = getattr(context, 'retry_count', 0) if context else 0
        
        return current_retries < max_retries
    
    def _get_instance_recovery_delay(self, error: AgentError, retry_count: int) -> float:
        """Calculate recovery delay with exponential backoff (instance method)."""
        base_delay = self._delay_config.get(error.category, 1.0)
        return base_delay * (2 ** retry_count)
    
    async def execute_recovery(
        self,
        error: AgentError,
        context: ErrorContext,
        fallback_operation: Optional[Callable[[], Awaitable[Any]]] = None
    ) -> RecoveryResult:
        """Execute recovery strategy for error."""
        if self.should_retry(error):
            return await self._attempt_retry(error, context)
        
        if fallback_operation:
            return await self._execute_fallback(fallback_operation, context)
        
        return RecoveryResult(success=False, strategy_used="no_strategy")
    
    async def _attempt_retry(
        self, 
        error: AgentError, 
        context: ErrorContext
    ) -> RecoveryResult:
        """Attempt retry with delay."""
        delay = self._get_instance_recovery_delay(error, context.retry_count)
        logger.info("Retrying after {:.2f}s (attempt {})", delay, context.retry_count + 1)
        
        await asyncio.sleep(delay)
        
        return RecoveryResult(
            success=True,
            strategy_used="retry",
            metadata={"delay": delay, "retry_count": context.retry_count + 1}
        )
    
    async def _execute_fallback(
        self,
        fallback_operation: Callable[[], Awaitable[Any]],
        context: ErrorContext
    ) -> RecoveryResult:
        """Execute fallback operation."""
        try:
            result = await fallback_operation()
            logger.info("Fallback operation succeeded for {}", context.agent_name)
            
            return RecoveryResult(
                success=True,
                data=result,
                strategy_used="fallback"
            )
        except Exception as fallback_error:
            logger.error("Fallback operation failed: {}", fallback_error)
            return RecoveryResult(
                success=False,
                strategy_used="fallback_failed",
                metadata={"fallback_error": str(fallback_error)}
            )


class RecoveryCoordinator:
    """Coordinates recovery efforts across different error types."""
    
    def __init__(self):
        """Initialize recovery coordinator."""
        self.strategy = ErrorRecoveryStrategy()
        self._fallback_cache: Dict[str, Any] = {}
    
    async def coordinate_recovery(
        self,
        error: AgentError,
        context: ErrorContext,
        classification: ErrorClassification,
        fallback_operation: Optional[Callable] = None
    ) -> RecoveryResult:
        """Coordinate recovery based on error classification."""
        if classification.requires_fallback and not fallback_operation:
            fallback_operation = self._get_cached_fallback(context)
        
        recovery_result = await self.strategy.execute_recovery(
            error, context, fallback_operation
        )
        
        self._update_recovery_metrics(recovery_result)
        return recovery_result
    
    def _get_cached_fallback(self, context: ErrorContext) -> Optional[Callable]:
        """Get cached fallback data for context."""
        cache_key = f"{context.agent_name}_{getattr(context, 'operation_name', 'default')}"
        cached_data = self._fallback_cache.get(cache_key)
        
        if cached_data:
            return lambda: cached_data
        
        return None
    
    def cache_fallback_data(self, context: ErrorContext, data: Any) -> None:
        """Cache data for future fallback use."""
        cache_key = f"{context.agent_name}_{getattr(context, 'operation_name', 'default')}"
        self._fallback_cache[cache_key] = {
            "data": data,
            "timestamp": time.time(),
            "context": context
        }
    
    def _update_recovery_metrics(self, result: RecoveryResult) -> None:
        """Update recovery metrics based on result."""
        # This would be implemented to update monitoring metrics
        pass


# Static methods monkey-patched to ErrorRecoveryStrategy for backward compatibility with tests
def _static_get_recovery_delay(error: Any, attempt: int = 0) -> float:
    """Static method to get recovery delay with exponential backoff and jitter."""
    import random
    
    # Base delay configuration by error type
    base_delays = {
        'NetworkError': 1.0,
        'DatabaseError': 1.5,
        'ValidationError': 0.5,
        'AgentError': 1.0,
    }
    
    error_type = type(error).__name__
    base_delay = base_delays.get(error_type, 1.0)
    
    # Exponential backoff with jitter
    delay = base_delay * (2 ** attempt)
    
    # Add jitter (±25%)
    jitter = random.uniform(0.75, 1.25)
    delay *= jitter
    
    # Cap maximum delay at 30 seconds
    return min(delay, 30.0)


def _static_should_retry(error: Any, attempt: int = 0) -> bool:
    """Static method to determine if error should be retried."""
    error_type = type(error).__name__
    
    # Non-retryable error types
    non_retryable = ['ValidationError', 'AgentValidationError']
    if error_type in non_retryable:
        return False
    
    # Critical errors should not be retried
    if hasattr(error, 'severity') and error.severity == ErrorSeverity.CRITICAL:
        return False
    
    # Check context for explicit max_retries limit first (this is the key fix)
    if hasattr(error, 'context') and error.context:
        context = error.context
        if hasattr(context, 'max_retries') and hasattr(context, 'retry_count'):
            return context.retry_count < context.max_retries
    
    # Fallback to max attempt limits by error type
    max_attempts = {
        'NetworkError': 3,
        'DatabaseError': 2,
        'AgentError': 2,
    }
    
    max_for_type = max_attempts.get(error_type, 1)
    return attempt < max_for_type


def _static_get_strategy(error: Any) -> str:
    """Static method to get recovery strategy for error."""
    error_type = type(error).__name__
    
    # Strategy mapping by error type
    if error_type in ['ValidationError', 'AgentValidationError']:
        return ErrorRecoveryStrategy.ABORT
    
    if hasattr(error, 'severity') and error.severity == ErrorSeverity.CRITICAL:
        return ErrorRecoveryStrategy.ABORT
    
    if error_type in ['NetworkError', 'DatabaseError']:
        return ErrorRecoveryStrategy.RETRY
    
    # Default strategy
    return ErrorRecoveryStrategy.RETRY


# Monkey patch static methods to ErrorRecoveryStrategy
ErrorRecoveryStrategy.get_recovery_delay = staticmethod(_static_get_recovery_delay)
ErrorRecoveryStrategy.should_retry = staticmethod(_static_should_retry)
ErrorRecoveryStrategy.get_strategy = staticmethod(_static_get_strategy)