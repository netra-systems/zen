"""
Retry strategy manager and utility functions.
Centralized management of retry strategies with metrics and utilities.
"""

import asyncio
from typing import Any, AsyncGenerator, Callable, Dict, Optional

from netra_backend.app.core.error_recovery import OperationType
from netra_backend.app.core.retry_strategy_base import EnhancedRetryStrategy
from netra_backend.app.core.retry_strategy_factory import (
    DEFAULT_RETRY_CONFIGS,
    RetryStrategyFactory,
)
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.shared_types import RetryConfig

logger = central_logger.get_logger(__name__)


class RetryManager:
    """Centralized retry strategy manager."""
    
    def __init__(self):
        """Initialize retry manager."""
        self.strategies: Dict[str, EnhancedRetryStrategy] = {}
        self.metrics: Dict[str, Dict[str, int]] = {}
    
    def get_strategy(
        self,
        operation_type: OperationType,
        operation_id: Optional[str] = None
    ) -> EnhancedRetryStrategy:
        """Get or create retry strategy for operation."""
        cache_key = self._create_cache_key(operation_type, operation_id)
        if cache_key not in self.strategies:
            self._create_and_cache_strategy(cache_key, operation_type)
        return self.strategies[cache_key]
    
    def record_retry_attempt(
        self,
        operation_type: OperationType,
        success: bool
    ) -> None:
        """Record retry attempt for metrics."""
        if operation_type.value not in self.metrics:
            self._initialize_metrics_for_operation(operation_type)
        self._update_metrics(operation_type, success)
    
    def get_retry_metrics(self) -> Dict[str, Any]:
        """Get retry operation metrics."""
        strategy_types = self._get_strategy_type_mapping()
        return {
            'total_metrics': self.metrics,
            'active_strategies': len(self.strategies),
            'strategy_types': strategy_types
        }
    
    def _create_cache_key(self, operation_type: OperationType, operation_id: Optional[str]) -> str:
        """Create cache key for strategy."""
        return f"{operation_type.value}:{operation_id or 'default'}"
    
    def _create_and_cache_strategy(self, cache_key: str, operation_type: OperationType) -> None:
        """Create and cache retry strategy for operation type."""
        config = DEFAULT_RETRY_CONFIGS.get(operation_type, RetryConfig())
        self.strategies[cache_key] = RetryStrategyFactory.create_strategy(operation_type, config)
    
    def _initialize_metrics_for_operation(self, operation_type: OperationType) -> None:
        """Initialize metrics structure for operation type."""
        self.metrics[operation_type.value] = {'attempts': 0, 'successes': 0, 'failures': 0}
    
    def _update_metrics(self, operation_type: OperationType, success: bool) -> None:
        """Update metrics based on retry attempt result."""
        self.metrics[operation_type.value]['attempts'] += 1
        metric_key = 'successes' if success else 'failures'
        self.metrics[operation_type.value][metric_key] += 1
    
    def _get_strategy_type_mapping(self) -> Dict[str, str]:
        """Get mapping of strategy IDs to strategy types."""
        return {
            strategy_id: type(strategy).__name__
            for strategy_id, strategy in self.strategies.items()
        }


# Global retry manager instance
retry_manager = RetryManager()


# Utility functions for retry operations
def should_retry_exception(
    exception: Exception, 
    exception_classifier: Optional[Callable], 
    retry_count: int, 
    max_retries: int
) -> bool:
    """Check if exception should be retried."""
    if not _exception_is_retryable(exception, exception_classifier):
        return False
    return retry_count < max_retries


def calculate_retry_delay(retry_config: RetryConfig, retry_count: int) -> float:
    """Calculate delay with exponential backoff."""
    base_delay = retry_config.base_delay * (2 ** retry_count)
    return min(base_delay, retry_config.max_delay)


def log_retry_attempt(
    logger_instance: Optional[Any], 
    delay: float, 
    retry_count: int, 
    max_retries: int, 
    exception: Exception
) -> None:
    """Log retry attempt information."""
    if logger_instance:
        logger_instance.warning(
            f"Retrying after {delay}s (attempt {retry_count + 1}/{max_retries}): {exception}"
        )


def log_max_retries_exceeded(logger_instance: Optional[Any], max_retries: int, exception: Exception) -> None:
    """Log when max retries are exceeded."""
    if logger_instance:
        logger_instance.error(f"Max retries ({max_retries}) exceeded: {exception}")


def log_non_retryable_exception(logger_instance: Optional[Any], exception: Exception) -> None:
    """Log non-retryable exception."""
    if logger_instance:
        logger_instance.error(f"Non-retryable exception: {exception}")


def add_retry_metadata_to_result(result: Any, retry_count: int) -> None:
    """Add retry metadata to result if possible."""
    if hasattr(result, '__dict__'):
        result.retry_count = retry_count


async def execute_generator_with_metadata(
    async_generator_func: AsyncGenerator, 
    retry_count: int
) -> AsyncGenerator:
    """Execute generator and add retry metadata to results."""
    async for result in async_generator_func:
        add_retry_metadata_to_result(result, retry_count)
        yield result
        return


async def handle_retryable_exception(
    exception: Exception,
    exception_classifier: Optional[Callable],
    retry_count: int,
    retry_config: RetryConfig,
    logger_instance: Optional[Any]
) -> None:
    """Handle retryable exception logic."""
    if not should_retry_exception(exception, exception_classifier, retry_count, retry_config.max_retries):
        raise
    if retry_count >= retry_config.max_retries:
        log_max_retries_exceeded(logger_instance, retry_config.max_retries, exception)
        raise
    delay = calculate_retry_delay(retry_config, retry_count)
    log_retry_attempt(logger_instance, delay, retry_count, retry_config.max_retries, exception)
    await asyncio.sleep(delay)


async def execute_retry_attempt(
    async_generator_func: AsyncGenerator,
    retry_count: int,
    retry_config: RetryConfig,
    retryable_exceptions: tuple,
    exception_classifier: Optional[Callable],
    logger_instance: Optional[Any]
) -> tuple[bool, Optional[Exception], Any]:
    """Execute single retry attempt."""
    try:
        async for result in execute_generator_with_metadata(async_generator_func, retry_count):
            return True, None, result
    except retryable_exceptions as e:
        await handle_retryable_exception(e, exception_classifier, retry_count, retry_config, logger_instance)
        return False, e, None
    except Exception as e:
        log_non_retryable_exception(logger_instance, e)
        raise


def _exception_is_retryable(exception: Exception, exception_classifier: Optional[Callable]) -> bool:
    """Check if exception is retryable."""
    if exception_classifier and not exception_classifier(exception):
        return False
    return True