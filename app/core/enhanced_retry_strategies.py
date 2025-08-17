"""Enhanced retry strategies with exponential backoff, jitter, and adaptive patterns.

Provides sophisticated retry mechanisms for different failure scenarios with
configurable backoff strategies and failure pattern recognition.
"""

import asyncio
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

from app.core.error_recovery import RecoveryContext, OperationType
from app.core.error_codes import ErrorSeverity
from app.schemas.shared_types import RetryConfig
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class BackoffStrategy(Enum):
    """Types of backoff strategies for retries."""
    EXPONENTIAL = "exponential"
    LINEAR = "linear" 
    FIXED = "fixed"
    FIBONACCI = "fibonacci"


class JitterType(Enum):
    """Types of jitter to add to retry delays."""
    NONE = "none"
    FULL = "full"
    EQUAL = "equal"
    DECORRELATED = "decorrelated"


# RetryConfig now imported from shared_types.py
# Additional fields for enhanced retry functionality
@dataclass
class EnhancedRetryConfig:
    """Enhanced configuration extending the base RetryConfig."""
    base_config: RetryConfig
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    jitter_type: JitterType = JitterType.FULL


class EnhancedRetryStrategy(ABC):
    """Base class for enhanced retry strategies."""
    
    def __init__(self, config: RetryConfig):
        """Initialize retry strategy."""
        self.config = config
        self.attempt_history: Dict[str, List[datetime]] = {}
    
    @abstractmethod
    def should_retry(self, context: RecoveryContext) -> bool:
        """Determine if operation should be retried."""
        pass
    
    def get_retry_delay(self, retry_count: int) -> float:
        """Calculate delay before next retry."""
        base_delay = self._calculate_base_delay(retry_count)
        jittered_delay = self._apply_jitter(base_delay, retry_count)
        return min(jittered_delay, self.config.max_delay)
    
    def _calculate_base_delay(self, retry_count: int) -> float:
        """Calculate base delay based on backoff strategy."""
        strategy = self.config.backoff_strategy
        delay_map = {
            BackoffStrategy.EXPONENTIAL: self._calculate_exponential_delay,
            BackoffStrategy.LINEAR: self._calculate_linear_delay,
            BackoffStrategy.FIBONACCI: self._calculate_fibonacci_delay
        }
        return delay_map.get(strategy, lambda x: self.config.base_delay)(retry_count)
    
    def _calculate_exponential_delay(self, retry_count: int) -> float:
        """Calculate exponential backoff delay."""
        return self.config.base_delay * (2 ** retry_count)
    
    def _calculate_linear_delay(self, retry_count: int) -> float:
        """Calculate linear backoff delay."""
        return self.config.base_delay * (retry_count + 1)
    
    def _calculate_fibonacci_delay(self, retry_count: int) -> float:
        """Calculate fibonacci backoff delay."""
        return self.config.base_delay * self._fibonacci(retry_count + 1)
    
    def _apply_jitter(self, delay: float, retry_count: int) -> float:
        """Apply jitter to delay."""
        jitter_map = {
            JitterType.NONE: lambda d, _: d,
            JitterType.FULL: lambda d, _: self._apply_full_jitter(d),
            JitterType.EQUAL: lambda d, _: self._apply_equal_jitter(d),
            JitterType.DECORRELATED: self._apply_decorrelated_jitter
        }
        jitter_func = jitter_map.get(self.config.jitter_type, lambda d, _: d)
        return jitter_func(delay, retry_count)
    
    def _apply_full_jitter(self, delay: float) -> float:
        """Apply full jitter to delay."""
        return random.uniform(0, delay)
    
    def _apply_equal_jitter(self, delay: float) -> float:
        """Apply equal jitter to delay."""
        return delay * 0.5 + random.uniform(0, delay * 0.5)
    
    def _apply_decorrelated_jitter(self, delay: float, retry_count: int) -> float:
        """Apply decorrelated jitter to delay."""
        previous_delay = delay if retry_count == 0 else delay / 2
        return random.uniform(self.config.base_delay, previous_delay * 3)
    
    def _fibonacci(self, n: int) -> int:
        """Calculate fibonacci number."""
        if n <= 1:
            return n
        return self._fibonacci_iterative(n)
    
    def record_attempt(self, operation_id: str) -> None:
        """Record retry attempt."""
        if operation_id not in self.attempt_history:
            self.attempt_history[operation_id] = []
        self.attempt_history[operation_id].append(datetime.now())
    
    def _fibonacci_iterative(self, n: int) -> int:
        """Calculate fibonacci number iteratively."""
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b


