"""Async resource management utilities for proper cleanup and task management."""

import asyncio
import functools
import weakref
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Awaitable, Callable, List, Set, TypeVar

from netra_backend.app.async_batch_processor import AsyncBatchProcessor
from netra_backend.app.exceptions_service import ServiceError
from netra_backend.app.error_context import ErrorContext

T = TypeVar('T')


class AsyncResourceManager:
    """Manages async resources with proper cleanup."""
    
    def __init__(self):
        self._resources: Set[Any] = weakref.WeakSet()
        self._cleanup_callbacks: List[Callable[[], Awaitable[None]]] = []
        self._shutting_down = False
    
    def register_resource(
        self, 
        resource: Any, 
        cleanup_callback: Callable[[], Awaitable[None]] = None
    ):
        """Register a resource for cleanup."""
        if not self._shutting_down:
            self._add_resource(resource)
            self._add_cleanup_callback(cleanup_callback)
    
    def _add_resource(self, resource: Any):
        """Add resource to tracked resources."""
        self._resources.add(resource)
    
    def _add_cleanup_callback(self, cleanup_callback: Callable[[], Awaitable[None]]):
        """Add cleanup callback if provided."""
        if cleanup_callback:
            self._cleanup_callbacks.append(cleanup_callback)
    
    async def cleanup_all(self):
        """Clean up all registered resources."""
        if self._shutting_down:
            return
        
        self._shutting_down = True
        await self._run_cleanup_callbacks()
        self._clear_resources()
    
    async def _run_cleanup_callbacks(self):
        """Execute all cleanup callbacks."""
        if self._cleanup_callbacks:
            await asyncio.gather(
                *[callback() for callback in self._cleanup_callbacks], 
                return_exceptions=True
            )
    
    def _clear_resources(self):
        """Clear all resources and callbacks."""
        self._resources.clear()
        self._cleanup_callbacks.clear()
    
    @property
    def resource_count(self) -> int:
        """Get number of tracked resources."""
        return len(self._resources)
    
    @property
    def is_shutting_down(self) -> bool:
        """Check if manager is shutting down."""
        return self._shutting_down


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
            return await self._execute_task(coro)
    
    async def _execute_task(self, coro: Awaitable[T]) -> T:
        """Execute a task and track it."""
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
        self._setup_background_task(task)
        return task
    
    def _setup_background_task(self, task: asyncio.Task[T]):
        """Set up background task tracking."""
        self._active_tasks.add(task)
        task.add_done_callback(self._active_tasks.discard)
    
    async def _run_background_task(self, coro: Awaitable[T]) -> T:
        """Run a background task with resource limits."""
        async with self._semaphore:
            return await coro
    
    @property
    def active_task_count(self) -> int:
        """Get the number of active tasks."""
        return len(self._active_tasks)
    
    @property
    def max_concurrent_tasks(self) -> int:
        """Get maximum concurrent tasks allowed."""
        return self._max_concurrent
    
    @property
    def available_slots(self) -> int:
        """Get number of available task slots."""
        return self._max_concurrent - self.active_task_count
    
    async def shutdown(self, timeout: float = 30.0):
        """Shutdown the task pool gracefully."""
        if self._shutting_down:
            return
        
        self._shutting_down = True
        
        if not self._active_tasks:
            return
        
        await self._cancel_and_wait_for_tasks(timeout)
        self._active_tasks.clear()
    
    async def _cancel_and_wait_for_tasks(self, timeout: float):
        """Cancel all tasks and wait for completion."""
        self._cancel_all_tasks()
        await self._wait_for_task_completion(timeout)
    
    def _cancel_all_tasks(self):
        """Cancel all active tasks."""
        for task in list(self._active_tasks):
            task.cancel()
    
    async def _wait_for_task_completion(self, timeout: float):
        """Wait for tasks to complete with timeout."""
        try:
            await asyncio.wait_for(
                asyncio.gather(*self._active_tasks, return_exceptions=True),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            pass  # Some tasks didn't complete in time



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
    executor = _get_thread_pool_executor()
    return await loop.run_in_executor(
        executor, 
        functools.partial(func, **kwargs), 
        *args
    )


def _get_thread_pool_executor() -> ThreadPoolExecutor:
    """Get or create thread pool executor."""
    if not hasattr(run_in_threadpool, '_executor'):
        run_in_threadpool._executor = ThreadPoolExecutor(max_workers=10)
    return run_in_threadpool._executor


async def shutdown_async_utils():
    """Shutdown all async utilities."""
    await _global_task_pool.shutdown()
    await _global_resource_manager.cleanup_all()
    _shutdown_thread_pool_executor()


def _shutdown_thread_pool_executor():
    """Shutdown thread pool executor if it exists."""
    if hasattr(run_in_threadpool, '_executor'):
        run_in_threadpool._executor.shutdown(wait=True)