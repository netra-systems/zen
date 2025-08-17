"""
Retry strategy executor with exponential backoff.
Provides the main exponential_backoff_retry function for async generators.
"""

from typing import Any, AsyncGenerator, Callable, Optional

from app.schemas.shared_types import RetryConfig
from app.core.retry_strategy_manager import execute_retry_attempt


async def exponential_backoff_retry(
    async_generator_func: AsyncGenerator,
    retry_config: RetryConfig,
    retryable_exceptions: tuple = (),
    exception_classifier: Optional[Callable] = None,
    logger: Optional[Any] = None
) -> AsyncGenerator:
    """Execute async generator with exponential backoff retry logic.
    
    Args:
        async_generator_func: Async generator function to retry
        retry_config: Configuration for retry behavior
        retryable_exceptions: Tuple of exceptions to retry on
        exception_classifier: Function to classify if error is retryable
        logger: Logger for retry messages
        
    Yields:
        Results from the async generator with retry metadata
    """
    retry_count = 0
    last_exception = None
    
    while retry_count <= retry_config.max_retries:
        success, exception, result = await _execute_single_retry_attempt(
            async_generator_func, retry_count, retry_config, 
            retryable_exceptions, exception_classifier, logger
        )
        
        if success:
            yield result
            return
        
        last_exception = exception
        retry_count += 1
    
    if last_exception:
        raise last_exception


async def _execute_single_retry_attempt(
    async_generator_func: AsyncGenerator,
    retry_count: int,
    retry_config: RetryConfig,
    retryable_exceptions: tuple,
    exception_classifier: Optional[Callable],
    logger: Optional[Any]
) -> tuple[bool, Optional[Exception], Any]:
    """Execute a single retry attempt."""
    return await execute_retry_attempt(
        async_generator_func, retry_count, retry_config, 
        retryable_exceptions, exception_classifier, logger
    )