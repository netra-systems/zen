"""Execution-specific error handler.

Handles agent execution errors with specialized execution context
support and fallback strategies.
"""

import time
from typing import Dict, Any, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.core.error_handlers.base_error_handler import BaseErrorHandler
from netra_backend.app.core.error_handlers.error_classification import ErrorClassifier, ErrorClassification
from netra_backend.app.core.error_handlers.error_recovery import RecoveryCoordinator

logger = central_logger.get_logger(__name__)


class ExecutionErrorHandler(BaseErrorHandler):
    """Handles agent execution errors with fallback strategies."""
    
    def __init__(self, max_history: int = 100):
        """Initialize execution error handler."""
        super().__init__(max_history)
        self.classifier = ErrorClassifier()
        self.recovery_coordinator = RecoveryCoordinator()
        self._fallback_data_cache: Dict[str, Any] = {}
    
    async def handle_error(
        self, 
        error: Exception, 
        context: ExecutionContext,
        **kwargs
    ) -> ExecutionResult:
        """Handle execution error with appropriate strategy."""
        classification = self.classifier.classify_error(error)
        return await self._process_error_with_classification(error, context, classification)
    
    async def handle_execution_error(self, error: Exception, 
                                   context: ExecutionContext) -> ExecutionResult:
        """Handle execution error with appropriate strategy."""
        return await self.handle_error(error, context)
    
    async def _process_error_with_classification(self, error: Exception, 
                                               context: ExecutionContext, 
                                               classification: ErrorClassification) -> ExecutionResult:
        """Process error based on classification."""
        self._update_error_metrics()
        
        if classification.requires_fallback:
            return await self._execute_fallback_strategy(context, classification)
        
        return self._create_error_result(error, context, classification)
    
    async def _execute_fallback_strategy(self, context: ExecutionContext,
                                       classification: ErrorClassification) -> ExecutionResult:
        """Execute fallback strategy based on error type."""
        fallback_result = await self._try_cached_fallback(context)
        if fallback_result:
            return fallback_result
        
        return await self._generate_graceful_degradation(context, classification)
    
    async def _try_cached_fallback(self, context: ExecutionContext) -> Optional[ExecutionResult]:
        """Try to use cached data as fallback."""
        cache_key = self._build_cache_key(context)
        cached_data = self._fallback_data_cache.get(cache_key)
        
        if cached_data:
            return self._create_cached_result(cached_data)
        
        return None
    
    def _build_cache_key(self, context: ExecutionContext) -> str:
        """Build cache key from execution context."""
        operation_name = getattr(context, 'operation_name', context.run_id)
        return f"{context.agent_name}_{operation_name}"
    
    def _create_cached_result(self, cached_data: Any) -> ExecutionResult:
        """Create execution result from cached data."""
        self._error_metrics['fallback_uses'] += 1
        return ExecutionResult(
            status=ExecutionStatus.DEGRADED,
            data=cached_data,
            metadata={"source": "cache_fallback"}
        )
    
    async def _generate_graceful_degradation(self, context: ExecutionContext,
                                           classification: ErrorClassification) -> ExecutionResult:
        """Generate graceful degradation response."""
        return ExecutionResult(
            success=False,
            status=ExecutionStatus.DEGRADED,
            result={"message": "Service temporarily degraded", "retry_after": 30},
            metrics={"degradation_reason": classification.category.value}
        )
    
    def _create_error_result(self, error: Exception, context: ExecutionContext,
                           classification: ErrorClassification) -> ExecutionResult:
        """Create error result from exception."""
        error_metadata = {
            "error_category": classification.category.value,
            "severity": classification.severity.value,
            "is_retryable": classification.is_retryable
        }
        
        return ExecutionResult(
            success=False,
            status=ExecutionStatus.FAILED,
            error=str(error),
            execution_time_ms=0.0,
            metrics=error_metadata
        )
    
    def cache_fallback_data(self, context: ExecutionContext, data: Any) -> None:
        """Cache data for future fallback use."""
        operation_name = getattr(context, 'operation_name', context.run_id)
        cache_key = f"{context.agent_name}_{operation_name}"
        
        self._fallback_data_cache[cache_key] = {
            "data": data,
            "timestamp": time.time(),
            "context": context
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get error handler health status."""
        return {
            "status": "healthy",
            "cache_size": len(self._fallback_data_cache),
            "classifier_status": "active",
            **self.get_error_stats()
        }


# Global instance for backward compatibility
global_execution_error_handler = ExecutionErrorHandler()