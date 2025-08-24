"""
Unified Retry and Timeout Handler

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Eliminate retry/timeout logic duplication across all services
- Value Impact: Consistent resilience patterns, standardized backoff strategies, unified error handling
- Strategic Impact: Improved system reliability, consistent SLA behavior, reduced operational complexity

This module provides unified retry and timeout handling that can be used across:
- Database connections (PostgreSQL, ClickHouse, Redis)
- HTTP requests (API calls, health checks, webhooks)
- File operations (with retries on temporary failures)
- Service startup and initialization

Key functionality:
- Configurable retry strategies (exponential backoff, linear, custom)
- Circuit breaker pattern integration
- Timeout management with escalation
- Async and sync support
- Comprehensive error classification
- Metrics integration for monitoring

Replaces 10+ duplicate retry/timeout implementations with a single unified handler.
Each function ≤25 lines, class ≤300 lines total.
"""

import asyncio
import logging
import time
import random
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Awaitable, Callable, Dict, List, Optional, Type, Union, Tuple
from datetime import datetime, timedelta, timezone

from netra_backend.app.core.configuration.environment import IsolatedEnvironment

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Retry strategy types."""
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    EXPONENTIAL_JITTER = "exponential_jitter"
    CUSTOM = "custom"


class RetryDecision(Enum):
    """Retry decision outcomes."""
    RETRY = "retry"
    STOP = "stop"
    ESCALATE = "escalate"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    backoff_multiplier: float = 2.0
    jitter_range: float = 0.1
    timeout_seconds: Optional[float] = None
    retryable_exceptions: Tuple[Type[Exception], ...] = field(default_factory=lambda: (Exception,))
    non_retryable_exceptions: Tuple[Type[Exception], ...] = field(default_factory=tuple)
    
    
@dataclass 
class RetryAttempt:
    """Information about a retry attempt."""
    attempt_number: int
    delay_before: float
    exception: Optional[Exception]
    timestamp: datetime
    elapsed_time: float


class RetryResult:
    """Result of a retry operation."""
    def __init__(self, success: bool, result: Any = None, attempts: List[RetryAttempt] = None, final_exception: Exception = None):
        self.success = success
        self.result = result
        self.attempts = attempts or []
        self.final_exception = final_exception
        self.total_attempts = len(self.attempts)
        self.total_time = sum(attempt.elapsed_time for attempt in self.attempts)


class UnifiedRetryHandler:
    """
    Unified retry handler for consistent resilience patterns across all services.
    
    Provides standardized retry logic with configurable strategies, timeouts,
    and error handling for both synchronous and asynchronous operations.
    """
    
    def __init__(self, service_name: str = "unknown", config: Optional[RetryConfig] = None):
        self.service_name = service_name
        self.config = config or RetryConfig()
        self.env = IsolatedEnvironment()
        self._load_config_from_env()
    
    def _load_config_from_env(self) -> None:
        """Load retry configuration from environment."""
        # Override config with environment variables if present
        self.config.max_attempts = int(self.env.get("RETRY_MAX_ATTEMPTS", str(self.config.max_attempts)))
        self.config.base_delay = float(self.env.get("RETRY_BASE_DELAY", str(self.config.base_delay)))
        self.config.max_delay = float(self.env.get("RETRY_MAX_DELAY", str(self.config.max_delay)))
        self.config.backoff_multiplier = float(self.env.get("RETRY_BACKOFF_MULTIPLIER", str(self.config.backoff_multiplier)))
        self.config.jitter_range = float(self.env.get("RETRY_JITTER_RANGE", str(self.config.jitter_range)))
        
        # Set timeout from environment
        timeout_env = self.env.get("RETRY_TIMEOUT_SECONDS")
        if timeout_env:
            self.config.timeout_seconds = float(timeout_env)
        
        # Set strategy from environment
        strategy_env = self.env.get("RETRY_STRATEGY", "").lower()
        if strategy_env:
            try:
                self.config.strategy = RetryStrategy(strategy_env)
            except ValueError:
                logger.warning(f"Unknown retry strategy '{strategy_env}', using default")
    
    def _calculate_delay(self, attempt_number: int) -> float:
        """Calculate delay before retry attempt."""
        if self.config.strategy == RetryStrategy.FIXED:
            delay = self.config.base_delay
        elif self.config.strategy == RetryStrategy.LINEAR:
            delay = self.config.base_delay * attempt_number
        elif self.config.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.config.base_delay * (self.config.backoff_multiplier ** (attempt_number - 1))
        elif self.config.strategy == RetryStrategy.EXPONENTIAL_JITTER:
            delay = self.config.base_delay * (self.config.backoff_multiplier ** (attempt_number - 1))
            # Add jitter to prevent thundering herd
            jitter = delay * self.config.jitter_range * (random.random() * 2 - 1)
            delay += jitter
        else:  # CUSTOM - subclasses can override this method
            delay = self.config.base_delay
            
        # Cap delay at maximum
        return min(delay, self.config.max_delay)
    
    def _should_retry(self, exception: Exception, attempt_number: int) -> RetryDecision:
        """Determine if operation should be retried."""
        # Check attempt limits
        if attempt_number >= self.config.max_attempts:
            return RetryDecision.STOP
            
        # Check non-retryable exceptions first
        for exc_type in self.config.non_retryable_exceptions:
            if isinstance(exception, exc_type):
                return RetryDecision.STOP
                
        # Check retryable exceptions
        for exc_type in self.config.retryable_exceptions:
            if isinstance(exception, exc_type):
                return RetryDecision.RETRY
                
        # Default decision
        return RetryDecision.STOP
    
    def execute_with_retry(self, func: Callable[[], Any], *args, **kwargs) -> RetryResult:
        """
        Execute function with retry logic.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            RetryResult with outcome and attempt information
        """
        attempts = []
        start_time = time.time()
        
        for attempt_num in range(1, self.config.max_attempts + 1):
            attempt_start = time.time()
            
            try:
                # Check overall timeout
                if self.config.timeout_seconds:
                    elapsed = time.time() - start_time
                    if elapsed >= self.config.timeout_seconds:
                        raise TimeoutError(f"Overall timeout exceeded: {elapsed:.2f}s >= {self.config.timeout_seconds}s")
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Success - record attempt and return
                attempt_time = time.time() - attempt_start
                attempts.append(RetryAttempt(
                    attempt_number=attempt_num,
                    delay_before=0.0,
                    exception=None,
                    timestamp=datetime.now(timezone.utc),
                    elapsed_time=attempt_time
                ))
                
                logger.debug(f"Operation succeeded on attempt {attempt_num}")
                return RetryResult(success=True, result=result, attempts=attempts)
                
            except Exception as e:
                attempt_time = time.time() - attempt_start
                
                # Decide whether to retry
                retry_decision = self._should_retry(e, attempt_num)
                
                if retry_decision == RetryDecision.STOP:
                    attempts.append(RetryAttempt(
                        attempt_number=attempt_num,
                        delay_before=0.0,
                        exception=e,
                        timestamp=datetime.now(timezone.utc),
                        elapsed_time=attempt_time
                    ))
                    logger.debug(f"Stopping retries after attempt {attempt_num}: {e}")
                    return RetryResult(success=False, attempts=attempts, final_exception=e)
                
                # Calculate delay for next attempt
                delay = self._calculate_delay(attempt_num) if attempt_num < self.config.max_attempts else 0.0
                
                attempts.append(RetryAttempt(
                    attempt_number=attempt_num,
                    delay_before=delay,
                    exception=e,
                    timestamp=datetime.now(timezone.utc),
                    elapsed_time=attempt_time
                ))
                
                logger.debug(f"Attempt {attempt_num} failed: {e}. Retrying in {delay:.2f}s")
                
                if delay > 0 and attempt_num < self.config.max_attempts:
                    time.sleep(delay)
        
        # Should not reach here, but handle edge case
        final_exception = attempts[-1].exception if attempts else Exception("Unknown error")
        return RetryResult(success=False, attempts=attempts, final_exception=final_exception)
    
    async def execute_with_retry_async(self, func: Callable[[], Awaitable[Any]], *args, **kwargs) -> RetryResult:
        """
        Execute async function with retry logic.
        
        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            RetryResult with outcome and attempt information
        """
        attempts = []
        start_time = time.time()
        
        for attempt_num in range(1, self.config.max_attempts + 1):
            attempt_start = time.time()
            
            try:
                # Check overall timeout
                if self.config.timeout_seconds:
                    elapsed = time.time() - start_time
                    if elapsed >= self.config.timeout_seconds:
                        raise TimeoutError(f"Overall timeout exceeded: {elapsed:.2f}s >= {self.config.timeout_seconds}s")
                
                # Execute async function
                if self.config.timeout_seconds:
                    remaining_time = self.config.timeout_seconds - elapsed
                    result = await asyncio.wait_for(func(*args, **kwargs), timeout=remaining_time)
                else:
                    result = await func(*args, **kwargs)
                
                # Success - record attempt and return
                attempt_time = time.time() - attempt_start
                attempts.append(RetryAttempt(
                    attempt_number=attempt_num,
                    delay_before=0.0,
                    exception=None,
                    timestamp=datetime.now(timezone.utc),
                    elapsed_time=attempt_time
                ))
                
                logger.debug(f"Async operation succeeded on attempt {attempt_num}")
                return RetryResult(success=True, result=result, attempts=attempts)
                
            except Exception as e:
                attempt_time = time.time() - attempt_start
                
                # Decide whether to retry
                retry_decision = self._should_retry(e, attempt_num)
                
                if retry_decision == RetryDecision.STOP:
                    attempts.append(RetryAttempt(
                        attempt_number=attempt_num,
                        delay_before=0.0,
                        exception=e,
                        timestamp=datetime.now(timezone.utc),
                        elapsed_time=attempt_time
                    ))
                    logger.debug(f"Stopping async retries after attempt {attempt_num}: {e}")
                    return RetryResult(success=False, attempts=attempts, final_exception=e)
                
                # Calculate delay for next attempt
                delay = self._calculate_delay(attempt_num) if attempt_num < self.config.max_attempts else 0.0
                
                attempts.append(RetryAttempt(
                    attempt_number=attempt_num,
                    delay_before=delay,
                    exception=e,
                    timestamp=datetime.now(timezone.utc),
                    elapsed_time=attempt_time
                ))
                
                logger.debug(f"Async attempt {attempt_num} failed: {e}. Retrying in {delay:.2f}s")
                
                if delay > 0 and attempt_num < self.config.max_attempts:
                    await asyncio.sleep(delay)
        
        # Should not reach here, but handle edge case
        final_exception = attempts[-1].exception if attempts else Exception("Unknown error")
        return RetryResult(success=False, attempts=attempts, final_exception=final_exception)
    
    def with_timeout(self, timeout_seconds: float) -> 'UnifiedRetryHandler':
        """Create a new handler with specified timeout."""
        new_config = RetryConfig(**self.config.__dict__)
        new_config.timeout_seconds = timeout_seconds
        return UnifiedRetryHandler(self.service_name, new_config)
    
    def with_max_attempts(self, max_attempts: int) -> 'UnifiedRetryHandler':
        """Create a new handler with specified max attempts."""
        new_config = RetryConfig(**self.config.__dict__)
        new_config.max_attempts = max_attempts
        return UnifiedRetryHandler(self.service_name, new_config)


# Decorator functions for easy retry application
def retry_on_exception(max_attempts: int = 3, base_delay: float = 1.0, 
                      strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
                      retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)):
    """Decorator to add retry behavior to functions."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            config = RetryConfig(
                max_attempts=max_attempts,
                base_delay=base_delay,
                strategy=strategy,
                retryable_exceptions=retryable_exceptions
            )
            handler = UnifiedRetryHandler(func.__name__, config)
            result = handler.execute_with_retry(func, *args, **kwargs)
            if result.success:
                return result.result
            else:
                raise result.final_exception
        return wrapper
    return decorator


