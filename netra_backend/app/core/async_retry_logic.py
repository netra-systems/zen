"""Async retry mechanisms and timeout utilities."""

import asyncio
import functools
import time
from contextlib import asynccontextmanager
from typing import Any, Awaitable, Callable, Dict, Optional, TypeVar

from netra_backend.app.exceptions_service import ServiceError, ServiceTimeoutError
from netra_backend.app.error_context import ErrorContext

T = TypeVar('T')


@asynccontextmanager
async def async_timeout(timeout: float, operation_name: str = "operation"):
    """Async context manager for timeout handling."""
    try:
        async with asyncio.timeout(timeout):
            yield
    except asyncio.TimeoutError:
        raise ServiceTimeoutError(
            timeout_seconds=timeout,
            context=ErrorContext.get_all_context()
        )


def with_timeout(timeout: float, operation_name: str = "operation"):
    """Decorator for adding timeout to async functions."""
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            async with async_timeout(timeout, operation_name):
                return await func(*args, **kwargs)
        return wrapper
    return decorator


def with_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """Decorator for adding retry logic to async functions."""
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await _retry_with_backoff(
                func, max_attempts, delay, backoff_factor, exceptions, *args, **kwargs
            )
        return wrapper
    return decorator


async def _retry_with_backoff(
    func: Callable[..., Awaitable[T]],
    max_attempts: int,
    delay: float,
    backoff_factor: float,
    exceptions: tuple,
    *args,
    **kwargs
) -> T:
    """Execute function with retry and exponential backoff."""
    last_exception = None
    current_delay = delay
    
    for attempt in range(max_attempts):
        try:
            return await func(*args, **kwargs)
        except exceptions as e:
            last_exception = e
            if _is_final_attempt(attempt, max_attempts):
                break
            
            await _sleep_with_backoff(current_delay)
            current_delay = _calculate_next_delay(current_delay, backoff_factor)
    
    raise last_exception


def _is_final_attempt(attempt: int, max_attempts: int) -> bool:
    """Check if this is the final retry attempt."""
    return attempt == max_attempts - 1


async def _sleep_with_backoff(delay: float) -> None:
    """Sleep for the specified delay period."""
    await asyncio.sleep(delay)


def _calculate_next_delay(current_delay: float, backoff_factor: float) -> float:
    """Calculate next delay with backoff factor."""
    return current_delay * backoff_factor


class AsyncCircuitBreaker:
    """Circuit breaker pattern for async operations."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        expected_exception: tuple = (Exception,)
    ):
        self._failure_threshold = failure_threshold
        self._timeout = timeout
        self._expected_exception = expected_exception
        self._initialize_state()
    
    def _initialize_state(self):
        """Initialize circuit breaker state."""
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
        """Execute function through circuit breaker."""
        async with self._lock:
            await self._check_and_update_state()
            
            try:
                result = await func(*args, **kwargs)
                self._handle_success()
                return result
            except self._expected_exception as e:
                self._handle_failure()
                raise e
    
    async def _check_and_update_state(self):
        """Check and update circuit breaker state."""
        if self._state == "OPEN":
            if self._should_transition_to_half_open():
                self._state = "HALF_OPEN"
            else:
                raise ServiceError(
                    message=f"Circuit breaker is OPEN (failed {self._failure_count} times)",
                    context=ErrorContext.get_all_context()
                )
    
    def _should_transition_to_half_open(self) -> bool:
        """Check if should transition from OPEN to HALF_OPEN."""
        return time.time() - self._last_failure_time >= self._timeout
    
    def _handle_success(self):
        """Handle successful execution."""
        if self._state == "HALF_OPEN":
            self._state = "CLOSED"
        self._failure_count = 0
        self._last_failure_time = None
    
    def _handle_failure(self):
        """Handle failed execution."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        if self._failure_count >= self._failure_threshold:
            self._state = "OPEN"
    
    @property
    def state(self) -> str:
        """Get current circuit breaker state."""
        return self._state
    
    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._failure_count
    
    @property
    def circuit_info(self) -> Dict[str, Any]:
        """Get circuit breaker information."""
        return {
            "state": self._state,
            "failure_count": self._failure_count,
            "failure_threshold": self._failure_threshold,
            "timeout": self._timeout,
            "last_failure_time": self._last_failure_time
        }


class AsyncLock:
    """Enhanced async lock with timeout and context tracking."""
    
    def __init__(self, name: str = "anonymous"):
        self._lock = asyncio.Lock()
        self._name = name
        self._acquired_at: Optional[float] = None
        self._acquired_by: Optional[str] = None
    
    async def acquire_with_timeout(self, timeout: float = 30.0) -> bool:
        """Acquire lock with timeout."""
        try:
            await asyncio.wait_for(self._lock.acquire(), timeout=timeout)
            self._set_acquisition_info()
            return True
        except asyncio.TimeoutError:
            return False
    
    def _set_acquisition_info(self):
        """Set lock acquisition information."""
        self._acquired_at = time.time()
        self._acquired_by = ErrorContext.get_trace_id()
    
    def release(self):
        """Release the lock."""
        self._clear_acquisition_info()
        self._lock.release()
    
    def _clear_acquisition_info(self):
        """Clear lock acquisition information."""
        self._acquired_at = None
        self._acquired_by = None
    
    @property
    def is_locked(self) -> bool:
        """Check if lock is currently held."""
        return self._lock.locked()
    
    @property
    def lock_info(self) -> Dict[str, Any]:
        """Get information about the lock."""
        return {
            "name": self._name,
            "locked": self.is_locked,
            "acquired_at": self._acquired_at,
            "acquired_by": self._acquired_by,
            "held_for_seconds": self._calculate_held_duration()
        }
    
    def _calculate_held_duration(self) -> Optional[float]:
        """Calculate how long lock has been held."""
        return time.time() - self._acquired_at if self._acquired_at else None
    
    @asynccontextmanager
    async def acquire(self, timeout: float = 30.0):
        """Context manager for lock acquisition."""
        acquired = await self.acquire_with_timeout(timeout)
        if not acquired:
            raise ServiceTimeoutError(
                service_name=f"AsyncLock({self._name})",
                timeout_seconds=timeout,
                context=ErrorContext.get_all_context()
            )
        
        try:
            yield
        finally:
            self.release()