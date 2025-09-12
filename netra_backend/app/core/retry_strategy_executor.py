"""
Retry strategy executor with exponential backoff using UnifiedRetryHandler.

 WARNING: [U+FE0F]  DEPRECATED: This module now delegates to UnifiedRetryHandler.
Use UnifiedRetryHandler directly for new code.

Provides the main exponential_backoff_retry function for async generators.
"""

import warnings
from typing import Any, AsyncGenerator, Callable, Optional

from netra_backend.app.core.retry_strategy_manager import execute_retry_attempt
from netra_backend.app.schemas.shared_types import RetryConfig


async def exponential_backoff_retry(
    async_generator_func: AsyncGenerator,
    retry_config: RetryConfig,
    retryable_exceptions: tuple = (),
    exception_classifier: Optional[Callable] = None,
    logger: Optional[Any] = None
) -> AsyncGenerator:
    """Execute async generator with exponential backoff retry logic using UnifiedRetryHandler.
    
     WARNING: [U+FE0F]  DEPRECATED: Use UnifiedRetryHandler directly for new code.
    
    Args:
        async_generator_func: Async generator function to retry
        retry_config: Configuration for retry behavior
        retryable_exceptions: Tuple of exceptions to retry on
        exception_classifier: Function to classify if error is retryable
        logger: Logger for retry messages
        
    Yields:
        Results from the async generator with retry metadata
    """
    warnings.warn(
        "exponential_backoff_retry is deprecated. Use UnifiedRetryHandler from "
        "netra_backend.app.core.resilience.unified_retry_handler for better functionality.",
        DeprecationWarning,
        stacklevel=2
    )
    
    try:
        # Import here to avoid circular dependencies
        from netra_backend.app.core.resilience.unified_retry_handler import (
            UnifiedRetryHandler, RetryConfig as UnifiedRetryConfig, RetryStrategy
        )
        
        # Convert legacy config to unified config
        unified_config = UnifiedRetryConfig(
            max_attempts=retry_config.max_retries + 1,
            base_delay=retry_config.base_delay,
            max_delay=retry_config.max_delay,
            strategy=RetryStrategy.EXPONENTIAL,
            backoff_multiplier=2.0,
            jitter_range=0.1,
            timeout_seconds=getattr(retry_config, 'timeout_seconds', None),
            retryable_exceptions=retryable_exceptions if retryable_exceptions else (Exception,),
            circuit_breaker_enabled=False,
            metrics_enabled=True
        )
        
        handler = UnifiedRetryHandler("retry_strategy_executor", unified_config)
        
        # Convert async generator to regular async function for UnifiedRetryHandler
        async def async_gen_wrapper():
            async for result in async_generator_func:
                return result  # Return first result for simplicity
        
        result = await handler.execute_with_retry_async(async_gen_wrapper)
        
        if result.success:
            yield result.result
        else:
            raise result.final_exception
            
    except ImportError:
        # Fall back to legacy implementation
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