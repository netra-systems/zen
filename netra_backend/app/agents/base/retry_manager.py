"""Retry Manager Implementation for Agent Reliability

⚠️  DEPRECATED: This class now delegates to UnifiedRetryHandler.
Use UnifiedRetryHandler directly for new code.

Retry logic with exponential backoff:
- Configurable retry attempts and delays
- Intelligent exception handling
- Context-aware retry preparation
- Exponential backoff with maximum delay limits

Business Value: Handles transient failures gracefully, reducing false failures.
"""

import asyncio
import warnings
from typing import Any, Awaitable, Callable, Dict

from netra_backend.app.agents.base.circuit_breaker import CircuitBreakerOpenException
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.core.resilience.unified_retry_handler import (
    UnifiedRetryHandler,
    RetryConfig as UnifiedRetryConfig,
    RetryStrategy,
    agent_retry_handler
)
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.shared_types import RetryConfig

logger = central_logger.get_logger(__name__)


class RetryManager:
    """Manages retry logic with exponential backoff.
    
    ⚠️  DEPRECATED: This class now delegates to UnifiedRetryHandler.
    Use UnifiedRetryHandler directly for new code.
    
    Provides intelligent retry mechanisms for transient failures
    with configurable backoff strategies.
    """
    
    def __init__(self, config: RetryConfig):
        warnings.warn(
            "RetryManager is deprecated. Use UnifiedRetryHandler from "
            "netra_backend.app.core.resilience.unified_retry_handler for better functionality.",
            DeprecationWarning,
            stacklevel=2
        )
        
        self.config = config
        
        # Convert legacy config to unified config
        unified_config = self._convert_to_unified_config(config)
        self._unified_handler = UnifiedRetryHandler("agent_retry_manager", unified_config)
        
        logger.info("RetryManager created with UnifiedRetryHandler delegation")
    
    def _convert_to_unified_config(self, config: RetryConfig) -> UnifiedRetryConfig:
        """Convert legacy RetryConfig to UnifiedRetryConfig."""
        return UnifiedRetryConfig(
            max_attempts=config.max_retries + 1,  # Legacy uses max_retries, unified uses max_attempts
            base_delay=config.base_delay,
            max_delay=config.max_delay,
            strategy=RetryStrategy.EXPONENTIAL,
            backoff_multiplier=2.0,
            jitter_range=0.1,
            timeout_seconds=None,
            retryable_exceptions=(
                ConnectionError,
                TimeoutError,
                CircuitBreakerOpenException,
            ),
            non_retryable_exceptions=(
                ValueError,
                TypeError,
                AttributeError,
            ),
            circuit_breaker_enabled=False,
            metrics_enabled=True
        )
        
    async def execute_with_retry(self, func: Callable[[], Awaitable[Any]],
                               context: ExecutionContext) -> Any:
        """Execute function with retry logic."""
        # Update context with retry information
        async def context_aware_func():
            context.retry_count = getattr(context, 'retry_count', 0)
            return await func()
        
        # Execute with unified retry handler
        result = await self._unified_handler.execute_with_retry_async(context_aware_func)
        
        if result.success:
            return result.result
        else:
            # Update context with final retry count
            context.retry_count = result.total_attempts
            raise result.final_exception
    
    # Legacy compatibility methods - deprecated, delegate to unified handler
    def _should_retry(self, exception: Exception, attempt: int) -> bool:
        """DEPRECATED: Check if operation should be retried."""
        return self._unified_handler._should_retry(exception, attempt + 1) != self._unified_handler._should_retry.__class__.__name__.STOP
    
    def _is_retryable_exception(self, exception: Exception) -> bool:
        """DEPRECATED: Check if exception is retryable."""
        # Import here to avoid circular imports
        from netra_backend.app.agents.base.errors import AgentExecutionError
        
        if isinstance(exception, AgentExecutionError):
            return exception.is_retryable
        
        return self._is_common_retryable_exception(exception)
    
    def _is_common_retryable_exception(self, exception: Exception) -> bool:
        """DEPRECATED: Check if exception is a common retryable type."""
        retryable_types = (
            ConnectionError,
            TimeoutError,
            CircuitBreakerOpenException
        )
        return isinstance(exception, retryable_types)