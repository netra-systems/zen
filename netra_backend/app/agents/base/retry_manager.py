"""Retry Manager Implementation for Agent Reliability

Retry logic with exponential backoff:
- Configurable retry attempts and delays
- Intelligent exception handling
- Context-aware retry preparation
- Exponential backoff with maximum delay limits

Business Value: Handles transient failures gracefully, reducing false failures.
"""

import asyncio
from typing import Dict, Any, Callable, Awaitable

from netra_backend.app.logging_config import central_logger
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.schemas.shared_types import RetryConfig
from netra_backend.app.agents.base.circuit_breaker import CircuitBreakerOpenException

logger = central_logger.get_logger(__name__)


class RetryManager:
    """Manages retry logic with exponential backoff.
    
    Provides intelligent retry mechanisms for transient failures
    with configurable backoff strategies.
    """
    
    def __init__(self, config: RetryConfig):
        self.config = config
        
    async def execute_with_retry(self, func: Callable[[], Awaitable[Any]],
                               context: ExecutionContext) -> Any:
        """Execute function with retry logic."""
        return await self._execute_retry_loop(func, context)
    
    async def _execute_retry_loop(self, func: Callable[[], Awaitable[Any]],
                                 context: ExecutionContext) -> Any:
        """Execute retry loop with attempts."""
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            result = await self._attempt_execution(func, context, attempt)
            if result["success"]:
                return result["value"]
            
            last_exception = result["exception"]
            if not self._should_retry_attempt(last_exception, attempt):
                break
        
        raise last_exception
    
    def _should_retry_attempt(self, exception: Exception, attempt: int) -> bool:
        """Check if should retry this attempt."""
        return self._should_retry(exception, attempt)
    
    async def _attempt_execution(self, func: Callable[[], Awaitable[Any]], 
                               context: ExecutionContext, attempt: int) -> Dict[str, Any]:
        """Attempt single execution with retry preparation."""
        try:
            await self._prepare_retry_attempt(attempt, context)
            result = await func()
            return self._create_success_result(result)
        except Exception as e:
            self._log_retry_attempt(context, attempt, e)
            return self._create_failure_result(e)
    
    def _create_success_result(self, result: Any) -> Dict[str, Any]:
        """Create success result dictionary."""
        return {"success": True, "value": result, "exception": None}
    
    def _create_failure_result(self, exception: Exception) -> Dict[str, Any]:
        """Create failure result dictionary."""
        return {"success": False, "value": None, "exception": exception}
    
    async def _prepare_retry_attempt(self, attempt: int, context: ExecutionContext) -> None:
        """Prepare context for retry attempt."""
        if attempt > 0:
            await self._wait_for_retry(attempt)
            context.retry_count = attempt
    
    def _should_retry(self, exception: Exception, attempt: int) -> bool:
        """Check if operation should be retried."""
        if attempt >= self.config.max_retries:
            return False
        
        # Check if exception is retryable
        return self._is_retryable_exception(exception)
    
    def _is_retryable_exception(self, exception: Exception) -> bool:
        """Check if exception is retryable."""
        # Import here to avoid circular imports
        from netra_backend.app.agents.base.errors import AgentExecutionError
        
        if isinstance(exception, AgentExecutionError):
            return exception.is_retryable
        
        return self._is_common_retryable_exception(exception)
    
    def _is_common_retryable_exception(self, exception: Exception) -> bool:
        """Check if exception is a common retryable type."""
        retryable_types = (
            ConnectionError,
            TimeoutError,
            CircuitBreakerOpenException
        )
        return isinstance(exception, retryable_types)
    
    async def _wait_for_retry(self, attempt: int) -> None:
        """Wait for exponential backoff delay."""
        delay = min(
            self.config.base_delay * (2 ** (attempt - 1)),
            self.config.max_delay
        )
        await asyncio.sleep(delay)
    
    def _log_retry_attempt(self, context: ExecutionContext, 
                          attempt: int, exception: Exception) -> None:
        """Log retry attempt details."""
        logger.warning(
            f"Retry attempt {attempt}/{self.config.max_retries} for "
            f"{context.agent_name}: {exception}"
        )