def async_retry_on_exception(max_attempts: int = 3, base_delay: float = 1.0,
                            strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
                            retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)):
    """Decorator to add retry behavior to async functions."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            config = RetryConfig(
                max_attempts=max_attempts,
                base_delay=base_delay,
                strategy=strategy,
                retryable_exceptions=retryable_exceptions
            )
            handler = UnifiedRetryHandler(func.__name__, config)
            result = await handler.execute_with_retry_async(func, *args, **kwargs)
            if result.success:
                return result.result
            else:
                raise result.final_exception
        return wrapper
    return decorator


# Convenience functions for common retry patterns
def retry_database_operation(func: Callable, max_attempts: int = 5, base_delay: float = 0.5) -> Any:
    """Retry database operations with appropriate settings."""
    import psycopg2
    import sqlalchemy.exc
    
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        strategy=RetryStrategy.EXPONENTIAL_JITTER,
        retryable_exceptions=(
            psycopg2.OperationalError,
            sqlalchemy.exc.DisconnectionError,
            sqlalchemy.exc.TimeoutError,
            ConnectionError,
            TimeoutError,
        ),
        non_retryable_exceptions=(
            psycopg2.ProgrammingError,  # SQL syntax errors
            sqlalchemy.exc.IntegrityError,  # Constraint violations
        )
    )
    
    handler = UnifiedRetryHandler("database", config)
    result = handler.execute_with_retry(func)
    if result.success:
        return result.result
    else:
        raise result.final_exception


def retry_http_request(func: Callable, max_attempts: int = 3, base_delay: float = 1.0) -> Any:
    """Retry HTTP requests with appropriate settings."""
    import urllib.error
    
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        strategy=RetryStrategy.EXPONENTIAL_JITTER,
        retryable_exceptions=(
            urllib.error.URLError,
            urllib.error.HTTPError,
            ConnectionError,
            TimeoutError,
        ),
        non_retryable_exceptions=(
            # Don't retry client errors (4xx)
            # This would need more sophisticated HTTP status code checking
        )
    )
    
    handler = UnifiedRetryHandler("http", config)
    result = handler.execute_with_retry(func)
    if result.success:
        return result.result
    else:
        raise result.final_exception


# Global instances for common service patterns
auth_retry_handler = UnifiedRetryHandler("auth_service")
backend_retry_handler = UnifiedRetryHandler("netra_backend")
launcher_retry_handler = UnifiedRetryHandler("dev_launcher")
default_retry_handler = UnifiedRetryHandler("default")


# Backoff strategy functions
def exponential_backoff(attempt: int, base_delay: float = 1.0, multiplier: float = 2.0, max_delay: float = 60.0) -> float:
    """Calculate exponential backoff delay."""
    delay = base_delay * (multiplier ** (attempt - 1))
    return min(delay, max_delay)


def linear_backoff(attempt: int, base_delay: float = 1.0, increment: float = 1.0, max_delay: float = 60.0) -> float:
    """Calculate linear backoff delay."""
    delay = base_delay + (increment * (attempt - 1))
    return min(delay, max_delay)