class DatabaseRetryStrategy(EnhancedRetryStrategy):
    """Specialized retry strategy for database operations."""
    
    def should_retry(self, context: RecoveryContext) -> bool:
        """Determine if database operation should be retried."""
        if context.retry_count >= self.config.max_retries:
            return False
        
        error_msg = str(context.error).lower()
        return self._evaluate_database_retry_conditions(error_msg, context)
    
    def _evaluate_database_retry_conditions(self, error_msg: str, context: RecoveryContext) -> bool:
        """Evaluate specific database retry conditions."""
        if self._is_connection_issue(error_msg) or self._is_temporary_database_issue(error_msg):
            return True
        if self._is_constraint_violation(error_msg):
            return False
        return context.severity != ErrorSeverity.CRITICAL
    
    def _is_connection_issue(self, error_msg: str) -> bool:
        """Check if error indicates connection issues."""
        return any(term in error_msg for term in ['connection', 'timeout', 'network'])
    
    def _is_constraint_violation(self, error_msg: str) -> bool:
        """Check if error indicates constraint violations."""
        return any(term in error_msg for term in ['constraint', 'unique', 'foreign key'])
    
    def _is_temporary_database_issue(self, error_msg: str) -> bool:
        """Check if error indicates temporary database issues."""
        return any(term in error_msg for term in ['deadlock', 'lock timeout', 'busy'])


class ApiRetryStrategy(EnhancedRetryStrategy):
    """Specialized retry strategy for API operations."""
    
    def should_retry(self, context: RecoveryContext) -> bool:
        """Determine if API operation should be retried."""
        if context.retry_count >= self.config.max_retries:
            return False
        
        status_code = context.metadata.get('status_code')
        if status_code:
            return self._should_retry_based_on_status_code(status_code)
        return self._should_retry_based_on_error_message(context.error)
    
    def _should_retry_based_on_status_code(self, status_code: int) -> bool:
        """Determine retry based on HTTP status code."""
        server_errors = [429, 500, 502, 503, 504]
        client_errors = range(400, 500)
        if status_code in server_errors:
            return True
        return status_code not in client_errors
    
    def _should_retry_based_on_error_message(self, error: Exception) -> bool:
        """Determine retry based on error message."""
        error_msg = str(error).lower()
        return any(term in error_msg for term in ['timeout', 'connection', 'network'])


