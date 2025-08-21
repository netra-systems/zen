"""Error recovery strategies and execution.

Provides unified error recovery mechanisms including retry logic,
fallback strategies, and compensation actions.
"""

import asyncio
import time
from typing import Dict, Optional, Any, Callable, Awaitable
from dataclasses import dataclass

from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.error_codes import ErrorSeverity
from netra_backend.app.schemas.core_enums import ErrorCategory
from netra_backend.app.schemas.shared_types import ErrorContext
from netra_backend.app.core.exceptions_agent import AgentError
from netra_backend.app.core.error_handlers.error_classification import ErrorClassification

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
        
        max_retries = self._retry_config.get(error.category, 0)
        current_retries = getattr(error.context, 'retry_count', 0)
        
        return current_retries < max_retries
    
    def get_recovery_delay(self, error: AgentError, retry_count: int) -> float:
        """Calculate recovery delay with exponential backoff."""
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
        delay = self.get_recovery_delay(error, context.retry_count)
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