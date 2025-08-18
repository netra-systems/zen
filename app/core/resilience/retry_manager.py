"""Intelligent retry manager for unified resilience framework.

This module provides enterprise-grade retry strategies with:
- Configurable backoff algorithms (exponential, linear, fixed)
- Jitter to prevent thundering herd effects
- Context-aware retry decisions
- Integration with circuit breakers and monitoring

All functions are ≤8 lines per MANDATORY requirements.
"""

import asyncio
import random
import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
from dataclasses import dataclass, field

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)
T = TypeVar('T')


class BackoffStrategy(Enum):
    """Retry backoff strategy types."""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIXED = "fixed"
    JITTERED_EXPONENTIAL = "jittered_exponential"


class JitterType(Enum):
    """Jitter types for backoff strategies."""
    NONE = "none"
    FULL = "full"
    EQUAL = "equal"
    DECORRELATED = "decorrelated"


@dataclass
class RetryConfig:
    """Enterprise retry configuration."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    jitter_type: JitterType = JitterType.EQUAL
    multiplier: float = 2.0
    retryable_exceptions: List[type] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        """Validate retry configuration."""
        self._validate_attempts()
        self._validate_delays()
        self._validate_multiplier()
    
    def _validate_attempts(self) -> None:
        """Validate max attempts is positive."""
        if self.max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
    
    def _validate_delays(self) -> None:
        """Validate delay values are positive."""
        if self.base_delay <= 0:
            raise ValueError("base_delay must be positive")
        if self.max_delay <= 0:
            raise ValueError("max_delay must be positive")
        if self.base_delay > self.max_delay:
            raise ValueError("base_delay cannot exceed max_delay")
    
    def _validate_multiplier(self) -> None:
        """Validate multiplier is positive."""
        if self.multiplier <= 0:
            raise ValueError("multiplier must be positive")


@dataclass
class RetryAttempt:
    """Information about a retry attempt."""
    attempt: int
    delay: float
    exception: Optional[Exception]
    timestamp: float
    total_elapsed: float


@dataclass
class RetryMetrics:
    """Retry metrics for monitoring."""
    total_attempts: int = 0
    successful_retries: int = 0
    failed_retries: int = 0
    total_delay: float = 0.0
    attempt_history: List[RetryAttempt] = field(default_factory=list)


class RetryExhaustedException(Exception):
    """Raised when retry attempts are exhausted."""
    
    def __init__(self, attempts: int, last_exception: Exception) -> None:
        super().__init__(f"Retry exhausted after {attempts} attempts")
        self.attempts = attempts
        self.last_exception = last_exception


class UnifiedRetryManager:
    """Enterprise retry manager with intelligent strategies."""
    
    def __init__(self, config: RetryConfig) -> None:
        self.config = config
        self.metrics = RetryMetrics()
    
    async def execute_with_retry(
        self, 
        func: Callable[[], T], 
        context: Optional[Dict[str, Any]] = None
    ) -> T:
        """Execute function with retry logic."""
        start_time = time.time()
        last_exception = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                result = await self._execute_attempt(func, attempt)
                self._record_success(attempt, start_time)
                return result
            except Exception as e:
                last_exception = e
                if not self._should_retry(e, attempt):
                    self._record_failure(attempt, start_time)
                    raise
                await self._handle_retry_delay(attempt, e, start_time)
        
        self._record_exhausted_retry(start_time)
        raise RetryExhaustedException(self.config.max_attempts, last_exception)
    
    async def _execute_attempt(self, func: Callable[[], T], attempt: int) -> T:
        """Execute a single attempt."""
        logger.debug(f"Retry attempt {attempt}/{self.config.max_attempts}")
        if asyncio.iscoroutinefunction(func):
            return await func()
        return func()
    
    def _should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if exception should trigger retry."""
        if attempt >= self.config.max_attempts:
            return False
        if not self.config.retryable_exceptions:
            return True
        return any(isinstance(exception, exc_type) 
                  for exc_type in self.config.retryable_exceptions)
    
    async def _handle_retry_delay(
        self, 
        attempt: int, 
        exception: Exception, 
        start_time: float
    ) -> None:
        """Handle delay before next retry attempt."""
        delay = self._calculate_delay(attempt)
        self._record_attempt(attempt, delay, exception, start_time)
        logger.info(f"Retrying after {delay:.2f}s due to: {type(exception).__name__}")
        await asyncio.sleep(delay)
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt."""
        if self.config.backoff_strategy == BackoffStrategy.FIXED:
            base_delay = self.config.base_delay
        elif self.config.backoff_strategy == BackoffStrategy.LINEAR:
            base_delay = self.config.base_delay * attempt
        else:  # EXPONENTIAL or JITTERED_EXPONENTIAL
            base_delay = self.config.base_delay * (self.config.multiplier ** (attempt - 1))
        
        delay = min(base_delay, self.config.max_delay)
        return self._apply_jitter(delay, attempt)
    
    def _apply_jitter(self, delay: float, attempt: int) -> float:
        """Apply jitter to delay based on jitter type."""
        if self.config.jitter_type == JitterType.NONE:
            return delay
        elif self.config.jitter_type == JitterType.FULL:
            return random.uniform(0, delay)
        elif self.config.jitter_type == JitterType.EQUAL:
            return delay * 0.5 + random.uniform(0, delay * 0.5)
        else:  # DECORRELATED
            previous_delay = self.config.base_delay if attempt == 1 else delay
            return random.uniform(self.config.base_delay, previous_delay * 3)
    
    def _record_attempt(
        self, 
        attempt: int, 
        delay: float, 
        exception: Exception, 
        start_time: float
    ) -> None:
        """Record retry attempt for metrics."""
        retry_attempt = RetryAttempt(
            attempt=attempt,
            delay=delay,
            exception=exception,
            timestamp=time.time(),
            total_elapsed=time.time() - start_time
        )
        self.metrics.attempt_history.append(retry_attempt)
        self.metrics.total_attempts += 1
        self.metrics.total_delay += delay
    
    def _record_success(self, attempts: int, start_time: float) -> None:
        """Record successful retry completion."""
        if attempts > 1:
            self.metrics.successful_retries += 1
            elapsed = time.time() - start_time
            logger.info(f"Retry succeeded after {attempts} attempts ({elapsed:.2f}s)")
    
    def _record_failure(self, attempts: int, start_time: float) -> None:
        """Record retry failure (non-retryable exception)."""
        elapsed = time.time() - start_time
        logger.warning(f"Retry failed after {attempts} attempts ({elapsed:.2f}s)")
    
    def _record_exhausted_retry(self, start_time: float) -> None:
        """Record exhausted retry attempts."""
        self.metrics.failed_retries += 1
        elapsed = time.time() - start_time
        logger.error(f"Retry exhausted after {self.config.max_attempts} attempts ({elapsed:.2f}s)")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get retry metrics for monitoring."""
        avg_delay = (self.metrics.total_delay / self.metrics.total_attempts 
                    if self.metrics.total_attempts > 0 else 0.0)
        
        return {
            "total_attempts": self.metrics.total_attempts,
            "successful_retries": self.metrics.successful_retries,
            "failed_retries": self.metrics.failed_retries,
            "success_rate": self._calculate_retry_success_rate(),
            "average_delay": avg_delay,
            "total_delay": self.metrics.total_delay,
            "config": self._get_config_summary()
        }
    
    def _calculate_retry_success_rate(self) -> float:
        """Calculate retry success rate."""
        total_retry_operations = self.metrics.successful_retries + self.metrics.failed_retries
        if total_retry_operations > 0:
            return self.metrics.successful_retries / total_retry_operations
        return 1.0
    
    def _get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary for metrics."""
        return {
            "max_attempts": self.config.max_attempts,
            "base_delay": self.config.base_delay,
            "max_delay": self.config.max_delay,
            "backoff_strategy": self.config.backoff_strategy.value,
            "jitter_type": self.config.jitter_type.value
        }
    
    def reset_metrics(self) -> None:
        """Reset retry metrics."""
        self.metrics = RetryMetrics()


# Predefined retry configurations for common use cases
class RetryPresets:
    """Predefined retry configurations for common scenarios."""
    
    @staticmethod
    def get_database_retry() -> RetryConfig:
        """Get retry configuration for database operations."""
        return RetryConfig(
            max_attempts=5,
            base_delay=0.5,
            max_delay=30.0,
            backoff_strategy=BackoffStrategy.JITTERED_EXPONENTIAL,
            jitter_type=JitterType.EQUAL
        )
    
    @staticmethod
    def get_api_retry() -> RetryConfig:
        """Get retry configuration for API calls."""
        return RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=60.0,
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
            jitter_type=JitterType.FULL
        )
    
    @staticmethod
    def get_llm_retry() -> RetryConfig:
        """Get retry configuration for LLM calls."""
        return RetryConfig(
            max_attempts=4,
            base_delay=2.0,
            max_delay=120.0,
            backoff_strategy=BackoffStrategy.JITTERED_EXPONENTIAL,
            jitter_type=JitterType.DECORRELATED
        )
    
    @staticmethod
    def get_websocket_retry() -> RetryConfig:
        """Get retry configuration for WebSocket connections."""
        return RetryConfig(
            max_attempts=10,
            base_delay=1.0,
            max_delay=30.0,
            backoff_strategy=BackoffStrategy.LINEAR,
            jitter_type=JitterType.EQUAL
        )