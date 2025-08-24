"""Comprehensive tests for AsyncResourceManager and AsyncTaskPool functionality.

BUSINESS VALUE: Prevents resource leaks and ensures efficient task management,
directly protecting system stability and preventing costly resource waste
that could impact customer AI operations.

Tests critical paths including resource cleanup, task concurrency limits,
background task handling, and shutdown procedures.
"""

import sys
from pathlib import Path

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from netra_backend.app.core.async_resource_manager import (
    AsyncResourceManager,
    AsyncTaskPool,
    get_global_resource_manager,
    get_global_task_pool,
    run_in_threadpool,
    shutdown_async_utils,
)
from netra_backend.app.core.exceptions_service import ServiceError

# Test fixtures for setup
@pytest.fixture
def resource_manager():
    """Fresh AsyncResourceManager instance."""
    return AsyncResourceManager()

@pytest.fixture
def task_pool():
    """AsyncTaskPool with small limit for testing."""
    return AsyncTaskPool(max_concurrent_tasks=3)

@pytest.fixture
def mock_resource():
    """Mock resource for testing."""
    # Mock: Generic component isolation for controlled unit testing
    resource = Mock()
    # Mock: Generic component isolation for controlled unit testing
    resource.cleanup = AsyncMock()
    return resource

@pytest.fixture
async def cleanup_callback():
    """Mock cleanup callback."""
    # Mock: Generic component isolation for controlled unit testing
    callback = AsyncMock()
    yield callback

# Helper functions for 25-line compliance
def assert_resource_count(manager, expected):
    """Assert resource manager has expected resource count."""
    assert manager.resource_count == expected

def assert_shutting_down(manager, expected):
    """Assert manager shutdown state matches expected."""
    assert manager.is_shutting_down == expected

def assert_task_count(pool, expected):
    """Assert task pool has expected active task count.""" 
    assert pool.active_task_count == expected

def assert_available_slots(pool, expected):
    """Assert task pool has expected available slots."""
    assert pool.available_slots == expected

def assert_max_concurrent(pool, expected):
    """Assert task pool has expected max concurrent limit."""
    assert pool.max_concurrent_tasks == expected

async def create_simple_task():
    """Simple async task for testing."""
    await asyncio.sleep(0.01)
    return "task_result"

async def create_slow_task():
    """Slow async task for testing."""
    await asyncio.sleep(0.1)
    return "slow_result"

def create_sync_task():
    """Simple sync task for testing."""
    time.sleep(0.01)
    return "sync_result"

# Core resource manager functionality tests
class TestAsyncResourceManagerBasics:
    """Test basic AsyncResourceManager functionality."""

    def test_resource_manager_initialization(self, resource_manager):
        """Resource manager initializes correctly."""
        assert_resource_count(resource_manager, 0)
        assert_shutting_down(resource_manager, False)
        assert resource_manager._cleanup_callbacks == []

    def test_register_resource_without_callback(self, resource_manager, mock_resource):
        """Resource registration without callback works."""
        resource_manager.register_resource(mock_resource)
        assert_resource_count(resource_manager, 1)

    def test_register_resource_with_callback(self, resource_manager, mock_resource, cleanup_callback):
        """Resource registration with callback works."""
        resource_manager.register_resource(mock_resource, cleanup_callback)
        assert_resource_count(resource_manager, 1)
        assert len(resource_manager._cleanup_callbacks) == 1

    def test_register_resource_during_shutdown(self, resource_manager, mock_resource):
        """Resource registration during shutdown is ignored."""
        resource_manager._shutting_down = True
        resource_manager.register_resource(mock_resource)
        assert_resource_count(resource_manager, 0)

    @pytest.mark.asyncio
    async def test_cleanup_all_basic(self, resource_manager):
        """Basic cleanup_all operation works."""
        await resource_manager.cleanup_all()
        assert_shutting_down(resource_manager, True)
        assert_resource_count(resource_manager, 0)

    @pytest.mark.asyncio
    async def test_cleanup_all_with_callbacks(self, resource_manager, cleanup_callback):
        """cleanup_all executes callbacks."""
        resource_manager._cleanup_callbacks.append(cleanup_callback)
        await resource_manager.cleanup_all()
        cleanup_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_all_idempotent(self, resource_manager):
        """cleanup_all can be called multiple times safely."""
        await resource_manager.cleanup_all()
        await resource_manager.cleanup_all()  # Should not raise
        assert_shutting_down(resource_manager, True)

