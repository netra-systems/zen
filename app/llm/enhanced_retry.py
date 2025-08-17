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
        configs = self._build_api_configs(kwargs)
        return configs.get(api_type, configs['standard'])
    
    def _build_api_configs(self, kwargs: dict) -> dict:
        """Build API configuration dictionary."""
        return {
            'openai': self._build_openai_config(kwargs),
            'anthropic': self._build_anthropic_config(kwargs),
            'standard': self._build_standard_config(kwargs)
        }
    
    def _build_openai_config(self, kwargs: dict) -> dict:
        """Build OpenAI configuration."""
        return {
            'max_attempts': kwargs.get('max_attempts', 5),
            'base_delay': kwargs.get('base_delay', 2.0),
            'max_delay': kwargs.get('max_delay', 120.0),
            'backoff_factor': kwargs.get('backoff_factor', 2.5)
        }
    
    def _build_anthropic_config(self, kwargs: dict) -> dict:
        """Build Anthropic configuration."""
        return {
            'max_attempts': kwargs.get('max_attempts', 4),
            'base_delay': kwargs.get('base_delay', 1.5),
            'max_delay': kwargs.get('max_delay', 90.0),
            'backoff_factor': kwargs.get('backoff_factor', 2.0)
        }
    
    def _build_standard_config(self, kwargs: dict) -> dict:
        """Build standard configuration."""
        return {
            'max_attempts': kwargs.get('max_attempts', 3),
            'base_delay': kwargs.get('base_delay', 1.0),
            'max_delay': kwargs.get('max_delay', 60.0),
            'backoff_factor': kwargs.get('backoff_factor', 2.0)
        }
    
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
            return await _execute_retry_attempts(func, strategy, *args, **kwargs)
        return wrapper
    return decorator


async def _execute_retry_attempts(func: Callable, strategy: RetryStrategy, *args, **kwargs) -> Any:
    """Execute function with retry attempts strategy."""
    last_error = None
    for attempt in range(1, strategy.max_attempts + 1):
        result = await _try_single_attempt(func, attempt, strategy, *args, **kwargs)
        if result[0]:  # Success
            return result[1]
        last_error = result[1]
    raise last_error

async def _try_single_attempt(func: Callable, attempt: int, strategy: RetryStrategy, *args, **kwargs) -> tuple:
    """Try single attempt and return (success, result_or_error)."""
    try:
        result = await _attempt_function_call(func, attempt, *args, **kwargs)
        return (True, result)
    except Exception as e:
        error = await _handle_retry_attempt_error(e, attempt, strategy)
        return (False, error)


async def _attempt_function_call(func: Callable, attempt: int, *args, **kwargs) -> Any:
    """Attempt function call and log success if retry."""
    result = await func(*args, **kwargs)
    if attempt > 1:
        logger.info(f"Retry successful on attempt {attempt}")
    return result


async def _handle_retry_attempt_error(error: Exception, attempt: int, strategy: RetryStrategy) -> Exception:
    """Handle retry attempt error and return error for re-raise."""
    if not strategy.should_retry(error):
        logger.error(f"Non-retryable error: {error}")
        raise error
    await _process_retryable_error(error, attempt, strategy)
    return error


async def _process_retryable_error(error: Exception, attempt: int, strategy: RetryStrategy) -> None:
    """Process retryable error with delay or final failure."""
    if attempt < strategy.max_attempts:
        await _apply_retry_delay(error, attempt, strategy)
    else:
        _log_final_retry_failure(strategy)


async def _apply_retry_delay(error: Exception, attempt: int, strategy: RetryStrategy) -> None:
    """Apply retry delay with warning log."""
    delay = strategy.calculate_delay(attempt)
    logger.warning(f"Attempt {attempt} failed: {error}. Retrying in {delay:.2f}s...")
    await asyncio.sleep(delay)


def _log_final_retry_failure(strategy: RetryStrategy) -> None:
    """Log final retry failure message."""
    logger.error(f"All {strategy.max_attempts} attempts failed")


class CircuitBreakerRetryStrategy:
    """Combines circuit breaker with retry strategy."""
    
    def __init__(self, retry_strategy: RetryStrategy):
        self.retry_strategy = retry_strategy
        self.consecutive_failures = 0
        self.circuit_open_until: Optional[float] = None
    
    async def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry and circuit breaker."""
        self._check_circuit_state()
        return await self._execute_with_circuit_handling(func, *args, **kwargs)
    
    def _check_circuit_state(self) -> None:
        """Check if circuit breaker is open and raise if needed."""
        if self._is_circuit_open():
            raise Exception("Circuit breaker is open")
    
    async def _execute_with_circuit_handling(self, func: Callable, *args, **kwargs) -> Any:
        """Execute with circuit breaker success/failure handling."""
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
        return self._check_circuit_recovery()
    
    def _check_circuit_recovery(self) -> bool:
        """Check if circuit should recover and return open status."""
        import time
        if time.time() >= self.circuit_open_until:
            self._reset_circuit_state()
            return False
        return True
    
    def _reset_circuit_state(self) -> None:
        """Reset circuit breaker to closed state."""
        self.circuit_open_until = None
        self.consecutive_failures = 0
    
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