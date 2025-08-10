"""Async utilities for proper resource management and optimized async patterns."""

import asyncio
import contextlib
import functools
import time
import weakref
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, List, Optional, Set, TypeVar, Union
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from .exceptions import ServiceTimeoutError, ServiceError
from .error_context import ErrorContext

T = TypeVar('T')


class AsyncResourceManager:
    """Manages async resources with proper cleanup."""
    
    def __init__(self):
        self._resources: Set[Any] = weakref.WeakSet()
        self._cleanup_callbacks: List[Callable[[], Awaitable[None]]] = []
        self._shutting_down = False
    
    def register_resource(self, resource: Any, cleanup_callback: Optional[Callable[[], Awaitable[None]]] = None):
        """Register a resource for cleanup."""
        if not self._shutting_down:
            self._resources.add(resource)
            if cleanup_callback:
                self._cleanup_callbacks.append(cleanup_callback)
    
    async def cleanup_all(self):
        """Clean up all registered resources."""
        if self._shutting_down:
            return
        
        self._shutting_down = True
        
        # Run cleanup callbacks
        if self._cleanup_callbacks:
            await asyncio.gather(*[callback() for callback in self._cleanup_callbacks], return_exceptions=True)
        
        # Clear resources
        self._resources.clear()
        self._cleanup_callbacks.clear()