class TestAsyncTaskPoolBasics:
    """Test basic AsyncTaskPool functionality."""

    def test_task_pool_initialization(self, task_pool):
        """Task pool initializes correctly."""
        assert_max_concurrent(task_pool, 3)
        assert_task_count(task_pool, 0)
        assert_available_slots(task_pool, 3)
        assert task_pool._shutting_down is False

    @pytest.mark.asyncio
    async def test_submit_task_basic(self, task_pool):
        """Basic task submission works."""
        result = await task_pool.submit_task(create_simple_task())
        assert result == "task_result"

    @pytest.mark.asyncio
    async def test_submit_task_updates_count(self, task_pool):
        """Task submission updates active count."""
        # Start a slow task to check counts
        task = asyncio.create_task(task_pool.submit_task(create_slow_task()))
        await asyncio.sleep(0.01)  # Let task start
        assert_task_count(task_pool, 1)
        await task  # Wait for completion
        assert_task_count(task_pool, 0)

    @pytest.mark.asyncio
    async def test_submit_task_during_shutdown(self, task_pool):
        """Task submission during shutdown raises error."""
        task_pool._shutting_down = True
        with pytest.raises(ServiceError, match="Task pool is shutting down"):
            await task_pool.submit_task(create_simple_task())

    @pytest.mark.asyncio
    async def test_submit_background_task(self, task_pool):
        """Background task submission works."""
        task = task_pool.submit_background_task(create_simple_task())
        result = await task
        assert result == "task_result"

    @pytest.mark.asyncio
    async def test_background_task_during_shutdown(self, task_pool):
        """Background task submission during shutdown raises error."""
        task_pool._shutting_down = True
        with pytest.raises(ServiceError, match="Task pool is shutting down"):
            task_pool.submit_background_task(create_simple_task())

class TestConcurrencyControl:
    """Test task pool concurrency control."""

    @pytest.mark.asyncio
    async def test_concurrent_limit_respected(self, task_pool):
        """Concurrent task limit is respected."""
        # Submit 3 slow tasks (at limit)
        tasks = [task_pool.submit_background_task(create_slow_task()) for _ in range(3)]
        await asyncio.sleep(0.01)  # Let tasks start
        
        assert_task_count(task_pool, 3)
        assert_available_slots(task_pool, 0)
        
        # Clean up
        await asyncio.gather(*tasks)

    @pytest.mark.asyncio
    async def test_semaphore_controls_execution(self, task_pool):
        """Semaphore properly controls task execution."""
        start_time = time.time()
        
        # Submit 4 tasks but only 3 can run concurrently
        tasks = [task_pool.submit_task(create_slow_task()) for _ in range(4)]
        results = await asyncio.gather(*tasks)
        
        elapsed = time.time() - start_time
        # Should take at least 0.2s (two batches of 0.1s tasks)
        assert elapsed >= 0.15
        assert all(result == "slow_result" for result in results)

    @pytest.mark.asyncio
    async def test_task_cleanup_after_completion(self, task_pool):
        """Tasks are cleaned up after completion."""
        task = task_pool.submit_background_task(create_simple_task())
        await task
        # Brief wait for cleanup
        await asyncio.sleep(0.01)
        assert_task_count(task_pool, 0)

class TestShutdownProcedures:
    """Test shutdown and cleanup procedures."""

    @pytest.mark.asyncio
    async def test_task_pool_shutdown_empty(self, task_pool):
        """Task pool shutdown with no active tasks."""
        await task_pool.shutdown()
        assert task_pool._shutting_down is True

    @pytest.mark.asyncio
    async def test_task_pool_shutdown_with_tasks(self, task_pool):
        """Task pool shutdown cancels active tasks."""
        # Start some background tasks
        tasks = [task_pool.submit_background_task(create_slow_task()) for _ in range(2)]
        
        # Shutdown should cancel them
        await task_pool.shutdown(timeout=0.1)
        assert task_pool._shutting_down is True
        assert_task_count(task_pool, 0)

    @pytest.mark.asyncio 
    async def test_shutdown_timeout_handling(self, task_pool):
        """Shutdown handles timeout gracefully."""
        # Start a long task
        task_pool.submit_background_task(create_slow_task())
        
        # Shutdown with very short timeout
        start_time = time.time()
        await task_pool.shutdown(timeout=0.01)
        elapsed = time.time() - start_time
        
        # Should not wait longer than timeout
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_shutdown_idempotent(self, task_pool):
        """Shutdown can be called multiple times safely."""
        await task_pool.shutdown()
        await task_pool.shutdown()  # Should not raise
        assert task_pool._shutting_down is True

class TestGlobalInstances:
    """Test global resource manager and task pool instances."""

    def test_get_global_resource_manager(self):
        """Global resource manager is accessible."""
        manager = get_global_resource_manager()
        assert isinstance(manager, AsyncResourceManager)

    def test_get_global_task_pool(self):
        """Global task pool is accessible."""
        pool = get_global_task_pool()
        assert isinstance(pool, AsyncTaskPool)

    def test_global_instances_are_singletons(self):
        """Global instances are singletons."""
        manager1 = get_global_resource_manager()
        manager2 = get_global_resource_manager()
        assert manager1 is manager2
        
        pool1 = get_global_task_pool()
        pool2 = get_global_task_pool()
        assert pool1 is pool2

    @pytest.mark.asyncio
    async def test_shutdown_async_utils(self):
        """shutdown_async_utils works correctly."""
        # This tests the global shutdown function
        await shutdown_async_utils()
        # Should complete without error

