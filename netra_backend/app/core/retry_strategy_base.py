"""
Base retry strategy implementation with backoff and jitter calculations.
Provides core retry functionality with configurable backoff strategies.
"""

import random
from abc import abstractmethod

from netra_backend.app.core.retry_strategy_types import (
    RetryHistoryMixin,
    RetryStrategyInterface,
)
from netra_backend.app.schemas.shared_types import (
    BackoffStrategy,
    JitterType,
    RetryConfig,
)


class EnhancedRetryStrategy(RetryStrategyInterface, RetryHistoryMixin):
    """Base class for enhanced retry strategies."""
    
    def __init__(self, config: RetryConfig):
        """Initialize retry strategy."""
        super().__init__()
        self.config = config
    
    @abstractmethod
    def should_retry(self, context) -> bool:
        """Determine if operation should be retried."""
        pass
    
    def get_retry_delay(self, retry_count: int) -> float:
        """Calculate delay before next retry."""
        base_delay = self._calculate_base_delay(retry_count)
        jittered_delay = self._apply_jitter(base_delay, retry_count)
        return min(jittered_delay, self.config.max_delay)
    
    def _calculate_base_delay(self, retry_count: int) -> float:
        """Calculate base delay based on backoff strategy."""
        strategy_map = self._get_strategy_map()
        calculator = strategy_map.get(
            self.config.backoff_strategy, 
            self._get_default_calculator()
        )
        return calculator(retry_count)
    
    def _get_strategy_map(self):
        """Get mapping of strategies to calculators."""
        return {
            BackoffStrategy.EXPONENTIAL: self._calculate_exponential_delay,
            BackoffStrategy.LINEAR: self._calculate_linear_delay,
            BackoffStrategy.FIBONACCI: self._calculate_fibonacci_delay
        }
    
    def _get_default_calculator(self):
        """Get default delay calculator."""
        return lambda x: self.config.base_delay
    
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
        jitter_map = self._get_jitter_map()
        jitter_func = jitter_map.get(self.config.jitter_type, self._no_jitter)
        return jitter_func(delay, retry_count)
    
    def _get_jitter_map(self):
        """Get mapping of jitter types to functions."""
        return {
            JitterType.NONE: self._no_jitter,
            JitterType.FULL: self._full_jitter,
            JitterType.EQUAL: self._equal_jitter,
            JitterType.DECORRELATED: self._decorrelated_jitter
        }
    
    def _no_jitter(self, delay: float, retry_count: int) -> float:
        """No jitter applied."""
        return delay
    
    def _full_jitter(self, delay: float, retry_count: int) -> float:
        """Apply full jitter to delay."""
        return random.uniform(0, delay)
    
    def _equal_jitter(self, delay: float, retry_count: int) -> float:
        """Apply equal jitter to delay."""
        return delay * 0.5 + random.uniform(0, delay * 0.5)
    
    def _decorrelated_jitter(self, delay: float, retry_count: int) -> float:
        """Apply decorrelated jitter to delay."""
        previous_delay = self._get_previous_delay(delay, retry_count)
        return random.uniform(self.config.base_delay, previous_delay * 3)
    
    def _get_previous_delay(self, delay: float, retry_count: int) -> float:
        """Get previous delay for decorrelated jitter."""
        return delay if retry_count == 0 else delay / 2
    
    def _fibonacci(self, n: int) -> int:
        """Calculate fibonacci number."""
        if n <= 1:
            return n
        return self._fibonacci_iterative(n)
    
    def _fibonacci_iterative(self, n: int) -> int:
        """Calculate fibonacci number iteratively."""
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b