class AsyncTaskPool:
    """Pool for managing async tasks with limits and cleanup."""
    
    def __init__(self, max_concurrent_tasks: int = 100):
        self._max_concurrent = max_concurrent_tasks
        self._active_tasks: Set[asyncio.Task] = set()
        self._semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self._shutting_down = False
    
    async def submit_task(self, coro: Awaitable[T]) -> T:
        """Submit a task to the pool."""
        if self._shutting_down:
            raise ServiceError(
                message="Task pool is shutting down",
                context=ErrorContext.get_all_context()
            )
        
        async with self._semaphore:
            task = asyncio.create_task(coro)
            self._active_tasks.add(task)
            
            try:
                result = await task
                return result
            finally:
                self._active_tasks.discard(task)
    
    def submit_background_task(self, coro: Awaitable[T]) -> asyncio.Task[T]:
        """Submit a background task (fire and forget)."""
        if self._shutting_down:
            raise ServiceError(
                message="Task pool is shutting down",
                context=ErrorContext.get_all_context()
            )
        
        task = asyncio.create_task(self._run_background_task(coro))
        self._active_tasks.add(task)
        task.add_done_callback(self._active_tasks.discard)
        return task
    
    async def _run_background_task(self, coro: Awaitable[T]) -> T:
        """Run a background task with resource limits."""
        async with self._semaphore:
            return await coro
    
    @property
    def active_task_count(self) -> int:
        """Get the number of active tasks."""
        return len(self._active_tasks)
    
    async def shutdown(self, timeout: float = 30.0):
        """Shutdown the task pool gracefully."""
        if self._shutting_down:
            return
        
        self._shutting_down = True
        
        if not self._active_tasks:
            return
        
        # Cancel all tasks
        for task in list(self._active_tasks):
            task.cancel()
        
        # Wait for tasks to complete with timeout
        try:
            await asyncio.wait_for(
                asyncio.gather(*self._active_tasks, return_exceptions=True),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            pass  # Some tasks didn't complete in time
        
        self._active_tasks.clear()


class AsyncRateLimiter:
    """Rate limiter for async operations."""
    
    def __init__(self, max_calls: int, time_window: float):
        self._max_calls = max_calls
        self._time_window = time_window
        self._calls: List[float] = []
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire permission to make a call."""
        async with self._lock:
            now = time.time()
            
            # Remove old calls outside the time window
            self._calls = [call_time for call_time in self._calls if now - call_time < self._time_window]
            
            # Check if we can make a call
            if len(self._calls) >= self._max_calls:
                # Calculate wait time
                oldest_call = min(self._calls)
                wait_time = self._time_window - (now - oldest_call)
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    return await self.acquire()  # Recursive call after waiting
            
            # Record this call
            self._calls.append(now)


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
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        break
                    
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff_factor
            
            raise last_exception
        return wrapper
    return decorator


class AsyncBatchProcessor:
    """Process items in batches asynchronously."""
    
    def __init__(self, batch_size: int = 10, max_concurrent_batches: int = 5):
        self._batch_size = batch_size
        self._semaphore = asyncio.Semaphore(max_concurrent_batches)
    
    async def process_items(
        self,
        items: List[T],
        processor: Callable[[List[T]], Awaitable[Any]],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Any]:
        """Process items in batches."""
        if not items:
            return []
        
        # Split items into batches
        batches = [items[i:i + self._batch_size] for i in range(0, len(items), self._batch_size)]
        
        # Process batches concurrently
        async def process_batch(batch_items: List[T], batch_index: int) -> Any:
            async with self._semaphore:
                result = await processor(batch_items)
                if progress_callback:
                    progress_callback(batch_index + 1, len(batches))
                return result
        
        tasks = [process_batch(batch, i) for i, batch in enumerate(batches)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for exceptions
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                raise result
            valid_results.append(result)
        
        return valid_results


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
            self._acquired_at = time.time()
            self._acquired_by = ErrorContext.get_trace_id()
            return True
        except asyncio.TimeoutError:
            return False
    
    def release(self):
        """Release the lock."""
        self._acquired_at = None
        self._acquired_by = None
        self._lock.release()
    
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
            "held_for_seconds": time.time() - self._acquired_at if self._acquired_at else None
        }
    
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
        
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
        """Execute function through circuit breaker."""
        async with self._lock:
            if self._state == "OPEN":
                if time.time() - self._last_failure_time < self._timeout:
                    raise ServiceError(
                        message=f"Circuit breaker is OPEN (failed {self._failure_count} times)",
                        context=ErrorContext.get_all_context()
                    )
                else:
                    self._state = "HALF_OPEN"
            
            try:
                result = await func(*args, **kwargs)
                
                # Success - reset failure count
                if self._state == "HALF_OPEN":
                    self._state = "CLOSED"
                self._failure_count = 0
                self._last_failure_time = None
                
                return result
                
            except self._expected_exception as e:
                self._failure_count += 1
                self._last_failure_time = time.time()
                
                if self._failure_count >= self._failure_threshold:
                    self._state = "OPEN"
                
                raise e
    
    @property
    def state(self) -> str:
        """Get current circuit breaker state."""
        return self._state
    
    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._failure_count


class AsyncConnectionPool:
    """Generic async connection pool."""
    
    def __init__(
        self,
        create_connection: Callable[[], Awaitable[T]],
        close_connection: Callable[[T], Awaitable[None]],
        max_size: int = 10,
        min_size: int = 1
    ):
        self._create_connection = create_connection
        self._close_connection = close_connection
        self._max_size = max_size
        self._min_size = min_size
        
        self._available_connections: asyncio.Queue[T] = asyncio.Queue(maxsize=max_size)
        self._active_connections: Set[T] = set()
        self._lock = asyncio.Lock()
        self._closed = False
    
    async def initialize(self):
        """Initialize the connection pool."""
        for _ in range(self._min_size):
            connection = await self._create_connection()
            await self._available_connections.put(connection)
    
    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[T, None]:
        """Acquire a connection from the pool."""
        if self._closed:
            raise ServiceError(message="Connection pool is closed")
        
        connection = None
        try:
            # Try to get an available connection
            try:
                connection = await asyncio.wait_for(self._available_connections.get(), timeout=5.0)
            except asyncio.TimeoutError:
                # Create a new connection if pool isn't full
                async with self._lock:
                    if len(self._active_connections) < self._max_size:
                        connection = await self._create_connection()
                    else:
                        # Wait for a connection to become available
                        connection = await self._available_connections.get()
            
            self._active_connections.add(connection)
            yield connection
            
        finally:
            if connection:
                self._active_connections.discard(connection)
                if not self._closed:
                    try:
                        await self._available_connections.put(connection)
                    except asyncio.QueueFull:
                        # Pool is full, close this connection
                        await self._close_connection(connection)
    
    async def close(self):
        """Close the connection pool."""
        if self._closed:
            return
        
        self._closed = True
        
        # Close all available connections
        while not self._available_connections.empty():
            try:
                connection = await asyncio.wait_for(self._available_connections.get(), timeout=1.0)
                await self._close_connection(connection)
            except asyncio.TimeoutError:
                break
        
        # Close any remaining active connections
        for connection in list(self._active_connections):
            await self._close_connection(connection)
        
        self._active_connections.clear()


# Global instances for common use
_global_resource_manager = AsyncResourceManager()
_global_task_pool = AsyncTaskPool()


def get_global_resource_manager() -> AsyncResourceManager:
    """Get the global resource manager."""
    return _global_resource_manager


def get_global_task_pool() -> AsyncTaskPool:
    """Get the global task pool."""
    return _global_task_pool


async def run_in_threadpool(func: Callable[..., T], *args, **kwargs) -> T:
    """Run a synchronous function in a thread pool."""
    loop = asyncio.get_event_loop()
    
    # Create a thread pool executor if not exists
    if not hasattr(run_in_threadpool, '_executor'):
        run_in_threadpool._executor = ThreadPoolExecutor(max_workers=10)
    
    return await loop.run_in_executor(run_in_threadpool._executor, functools.partial(func, **kwargs), *args)


async def shutdown_async_utils():
    """Shutdown all async utilities."""
    await _global_task_pool.shutdown()
    await _global_resource_manager.cleanup_all()
    
    # Shutdown thread pool executor if it exists
    if hasattr(run_in_threadpool, '_executor'):
        run_in_threadpool._executor.shutdown(wait=True)