class TestThreadPoolExecution:
    """Test thread pool execution functionality."""

    @pytest.mark.asyncio
    async def test_run_in_threadpool_basic(self):
        """Basic thread pool execution works."""
        result = await run_in_threadpool(create_sync_task)
        assert result == "sync_result"

    @pytest.mark.asyncio
    async def test_run_in_threadpool_with_args(self):
        """Thread pool execution with arguments works."""
        async def task_with_args(x, y):
            return x + y
        
        result = await run_in_threadpool(task_with_args, 5, 3)
        assert result == 8

    @pytest.mark.asyncio
    async def test_run_in_threadpool_with_kwargs(self):
        """Thread pool execution with keyword arguments works."""
        async def task_with_kwargs(x, y=10):
            return x * y
        
        result = await run_in_threadpool(task_with_kwargs, 3, y=4)
        assert result == 12

    def test_thread_pool_executor_creation(self):
        """Thread pool executor is created on demand."""
        from netra_backend.app.core.async_resource_manager import (
            _get_thread_pool_executor,
        )
        executor = _get_thread_pool_executor()
        assert isinstance(executor, ThreadPoolExecutor)

    def test_thread_pool_executor_reuse(self):
        """Thread pool executor is reused."""
        from netra_backend.app.core.async_resource_manager import (
            _get_thread_pool_executor,
        )
        executor1 = _get_thread_pool_executor()
        executor2 = _get_thread_pool_executor()
        assert executor1 is executor2

class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_resource_cleanup_with_exceptions(self, resource_manager):
        """Resource cleanup handles exceptions gracefully."""
        # Mock: Async component isolation for testing without real async operations
        failing_callback = AsyncMock(side_effect=Exception("Cleanup failed"))
        resource_manager._cleanup_callbacks.append(failing_callback)
        
        # Should not raise exception
        await resource_manager.cleanup_all()
        failing_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_task_execution_exception_handling(self, task_pool):
        """Task execution properly handles exceptions."""
        async def failing_task():
            raise ValueError("Task failed")
        
        with pytest.raises(ValueError, match="Task failed"):
            await task_pool.submit_task(failing_task())

    @pytest.mark.asyncio
    async def test_background_task_exception_isolation(self, task_pool):
        """Background task exceptions don't affect pool."""
        async def failing_task():
            raise ValueError("Background task failed")
        
        task = task_pool.submit_background_task(failing_task())
        
        # Task should complete with exception, but pool should be fine
        with pytest.raises(ValueError):
            await task
        
        # Pool should still work for new tasks
        result = await task_pool.submit_task(create_simple_task())
        assert result == "task_result"

    def test_resource_manager_weak_references(self, resource_manager):
        """Resource manager uses weak references."""
        # This is a challenging test due to weak references
        # We mainly verify that the WeakSet behaves correctly
        # Mock: Generic component isolation for controlled unit testing
        mock_resource = Mock()
        resource_manager.register_resource(mock_resource)
        assert_resource_count(resource_manager, 1)
        
        # When resource goes out of scope, it should be cleaned up automatically
        del mock_resource
        # Force garbage collection in test would be needed for full verification

class TestPerformanceAndScaling:
    """Test performance characteristics and scaling."""

    @pytest.mark.asyncio
    async def test_many_quick_tasks(self, task_pool):
        """Many quick tasks execute efficiently."""
        tasks = [task_pool.submit_task(create_simple_task()) for _ in range(10)]
        results = await asyncio.gather(*tasks)
        assert all(result == "task_result" for result in results)

    @pytest.mark.asyncio
    async def test_task_pool_capacity_management(self):
        """Task pool manages capacity correctly."""
        large_pool = AsyncTaskPool(max_concurrent_tasks=10)
        
        # Start many background tasks
        tasks = [large_pool.submit_background_task(create_slow_task()) for _ in range(5)]
        await asyncio.sleep(0.01)  # Let tasks start
        
        assert_task_count(large_pool, 5)
        assert_available_slots(large_pool, 5)
        
        # Clean up
        await asyncio.gather(*tasks)
        await large_pool.shutdown()

    def test_large_resource_count(self, resource_manager):
        """Resource manager handles many resources."""
        # Mock: Generic component isolation for controlled unit testing
        resources = [Mock() for _ in range(100)]
        for resource in resources:
            resource_manager.register_resource(resource)
        assert_resource_count(resource_manager, 100)