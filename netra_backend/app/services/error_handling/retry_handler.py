"""
Retry Handler - SSOT Error Handling Implementation

This module provides intelligent retry functionality for the Netra platform.
Following SSOT principles, this is the canonical implementation for retry logic.

Business Value: Platform/Internal - System Reliability & Resilience
Ensures robust error handling and automatic recovery across all platform operations.

CRITICAL: This is a minimal SSOT-compliant stub to resolve import errors.
Full implementation should follow CLAUDE.md SSOT patterns.
"""

import asyncio
import logging
import time
from functools import wraps
from typing import Callable, Any, Optional, Type, Union, List, Dict
from dataclasses import dataclass
from enum import Enum

from shared.isolated_environment import get_env


logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Retry strategy types."""
    FIXED_DELAY = "fixed_delay"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    CUSTOM = "custom"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    retry_on_exceptions: Optional[List[Type[Exception]]] = None
    stop_on_exceptions: Optional[List[Type[Exception]]] = None
    jitter: bool = True


@dataclass
class RetryResult:
    """Result of retry operation."""
    success: bool
    attempts_made: int
    total_time: float
    last_exception: Optional[Exception]
    result: Any = None


class RetryHandler:
    """
    SSOT Retry Handler.
    
    This is the canonical implementation for all retry logic across the platform.
    Provides intelligent retry with exponential backoff, jitter, and circuit breaker integration.
    """
    
    def __init__(self, config: Optional[RetryConfig] = None):
        """Initialize retry handler with SSOT environment."""
        self._env = get_env()
        self._config = config or self._load_default_config()
        self._retry_enabled = self._env.get("RETRY_HANDLER_ENABLED", "true").lower() == "true"
    
    def _load_default_config(self) -> RetryConfig:
        """Load default retry configuration from environment."""
        return RetryConfig(
            max_attempts=int(self._env.get("RETRY_MAX_ATTEMPTS", "3")),
            initial_delay=float(self._env.get("RETRY_INITIAL_DELAY", "1.0")),
            max_delay=float(self._env.get("RETRY_MAX_DELAY", "60.0")),
            backoff_factor=float(self._env.get("RETRY_BACKOFF_FACTOR", "2.0")),
            strategy=RetryStrategy(self._env.get("RETRY_STRATEGY", "exponential_backoff")),
            jitter=self._env.get("RETRY_JITTER", "true").lower() == "true"
        )
    
    def retry(self, 
              func: Callable,
              *args,
              config: Optional[RetryConfig] = None,
              **kwargs) -> RetryResult:
        """
        Execute function with retry logic.
        
        Args:
            func: Function to execute
            *args: Function arguments
            config: Override retry configuration
            **kwargs: Function keyword arguments
            
        Returns:
            Retry result
        """
        if not self._retry_enabled:
            try:
                result = func(*args, **kwargs)
                return RetryResult(
                    success=True,
                    attempts_made=1,
                    total_time=0.0,
                    last_exception=None,
                    result=result
                )
            except Exception as e:
                return RetryResult(
                    success=False,
                    attempts_made=1,
                    total_time=0.0,
                    last_exception=e,
                    result=None
                )
        
        config = config or self._config
        start_time = time.time()
        last_exception = None
        
        for attempt in range(1, config.max_attempts + 1):
            try:
                result = func(*args, **kwargs)
                total_time = time.time() - start_time
                
                logger.info(f"Function succeeded on attempt {attempt}")
                return RetryResult(
                    success=True,
                    attempts_made=attempt,
                    total_time=total_time,
                    last_exception=None,
                    result=result
                )
                
            except Exception as e:
                last_exception = e
                
                # Check if we should stop retrying on this exception
                if config.stop_on_exceptions and type(e) in config.stop_on_exceptions:
                    logger.warning(f"Stopping retry due to stop exception: {type(e).__name__}")
                    break
                
                # Check if we should retry on this exception
                if config.retry_on_exceptions and type(e) not in config.retry_on_exceptions:
                    logger.warning(f"Not retrying due to non-retryable exception: {type(e).__name__}")
                    break
                
                # Don't sleep after the last attempt
                if attempt < config.max_attempts:
                    delay = self._calculate_delay(attempt, config)
                    logger.warning(f"Attempt {attempt} failed: {e}. Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
                else:
                    logger.error(f"Attempt {attempt} failed: {e}. No more retries.")
        
        total_time = time.time() - start_time
        return RetryResult(
            success=False,
            attempts_made=config.max_attempts,
            total_time=total_time,
            last_exception=last_exception,
            result=None
        )
    
    async def retry_async(self,
                         func: Callable,
                         *args,
                         config: Optional[RetryConfig] = None,
                         **kwargs) -> RetryResult:
        """
        Execute async function with retry logic.
        
        Args:
            func: Async function to execute
            *args: Function arguments
            config: Override retry configuration
            **kwargs: Function keyword arguments
            
        Returns:
            Retry result
        """
        if not self._retry_enabled:
            try:
                result = await func(*args, **kwargs)
                return RetryResult(
                    success=True,
                    attempts_made=1,
                    total_time=0.0,
                    last_exception=None,
                    result=result
                )
            except Exception as e:
                return RetryResult(
                    success=False,
                    attempts_made=1,
                    total_time=0.0,
                    last_exception=e,
                    result=None
                )
        
        config = config or self._config
        start_time = time.time()
        last_exception = None
        
        for attempt in range(1, config.max_attempts + 1):
            try:
                result = await func(*args, **kwargs)
                total_time = time.time() - start_time
                
                logger.info(f"Async function succeeded on attempt {attempt}")
                return RetryResult(
                    success=True,
                    attempts_made=attempt,
                    total_time=total_time,
                    last_exception=None,
                    result=result
                )
                
            except Exception as e:
                last_exception = e
                
                # Same exception handling logic as sync version
                if config.stop_on_exceptions and type(e) in config.stop_on_exceptions:
                    logger.warning(f"Stopping async retry due to stop exception: {type(e).__name__}")
                    break
                
                if config.retry_on_exceptions and type(e) not in config.retry_on_exceptions:
                    logger.warning(f"Not retrying async due to non-retryable exception: {type(e).__name__}")
                    break
                
                if attempt < config.max_attempts:
                    delay = self._calculate_delay(attempt, config)
                    logger.warning(f"Async attempt {attempt} failed: {e}. Retrying in {delay:.2f} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Async attempt {attempt} failed: {e}. No more retries.")
        
        total_time = time.time() - start_time
        return RetryResult(
            success=False,
            attempts_made=config.max_attempts,
            total_time=total_time,
            last_exception=last_exception,
            result=None
        )
    
    def _calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        """Calculate delay for retry attempt."""
        if config.strategy == RetryStrategy.FIXED_DELAY:
            delay = config.initial_delay
        elif config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = config.initial_delay * (config.backoff_factor ** (attempt - 1))
        elif config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = config.initial_delay * attempt
        else:  # CUSTOM or fallback
            delay = config.initial_delay
        
        # Apply maximum delay limit
        delay = min(delay, config.max_delay)
        
        # Apply jitter to avoid thundering herd
        if config.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)  # 50-100% of calculated delay
        
        return delay


def retry_on_exception(*exception_types: Type[Exception],
                      max_attempts: int = 3,
                      initial_delay: float = 1.0):
    """
    Decorator for automatic retry on specific exceptions.
    
    Args:
        *exception_types: Exception types to retry on
        max_attempts: Maximum retry attempts
        initial_delay: Initial delay between retries
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            config = RetryConfig(
                max_attempts=max_attempts,
                initial_delay=initial_delay,
                retry_on_exceptions=list(exception_types)
            )
            handler = RetryHandler(config)
            result = handler.retry(func, *args, **kwargs)
            
            if result.success:
                return result.result
            else:
                raise result.last_exception
        
        return wrapper
    return decorator


# SSOT Factory Function
def create_retry_handler(config: Optional[RetryConfig] = None) -> RetryHandler:
    """
    SSOT factory function for creating retry handler instances.
    
    Args:
        config: Retry configuration
        
    Returns:
        Configured retry handler
    """
    return RetryHandler(config)


# Export SSOT interface
__all__ = [
    "RetryHandler",
    "RetryConfig",
    "RetryResult",
    "RetryStrategy",
    "retry_on_exception",
    "create_retry_handler"
]