class MemoryAwareRetryStrategy(EnhancedRetryStrategy):
    """Retry strategy that considers memory pressure."""
    
    def __init__(self, config: RetryConfig, memory_threshold: float = 0.8):
        """Initialize with memory threshold."""
        super().__init__(config)
        self.memory_threshold = memory_threshold
    
    def should_retry(self, context: RecoveryContext) -> bool:
        """Check if retry is safe considering memory usage."""
        if context.retry_count >= self.config.max_retries:
            return False
        if self._memory_prevents_retry():
            return False
        error_msg = str(context.error).lower()
        if 'memory' in error_msg:
            return False
        return context.severity != ErrorSeverity.CRITICAL
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage percentage."""
        try:
            import psutil
            return psutil.virtual_memory().percent / 100.0
        except ImportError:
            # Fallback if psutil not available
            return 0.5
    
    def _memory_prevents_retry(self) -> bool:
        """Check if memory usage prevents retry."""
        if self._get_memory_usage() > self.memory_threshold:
            logger.warning(f"Skipping retry due to high memory usage")
            return True
        return False


class AdaptiveRetryStrategy(EnhancedRetryStrategy):
    """Adaptive retry strategy that learns from failure patterns."""
    
    def __init__(self, config: RetryConfig):
        """Initialize adaptive strategy."""
        super().__init__(config)
        self.failure_patterns: Dict[str, int] = {}
        self.success_patterns: Dict[str, int] = {}
    
    def should_retry(self, context: RecoveryContext) -> bool:
        """Adaptive retry decision based on historical patterns."""
        if context.retry_count >= self.config.max_retries:
            return False
        error_pattern = self._extract_error_pattern(context.error)
        failure_rate = self._get_pattern_failure_rate(error_pattern)
        self._adjust_retry_limits_based_on_failure_rate(failure_rate)
        return context.severity != ErrorSeverity.CRITICAL
    
    def record_success(self, error_pattern: str) -> None:
        """Record successful retry for pattern learning."""
        self.success_patterns[error_pattern] = (
            self.success_patterns.get(error_pattern, 0) + 1
        )
    
    def record_failure(self, error_pattern: str) -> None:
        """Record failed retry for pattern learning."""
        self.failure_patterns[error_pattern] = (
            self.failure_patterns.get(error_pattern, 0) + 1
        )
    
    def _extract_error_pattern(self, error: Exception) -> str:
        """Extract pattern from error for classification."""
        error_type = type(error).__name__
        error_msg = str(error).lower()
        key_terms = ['connection', 'timeout', 'memory', 'permission', 'not found']
        pattern_terms = [term for term in key_terms if term in error_msg]
        return f"{error_type}:{':'.join(pattern_terms)}"
    
    def _get_pattern_failure_rate(self, pattern: str) -> float:
        """Calculate failure rate for error pattern."""
        failures = self.failure_patterns.get(pattern, 0)
        successes = self.success_patterns.get(pattern, 0)
        total = failures + successes
        
        return failures / total if total > 0 else 0.5
    
    def _adjust_retry_limits_based_on_failure_rate(self, failure_rate: float) -> None:
        """Adjust retry limits based on historical failure rate."""
        if failure_rate > 0.8:  # High failure rate
            self.config.max_retries = min(self.config.max_retries, 2)
        elif failure_rate < 0.3:  # Low failure rate
            self.config.max_retries = min(self.config.max_retries + 1, 5)


class RetryStrategyFactory:
    """Factory for creating retry strategies."""
    
    @staticmethod
    def create_strategy(
        operation_type: OperationType,
        config: Optional[RetryConfig] = None
    ) -> EnhancedRetryStrategy:
        """Create appropriate retry strategy for operation type."""
        if config is None:
            config = RetryConfig()
        
        if operation_type in [OperationType.DATABASE_READ, OperationType.DATABASE_WRITE]:
            return DatabaseRetryStrategy(config)
        elif operation_type == OperationType.EXTERNAL_API:
            return ApiRetryStrategy(config)
        elif operation_type == OperationType.AGENT_EXECUTION:
            return MemoryAwareRetryStrategy(config)
        else:
            return AdaptiveRetryStrategy(config)


# Default retry configurations for different operations
DEFAULT_RETRY_CONFIGS = {
    OperationType.DATABASE_READ: RetryConfig(
        max_retries=3,
        base_delay=0.1,
        backoff_strategy=BackoffStrategy.EXPONENTIAL,
        jitter_type=JitterType.EQUAL
    ),
    OperationType.DATABASE_WRITE: RetryConfig(
        max_retries=2,
        base_delay=0.5,
        backoff_strategy=BackoffStrategy.LINEAR,
        jitter_type=JitterType.FULL
    ),
    OperationType.EXTERNAL_API: RetryConfig(
        max_retries=4,
        base_delay=1.0,
        max_delay=60.0,
        backoff_strategy=BackoffStrategy.EXPONENTIAL,
        jitter_type=JitterType.DECORRELATED
    ),
    OperationType.LLM_REQUEST: RetryConfig(
        max_retries=3,
        base_delay=2.0,
        max_delay=120.0,
        backoff_strategy=BackoffStrategy.FIBONACCI,
        jitter_type=JitterType.FULL
    ),
    OperationType.WEBSOCKET_SEND: RetryConfig(
        max_retries=2,
        base_delay=0.1,
        backoff_strategy=BackoffStrategy.FIXED,
        jitter_type=JitterType.NONE
    ),
    OperationType.AGENT_EXECUTION: RetryConfig(
        max_retries=2,
        base_delay=1.0,
        backoff_strategy=BackoffStrategy.EXPONENTIAL,
        jitter_type=JitterType.EQUAL
    )
}


# Global retry manager for centralized strategy management
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
        cache_key = f"{operation_type.value}:{operation_id or 'default'}"
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
        strategy_types = {
            strategy_id: type(strategy).__name__
            for strategy_id, strategy in self.strategies.items()
        }
        return {
            'total_metrics': self.metrics,
            'active_strategies': len(self.strategies),
            'strategy_types': strategy_types
        }
    
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


# Global retry manager instance
retry_manager = RetryManager()


def _should_retry_exception(
    exception: Exception, 
    exception_classifier: Optional[Callable], 
    retry_count: int, 
    max_retries: int
) -> bool:
    """Check if exception should be retried."""
    if exception_classifier and not exception_classifier(exception):
        return False
    return retry_count < max_retries


def _calculate_retry_delay(retry_config: RetryConfig, retry_count: int) -> float:
    """Calculate delay with exponential backoff."""
    base_delay = retry_config.base_delay * (2 ** retry_count)
    return min(base_delay, retry_config.max_delay)


def _log_retry_attempt(
    logger: Optional[Any], 
    delay: float, 
    retry_count: int, 
    max_retries: int, 
    exception: Exception
) -> None:
    """Log retry attempt information."""
    if logger:
        logger.warning(
            f"Retrying after {delay}s (attempt {retry_count + 1}/{max_retries}): {exception}"
        )


def _log_max_retries_exceeded(logger: Optional[Any], max_retries: int, exception: Exception) -> None:
    """Log when max retries are exceeded."""
    if logger:
        logger.error(f"Max retries ({max_retries}) exceeded: {exception}")


def _log_non_retryable_exception(logger: Optional[Any], exception: Exception) -> None:
    """Log non-retryable exception."""
    if logger:
        logger.error(f"Non-retryable exception: {exception}")


def _add_retry_metadata_to_result(result: Any, retry_count: int) -> None:
    """Add retry metadata to result if possible."""
    if hasattr(result, '__dict__'):
        result.retry_count = retry_count


async def _execute_generator_with_metadata(
    async_generator_func: AsyncGenerator, 
    retry_count: int
) -> AsyncGenerator:
    """Execute generator and add retry metadata to results."""
    async for result in async_generator_func:
        _add_retry_metadata_to_result(result, retry_count)
        yield result
        return


async def _handle_retryable_exception(
    exception: Exception,
    exception_classifier: Optional[Callable],
    retry_count: int,
    retry_config: RetryConfig,
    logger: Optional[Any]
) -> None:
    """Handle retryable exception logic."""
    if not _should_retry_exception(exception, exception_classifier, retry_count, retry_config.max_retries):
        raise
    if retry_count >= retry_config.max_retries:
        _log_max_retries_exceeded(logger, retry_config.max_retries, exception)
        raise
    delay = _calculate_retry_delay(retry_config, retry_count)
    _log_retry_attempt(logger, delay, retry_count, retry_config.max_retries, exception)
    await asyncio.sleep(delay)


async def _execute_retry_attempt(
    async_generator_func: AsyncGenerator,
    retry_count: int,
    retry_config: RetryConfig,
    retryable_exceptions: tuple,
    exception_classifier: Optional[Callable],
    logger: Optional[Any]
) -> tuple[bool, Optional[Exception], Any]:
    """Execute single retry attempt."""
    try:
        async for result in _execute_generator_with_metadata(async_generator_func, retry_count):
            return True, None, result
    except retryable_exceptions as e:
        await _handle_retryable_exception(e, exception_classifier, retry_count, retry_config, logger)
        return False, e, None
    except Exception as e:
        _log_non_retryable_exception(logger, e)
        raise


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
        success, exception, result = await _execute_retry_attempt(
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