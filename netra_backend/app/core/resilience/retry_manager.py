"""Retry Manager for Unified Resilience Framework

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability - Provide intelligent retry strategies
- Value Impact: Reduces transient failure impact through smart retry logic
- Strategic Impact: Improves overall system reliability and user experience

This module provides intelligent retry management with configurable strategies.
"""

import asyncio
import random
import time
from enum import Enum
from typing import Callable, Optional, Any

from pydantic import BaseModel

from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class BackoffStrategy(str, Enum):
    """Retry backoff strategies."""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIXED = "fixed"
    RANDOM = "random"


class JitterType(str, Enum):
    """Jitter types for retry strategies."""
    NONE = "none"
    FULL = "full"
    EQUAL = "equal"
    DECORRELATED = "decorrelated"


class RetryConfig(BaseModel):
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    backoff_multiplier: float = 2.0
    jitter_type: JitterType = JitterType.EQUAL
    enabled: bool = True
    retry_on_exceptions: Optional[tuple] = None


class RetryExhaustedException(Exception):
    """Raised when all retry attempts are exhausted."""
    
    def __init__(self, attempts: int, last_exception: Exception):
        self.attempts = attempts
        self.last_exception = last_exception
        super().__init__(f"All {attempts} retry attempts exhausted. Last error: {last_exception}")


class UnifiedRetryManager:
    """Unified retry manager with configurable strategies."""
    
    def __init__(self, config: RetryConfig):
        """Initialize retry manager."""
        self.config = config
        self._logger = logger
    
    async def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function with retry logic.
        
        Args:
            func: The function to execute
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The result of the function execution
            
        Raises:
            RetryExhaustedException: When all retry attempts are exhausted
        """
        if not self.config.enabled:
            return await self._execute_function(func, *args, **kwargs)
        
        last_exception = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                result = await self._execute_function(func, *args, **kwargs)
                if attempt > 1:
                    self._logger.info(f"Function succeeded on attempt {attempt}")
                return result
            except Exception as e:
                last_exception = e
                
                # Check if this exception type should be retried
                if self.config.retry_on_exceptions and not isinstance(e, self.config.retry_on_exceptions):
                    self._logger.info(f"Not retrying exception type: {type(e).__name__}")
                    raise e
                
                if attempt < self.config.max_attempts:
                    delay = self._calculate_delay(attempt)
                    self._logger.warning(f"Attempt {attempt} failed: {e}. Retrying in {delay:.2f}s")
                    await asyncio.sleep(delay)
                else:
                    self._logger.error(f"All {self.config.max_attempts} attempts failed. Last error: {e}")
        
        raise RetryExhaustedException(self.config.max_attempts, last_exception)
    
    async def _execute_function(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function, handling both sync and async."""
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate retry delay based on strategy."""
        if self.config.backoff_strategy == BackoffStrategy.FIXED:
            delay = self.config.base_delay_seconds
        elif self.config.backoff_strategy == BackoffStrategy.LINEAR:
            delay = self.config.base_delay_seconds * attempt
        elif self.config.backoff_strategy == BackoffStrategy.EXPONENTIAL:
            delay = self.config.base_delay_seconds * (self.config.backoff_multiplier ** (attempt - 1))
        elif self.config.backoff_strategy == BackoffStrategy.RANDOM:
            delay = random.uniform(self.config.base_delay_seconds, self.config.max_delay_seconds)
        else:
            delay = self.config.base_delay_seconds
        
        # Apply jitter
        delay = self._apply_jitter(delay, attempt)
        
        # Cap at max delay
        return min(delay, self.config.max_delay_seconds)
    
    def _apply_jitter(self, delay: float, attempt: int) -> float:
        """Apply jitter to delay."""
        if self.config.jitter_type == JitterType.NONE:
            return delay
        elif self.config.jitter_type == JitterType.FULL:
            return random.uniform(0, delay)
        elif self.config.jitter_type == JitterType.EQUAL:
            jitter = delay * 0.1  # 10% jitter
            return delay + random.uniform(-jitter, jitter)
        elif self.config.jitter_type == JitterType.DECORRELATED:
            # Decorrelated jitter prevents thundering herd
            return random.uniform(self.config.base_delay_seconds, delay * 3)
        else:
            return delay
    
    def update_config(self, config: RetryConfig) -> None:
        """Update retry configuration."""
        self.config = config
        self._logger.info("Retry configuration updated")


class RetryPresets:
    """Predefined retry configurations for common scenarios."""
    
    @staticmethod
    def create_api_retry() -> RetryConfig:
        """Create retry config optimized for API calls."""
        return RetryConfig(
            max_attempts=3,
            base_delay_seconds=1.0,
            max_delay_seconds=30.0,
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
            backoff_multiplier=2.0,
            jitter_type=JitterType.EQUAL
        )
    
    @staticmethod
    def create_database_retry() -> RetryConfig:
        """Create retry config optimized for database operations."""
        return RetryConfig(
            max_attempts=2,
            base_delay_seconds=0.5,
            max_delay_seconds=5.0,
            backoff_strategy=BackoffStrategy.LINEAR,
            backoff_multiplier=1.5,
            jitter_type=JitterType.FULL
        )
    
    @staticmethod
    def create_llm_retry() -> RetryConfig:
        """Create retry config optimized for LLM API calls."""
        return RetryConfig(
            max_attempts=3,
            base_delay_seconds=2.0,
            max_delay_seconds=120.0,
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
            backoff_multiplier=2.5,
            jitter_type=JitterType.DECORRELATED
        )
    
    @staticmethod
    def create_quick_retry() -> RetryConfig:
        """Create retry config for quick operations."""
        return RetryConfig(
            max_attempts=2,
            base_delay_seconds=0.1,
            max_delay_seconds=1.0,
            backoff_strategy=BackoffStrategy.FIXED,
            jitter_type=JitterType.NONE
        )
    
    @staticmethod
    def create_no_retry() -> RetryConfig:
        """Create config that disables retries."""
        return RetryConfig(
            max_attempts=1,
            enabled=False
        )


# Export all classes
__all__ = [
    "BackoffStrategy",
    "JitterType",
    "RetryConfig",
    "RetryExhaustedException", 
    "UnifiedRetryManager",
    "RetryPresets",
]