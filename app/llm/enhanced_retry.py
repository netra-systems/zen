"""Enhanced retry strategies for LLM operations.

Provides advanced retry mechanisms with exponential backoff,
jitter, and API-specific error handling.
"""

import asyncio
import random
from typing import Any, Callable, Optional, Tuple, TypeVar
from functools import wraps

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

T = TypeVar('T')


class RetryStrategy:
    """Advanced retry strategy with jitter and backoff."""
    
    def __init__(self, 
                 max_attempts: int = 5,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 backoff_factor: float = 2.0,
                 jitter_range: Tuple[float, float] = (0.5, 1.5)):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter_range = jitter_range
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter."""
        base = self._calculate_base_delay(attempt)
        jittered = self._apply_jitter(base)
        return min(jittered, self.max_delay)
    
    def _calculate_base_delay(self, attempt: int) -> float:
        """Calculate base delay with exponential backoff."""
        return self.base_delay * (self.backoff_factor ** (attempt - 1))
    
    def _apply_jitter(self, delay: float) -> float:
        """Apply random jitter to delay."""
        jitter_factor = random.uniform(*self.jitter_range)
        return delay * jitter_factor
    
    def should_retry(self, error: Exception) -> bool:
        """Determine if error is retryable."""
        error_msg = str(error).lower()
        return self._is_retryable_error(error_msg)
    
    def _is_retryable_error(self, error_msg: str) -> bool:
        """Check if error message indicates retryable condition."""
        retryable_patterns = [
            'overloaded', 'rate limit', 'timeout',
            '429', '503', '504', 'temporarily'
        ]
        return any(pattern in error_msg for pattern in retryable_patterns)


class APISpecificRetryStrategy(RetryStrategy):
    """API-specific retry strategy with custom handling."""
    
    def __init__(self, api_type: str = 'standard', **kwargs):
        self.api_type = api_type
        super().__init__(**self._get_config_for_api(api_type, kwargs))
    
    def _get_config_for_api(self, api_type: str, kwargs: dict) -> dict:
        """Get retry configuration for specific API type."""
        configs = {
            'openai': {
                'max_attempts': kwargs.get('max_attempts', 5),
                'base_delay': kwargs.get('base_delay', 2.0),
                'max_delay': kwargs.get('max_delay', 120.0),
                'backoff_factor': kwargs.get('backoff_factor', 2.5)
            },
            'anthropic': {
                'max_attempts': kwargs.get('max_attempts', 4),
                'base_delay': kwargs.get('base_delay', 1.5),
                'max_delay': kwargs.get('max_delay', 90.0),
                'backoff_factor': kwargs.get('backoff_factor', 2.0)
            },
            'standard': {
                'max_attempts': kwargs.get('max_attempts', 3),
                'base_delay': kwargs.get('base_delay', 1.0),
                'max_delay': kwargs.get('max_delay', 60.0),
                'backoff_factor': kwargs.get('backoff_factor', 2.0)
            }
        }
        return configs.get(api_type, configs['standard'])
    
    def should_retry(self, error: Exception) -> bool:
        """API-specific retry decision."""
        if not super().should_retry(error):
            return False
        return self._check_api_specific_conditions(error)
    
    def _check_api_specific_conditions(self, error: Exception) -> bool:
        """Check API-specific retry conditions."""
        error_msg = str(error)
        if '401' in error_msg or 'unauthorized' in error_msg.lower():
            return False  # Don't retry auth errors
        if '400' in error_msg or 'bad request' in error_msg.lower():
            return False  # Don't retry bad requests
        return True


def with_enhanced_retry(strategy: Optional[RetryStrategy] = None):
    """Decorator for enhanced retry with custom strategy."""
    if strategy is None:
        strategy = RetryStrategy()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_error = None
            for attempt in range(1, strategy.max_attempts + 1):
                try:
                    result = await func(*args, **kwargs)
                    if attempt > 1:
                        logger.info(f"Retry successful on attempt {attempt}")
                    return result
                except Exception as e:
                    last_error = e
                    if not strategy.should_retry(e):
                        logger.error(f"Non-retryable error: {e}")
                        raise
                    if attempt < strategy.max_attempts:
                        delay = strategy.calculate_delay(attempt)
                        logger.warning(
                            f"Attempt {attempt} failed: {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"All {strategy.max_attempts} attempts failed")
            raise last_error
        return wrapper
    return decorator


class CircuitBreakerRetryStrategy:
    """Combines circuit breaker with retry strategy."""
    
    def __init__(self, retry_strategy: RetryStrategy):
        self.retry_strategy = retry_strategy
        self.consecutive_failures = 0
        self.circuit_open_until: Optional[float] = None
    
    async def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry and circuit breaker."""
        if self._is_circuit_open():
            raise Exception("Circuit breaker is open")
        
        try:
            result = await self._execute_with_strategy(func, *args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    async def _execute_with_strategy(self, func: Callable, *args, **kwargs) -> Any:
        """Execute with retry strategy."""
        @with_enhanced_retry(self.retry_strategy)
        async def wrapped():
            return await func(*args, **kwargs)
        return await wrapped()
    
    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is open."""
        if self.circuit_open_until is None:
            return False
        import time
        if time.time() >= self.circuit_open_until:
            self.circuit_open_until = None
            self.consecutive_failures = 0
            return False
        return True
    
    def _on_success(self) -> None:
        """Handle successful execution."""
        self.consecutive_failures = 0
    
    def _on_failure(self) -> None:
        """Handle failed execution."""
        self.consecutive_failures += 1
        if self.consecutive_failures >= 5:
            import time
            self.circuit_open_until = time.time() + 30
            logger.error("Circuit breaker opened due to consecutive failures")


# Pre-configured strategies
FAST_LLM_RETRY = APISpecificRetryStrategy('standard', max_attempts=3, base_delay=0.5)
STANDARD_LLM_RETRY = APISpecificRetryStrategy('standard', max_attempts=5, base_delay=1.0)
SLOW_LLM_RETRY = APISpecificRetryStrategy('standard', max_attempts=7, base_delay=2.0)
OPENAI_RETRY = APISpecificRetryStrategy('openai')
ANTHROPIC_RETRY = APISpecificRetryStrategy('anthropic')