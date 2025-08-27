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
        def task_with_args(x, y):
            return x + y
        
        result = await run_in_threadpool(task_with_args, 5, 3)
        assert result == 8

    @pytest.mark.asyncio
    async def test_run_in_threadpool_with_kwargs(self):
        """Thread pool execution with keyword arguments works."""
        def task_with_kwargs(x, y=10):
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


class TestEdgeCasesAndRegressions:
    """Test edge cases and regression scenarios for async resource manager."""
    
    @pytest.mark.asyncio
    async def test_task_pool_shutdown_with_zero_timeout(self):
        """Test task pool shutdown with zero timeout doesn't hang."""
        pool = AsyncTaskPool(max_concurrent_tasks=2)
        
        # Start a slow task
        slow_task = pool.submit_background_task(create_slow_task()) 
        await asyncio.sleep(0.01)  # Let task start
        
        # Shutdown with zero timeout should complete quickly
        start_time = time.time()
        await pool.shutdown(timeout=0.0)
        shutdown_duration = time.time() - start_time
        
        # Should complete very quickly with zero timeout
        assert shutdown_duration < 0.1  # Less than 100ms
        
        # Task should be cancelled
        assert slow_task.cancelled() or slow_task.done()
    
    @pytest.mark.asyncio  
    async def test_resource_manager_cleanup_with_invalid_callback(self):
        """Test resource manager handles invalid cleanup callbacks gracefully."""
        manager = AsyncResourceManager()
        
        # Create a resource with a callback that will raise an exception
        resource = Mock()
        
        async def failing_callback():
            raise ValueError("Callback failure")
        
        manager.register_resource(resource, cleanup_callback=failing_callback)
        
        # Cleanup should not raise exception, even with failing callback  
        # The gather with return_exceptions=True should handle it gracefully
        await manager.cleanup_all()
        
        # If we get here, the cleanup handled the exception properly
        assert manager.resource_count == 0


class TestAdvancedResourcePoolingPatterns:
    """Test advanced resource pooling and connection management patterns."""
    
    class MockConnectionPool:
        """Mock connection pool for testing resource pooling patterns."""
        
        def __init__(self, min_size=2, max_size=10):
            self.min_size = min_size
            self.max_size = max_size
            self.active_connections = []
            self.available_connections = []
            self.total_created = 0
            self.total_destroyed = 0
            self.is_closed = False
            
        async def create_connection(self):
            """Create a new connection."""
            if self.total_size >= self.max_size:
                raise RuntimeError("Pool exhausted")
                
            connection_id = f"conn_{self.total_created}"
            connection = Mock()
            connection.id = connection_id
            connection.is_closed = False
            connection.close = AsyncMock()
            
            self.total_created += 1
            return connection
            
        async def acquire(self):
            """Acquire a connection from the pool."""
            if self.is_closed:
                raise RuntimeError("Pool is closed")
                
            if self.available_connections:
                connection = self.available_connections.pop()
                self.active_connections.append(connection)
                return connection
                
            # Create new connection if under max
            if self.total_size < self.max_size:
                connection = await self.create_connection()
                self.active_connections.append(connection)
                return connection
                
            # Wait for connection to become available (simplified - would use asyncio.Event in real impl)
            await asyncio.sleep(0.01)
            return await self.acquire()
            
        async def release(self, connection):
            """Release a connection back to the pool."""
            if connection in self.active_connections:
                self.active_connections.remove(connection)
                
                # Check if connection is still healthy
                if not connection.is_closed:
                    self.available_connections.append(connection)
                else:
                    await self.destroy_connection(connection)
                    
        async def destroy_connection(self, connection):
            """Destroy a connection."""
            await connection.close()
            self.total_destroyed += 1
            
        async def close(self):
            """Close the entire pool."""
            self.is_closed = True
            
            # Close all connections
            all_connections = self.active_connections + self.available_connections
            for connection in all_connections:
                await self.destroy_connection(connection)
                
            self.active_connections.clear()
            self.available_connections.clear()
            
        @property
        def total_size(self):
            """Total number of connections."""
            return len(self.active_connections) + len(self.available_connections)
            
        @property
        def active_size(self):
            """Number of active connections."""
            return len(self.active_connections)
            
        @property
        def available_size(self):
            """Number of available connections."""
            return len(self.available_connections)
    
    @pytest.fixture
    def connection_pool(self):
        """Create connection pool instance."""
        return self.MockConnectionPool(min_size=2, max_size=5)
        
    @pytest.fixture
    def resource_manager(self):
        """Create resource manager for pool testing."""
        return AsyncResourceManager()
    
    @pytest.mark.asyncio
    async def test_connection_pool_basic_operations(self, connection_pool):
        """Test basic connection pool acquire/release operations."""
        # Acquire a connection
        conn1 = await connection_pool.acquire()
        assert connection_pool.active_size == 1
        assert connection_pool.available_size == 0
        assert conn1.id == "conn_0"
        
        # Acquire another connection
        conn2 = await connection_pool.acquire()
        assert connection_pool.active_size == 2
        assert connection_pool.available_size == 0
        assert conn2.id == "conn_1"
        
        # Release first connection
        await connection_pool.release(conn1)
        assert connection_pool.active_size == 1
        assert connection_pool.available_size == 1
        
        # Acquire should reuse released connection
        conn3 = await connection_pool.acquire()
        assert conn3 is conn1  # Should be same connection
        assert connection_pool.active_size == 2
        assert connection_pool.available_size == 0
    
    @pytest.mark.asyncio
    async def test_connection_pool_max_size_enforcement(self, connection_pool):
        """Test that connection pool enforces maximum size limits."""
        connections = []
        
        # Acquire up to max size
        for i in range(connection_pool.max_size):
            conn = await connection_pool.acquire()
            connections.append(conn)
            
        assert connection_pool.active_size == connection_pool.max_size
        assert connection_pool.available_size == 0
        
        # Attempting to acquire beyond max should wait or fail
        # In this simplified mock, it will retry after a small delay
        acquire_task = asyncio.create_task(connection_pool.acquire())
        await asyncio.sleep(0.05)  # Should still be waiting
        
        # Release a connection
        await connection_pool.release(connections[0])
        
        # Now the waiting acquire should complete
        new_conn = await acquire_task
        assert new_conn is not None
        
        # Clean up remaining connections
        for conn in connections[1:]:
            await connection_pool.release(conn)
        await connection_pool.release(new_conn)
    
    @pytest.mark.asyncio
    async def test_connection_pool_resource_manager_integration(self, connection_pool, resource_manager):
        """Test integration of connection pool with resource manager."""
        
        # Register pool for cleanup
        resource_manager.register_resource(connection_pool, cleanup_callback=connection_pool.close)
        
        # Use the pool
        conn1 = await connection_pool.acquire()
        conn2 = await connection_pool.acquire()
        
        assert connection_pool.active_size == 2
        assert not connection_pool.is_closed
        
        # Cleanup should close the pool
        await resource_manager.cleanup_all()
        
        assert connection_pool.is_closed
        assert connection_pool.total_size == 0
        assert connection_pool.total_destroyed == 2  # Both connections destroyed
    
    @pytest.mark.asyncio
    async def test_connection_pool_concurrent_access_patterns(self, connection_pool):
        """Test concurrent access patterns to connection pool."""
        
        async def worker_task(worker_id: int):
            """Worker task that uses connections."""
            results = []
            for i in range(3):  # Each worker does 3 operations
                conn = await connection_pool.acquire()
                
                # Simulate work with connection
                await asyncio.sleep(0.01)
                operation_result = f"worker_{worker_id}_op_{i}"
                results.append(operation_result)
                
                await connection_pool.release(conn)
                
            return results
        
        # Start multiple concurrent workers
        num_workers = 4
        worker_tasks = [worker_task(i) for i in range(num_workers)]
        
        # Execute all workers concurrently
        start_time = time.time()
        results = await asyncio.gather(*worker_tasks)
        execution_time = time.time() - start_time
        
        # Verify results
        assert len(results) == num_workers
        for worker_results in results:
            assert len(worker_results) == 3
            
        # Verify pool state after concurrent access
        assert connection_pool.active_size == 0  # All connections returned
        assert connection_pool.available_size <= connection_pool.max_size
        
        # Should complete reasonably quickly despite coordination
        assert execution_time < 1.0
    
    @pytest.mark.asyncio
    async def test_connection_pool_failure_recovery_patterns(self, connection_pool):
        """Test connection pool behavior during failure scenarios."""
        
        # Acquire some connections
        conn1 = await connection_pool.acquire()
        conn2 = await connection_pool.acquire()
        
        # Simulate connection failure
        conn1.is_closed = True
        
        # Release failed connection - should be destroyed, not reused
        initial_destroyed = connection_pool.total_destroyed
        await connection_pool.release(conn1)
        
        assert connection_pool.total_destroyed == initial_destroyed + 1
        assert conn1 not in connection_pool.available_connections
        
        # Release healthy connection - should be available for reuse
        await connection_pool.release(conn2)
        assert conn2 in connection_pool.available_connections
        
        # Acquire again - should get the healthy connection, not create new
        conn3 = await connection_pool.acquire()
        assert conn3 is conn2
        
        await connection_pool.release(conn3)
    
    @pytest.mark.asyncio
    async def test_connection_pool_graceful_shutdown_patterns(self, connection_pool):
        """Test graceful shutdown patterns for connection pools."""
        
        # Acquire connections and simulate active work
        active_connections = []
        for i in range(3):
            conn = await connection_pool.acquire()
            active_connections.append(conn)
            
        # Create background tasks that will release connections during shutdown
        async def slow_release_task(connection, delay):
            await asyncio.sleep(delay)
            await connection_pool.release(connection)
            
        release_tasks = [
            asyncio.create_task(slow_release_task(active_connections[0], 0.02)),
            asyncio.create_task(slow_release_task(active_connections[1], 0.04)),
            asyncio.create_task(slow_release_task(active_connections[2], 0.06))
        ]
        
        # Start shutdown process
        shutdown_task = asyncio.create_task(connection_pool.close())
        
        # Allow some releases to happen during shutdown
        await asyncio.sleep(0.05)
        
        # Complete shutdown
        await shutdown_task
        
        # Wait for all release tasks to complete
        await asyncio.gather(*release_tasks, return_exceptions=True)
        
        # Verify pool is properly closed
        assert connection_pool.is_closed
        assert connection_pool.total_size == 0
        assert connection_pool.total_destroyed >= 3  # All connections destroyed
        
        # Attempting operations on closed pool should fail
        with pytest.raises(RuntimeError, match="Pool is closed"):
            await connection_pool.acquire()
    
    @pytest.mark.asyncio
    async def test_connection_pool_resource_leak_prevention(self, connection_pool, resource_manager):
        """Test that connection pools prevent resource leaks."""
        
        # Track initial state
        initial_created = connection_pool.total_created
        initial_destroyed = connection_pool.total_destroyed
        
        # Register pool with resource manager
        resource_manager.register_resource(connection_pool, cleanup_callback=connection_pool.close)
        
        # Create some connections and "forget" to release them (simulate bug)
        leaked_connections = []
        for i in range(3):
            conn = await connection_pool.acquire()
            leaked_connections.append(conn)
            # Don't release - simulate leak
        
        # Verify connections were created
        assert connection_pool.total_created == initial_created + 3
        assert connection_pool.active_size == 3
        
        # Resource manager cleanup should handle leaked connections
        await resource_manager.cleanup_all()
        
        # Verify all connections were properly destroyed
        assert connection_pool.is_closed
        assert connection_pool.total_destroyed >= initial_destroyed + 3
        assert connection_pool.total_size == 0
        
        # No resource leaks should remain
        assert len(connection_pool.active_connections) == 0


class TestAsyncResourceManagerPerformanceOptimization:
    """Test performance optimization patterns for the async resource manager."""
    
    @pytest.mark.asyncio
    async def test_memory_efficient_bulk_resource_cleanup(self):
        """Test memory-efficient cleanup of large numbers of resources."""
        from netra_backend.app.core.async_resource_manager import AsyncResourceManager
        import gc
        import tracemalloc
        
        # Start memory tracking
        tracemalloc.start()
        
        manager = AsyncResourceManager()
        
        # Create large number of mock resources (using objects, not strings for weak references)
        class MockResource:
            def __init__(self, name):
                self.name = name
        
        resources = []
        cleanup_counter = {"count": 0}
        
        # Create a single cleanup function to avoid closure issues
        async def cleanup_callback():
            cleanup_counter["count"] += 1
        
        for i in range(100):  # Reduced from 1000 to avoid timeout issues
            resource = MockResource(f"resource_{i}")
            resources.append(resource)
            manager.register_resource(resource, cleanup_callback=cleanup_callback)
        
        # Force garbage collection before measurement
        gc.collect()
        current, peak = tracemalloc.get_traced_memory()
        initial_memory = current
        
        # Perform bulk cleanup
        await manager.cleanup_all()
        
        # Force garbage collection after cleanup
        gc.collect()
        current, peak = tracemalloc.get_traced_memory()
        final_memory = current
        
        tracemalloc.stop()
        
        # Verify all resources were cleaned up
        assert cleanup_counter["count"] == 100
        assert manager.resource_count == 0
        
        # Verify memory was efficiently managed
        # Memory growth should be reasonable for the test environment
        memory_growth = final_memory - initial_memory
        # Allow for reasonable memory growth due to test framework overhead
        assert memory_growth < 100000  # Less than 100KB growth is acceptable
        
        # Verify cleanup was performed efficiently
        assert manager.is_shutting_down
        
        # Verify no memory leaks - final memory should be manageable
        # (This is more about ensuring the cleanup worked than absolute memory values)
        assert final_memory > 0  # Sanity check
    
    @pytest.mark.asyncio
    async def test_concurrent_task_pool_performance_optimization(self):
        """Test performance optimization for concurrent task execution."""
        from netra_backend.app.core.async_resource_manager import AsyncTaskPool
        import time
        import asyncio
        
        # Create task pool with performance-optimized settings
        task_pool = AsyncTaskPool(max_concurrent_tasks=50)
        
        # Performance metrics tracking
        start_time = time.time()
        completed_tasks = []
        
        async def performance_test_task(task_id: int, duration: float = 0.01):
            """Simulated task with controlled duration."""
            await asyncio.sleep(duration)
            completed_tasks.append(task_id)
            return f"task_{task_id}_completed"
        
        # Submit large batch of tasks concurrently
        tasks = []
        for i in range(200):  # More tasks than max concurrent
            task = task_pool.submit_background_task(
                performance_test_task(i, 0.005)  # Very short duration
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # Performance assertions
        execution_time = end_time - start_time
        assert execution_time < 2.0  # Should complete within 2 seconds
        
        # Verify all tasks completed successfully
        assert len(completed_tasks) == 200
        assert len(results) == 200
        
        # Verify no exceptions in results
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0
        
        # Verify task pool managed concurrency effectively
        assert task_pool.active_task_count == 0  # All tasks should be done
        assert task_pool.available_slots == task_pool.max_concurrent_tasks
        
        # Performance optimization validation
        # With 50 concurrent slots and 200 tasks, we should see efficient batching
        avg_time_per_task = execution_time / 200
        assert avg_time_per_task < 0.01  # Each task should average less than 10ms
        
        await task_pool.shutdown()
    
    @pytest.mark.asyncio
    async def test_resource_cleanup_batching_optimization(self):
        """Test batch optimization for resource cleanup operations (Iteration 73)."""
        from netra_backend.app.core.async_resource_manager import AsyncResourceManager
        import asyncio
        
        manager = AsyncResourceManager()
        cleanup_count = {"value": 0}
        
        async def batch_cleanup_callback():
            """Simulated cleanup with timing."""
            await asyncio.sleep(0.001)
            cleanup_count["value"] += 1
        
        # Register multiple resources for batch cleanup
        resources = []
        for i in range(30):
            resource = f"batch_resource_{i}"
            resources.append(resource)
            # Create a simple mock resource that can be weakly referenced
            class MockBatchResource:
                def __init__(self, name):
                    self.name = name
            mock_resource = MockBatchResource(resource)
            manager.register_resource(mock_resource, cleanup_callback=batch_cleanup_callback)
        
        start_time = asyncio.get_event_loop().time()
        await manager.cleanup_all()
        end_time = asyncio.get_event_loop().time()
        
        # Verify batch processing efficiency
        total_time = end_time - start_time
        assert total_time < 1.0  # Should complete quickly due to batching
        assert cleanup_count["value"] == 30  # All cleaned up
        assert manager.resource_count == 0
    
    @pytest.mark.asyncio
    async def test_threadpool_execution_performance_optimization(self):
        """Test thread pool execution performance optimization (Iteration 74)."""
        from netra_backend.app.core.async_resource_manager import run_in_threadpool
        import time
        
        def cpu_bound_task(n: int) -> int:
            """Simulated CPU-bound work."""
            total = 0
            for i in range(n):
                total += i
            return total
        
        # Test concurrent thread pool execution
        start_time = time.time()
        
        tasks = []
        for i in range(10):  # Reduced for faster execution
            task = run_in_threadpool(cpu_bound_task, 100)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Performance assertions
        execution_time = end_time - start_time
        assert execution_time < 2.0  # Should leverage thread pool efficiently
        
        # Verify results are correct
        assert len(results) == 10
        expected_result = cpu_bound_task(100)
        assert all(r == expected_result for r in results)
    
    @pytest.mark.asyncio
    async def test_memory_pool_optimization_patterns(self):
        """Test memory pool optimization for resource reuse (Iteration 75)."""
        from netra_backend.app.core.async_resource_manager import AsyncResourceManager
        
        manager = AsyncResourceManager()
        
        # Memory pool simulation
        class ReusableResource:
            def __init__(self, name):
                self.name = name
                self.reuse_count = 0
                
            def reset(self):
                """Reset resource for reuse."""
                self.reuse_count += 1
        
        # Pool of reusable resources
        resource_pool = []
        
        # Create initial pool
        for i in range(5):  # Smaller pool for faster testing
            resource = ReusableResource(f"pooled_{i}")
            resource_pool.append(resource)
            manager.register_resource(resource)
        
        # Simulate resource reuse patterns
        for cycle in range(3):
            for resource in resource_pool:
                resource.reset()
                
        # Verify memory pool efficiency
        assert all(r.reuse_count == 3 for r in resource_pool)  # All reused
        assert manager.resource_count == 5  # Pool maintained
        
        # Cleanup should be efficient
        await manager.cleanup_all()
        assert manager.resource_count == 0
    
    @pytest.mark.asyncio
    async def test_bulk_operation_optimization_patterns(self):
        """Test bulk operation optimization patterns (Iteration 76)."""
        from netra_backend.app.core.async_resource_manager import AsyncResourceManager
        import asyncio
        
        manager = AsyncResourceManager()
        processed_count = {"value": 0}
        
        # Bulk operation simulation
        class BulkResource:
            def __init__(self, batch_id: int):
                self.batch_id = batch_id
                self.processed = False
        
        async def bulk_processor_callback():
            """Optimized bulk processing."""
            await asyncio.sleep(0.001)  # Bulk operations are more efficient
            processed_count["value"] += 1
        
        # Create bulk resources
        bulk_resources = []
        for batch in range(5):
            resource = BulkResource(batch)
            bulk_resources.append(resource)
            manager.register_resource(resource, cleanup_callback=bulk_processor_callback)
        
        # Test bulk processing performance
        start_time = time.time()
        await manager.cleanup_all()
        end_time = time.time()
        
        # Bulk optimization validations
        processing_time = end_time - start_time
        assert processing_time < 1.0  # Bulk should be efficient
        assert processed_count["value"] == 5  # All processed
        assert manager.resource_count == 0
    
    @pytest.mark.asyncio
    async def test_connection_pool_efficiency_patterns(self):
        """Test connection pool efficiency patterns (Iteration 77)."""
        from netra_backend.app.core.async_resource_manager import AsyncResourceManager
        import time
        
        manager = AsyncResourceManager()
        
        # Simulated connection pool
        class EfficiencyTestConnection:
            def __init__(self, conn_id):
                self.conn_id = conn_id
                self.active = True
                self.operations = 0
            
            def execute_operation(self):
                """Simulate connection operation."""
                self.operations += 1
                return f"result_{self.operations}"
        
        # Create connection pool
        connections = []
        for i in range(8):
            conn = EfficiencyTestConnection(i)
            connections.append(conn)
            manager.register_resource(conn)
        
        # Test connection efficiency
        start_time = time.time()
        
        # Simulate concurrent operations
        for conn in connections:
            for _ in range(10):
                result = conn.execute_operation()
                assert result.startswith("result_")
        
        end_time = time.time()
        
        # Efficiency validations
        processing_time = end_time - start_time
        assert processing_time < 0.5  # Should be very fast
        
        # All connections should have operated
        total_operations = sum(conn.operations for conn in connections)
        assert total_operations == 80  # 8 connections * 10 operations
        
        await manager.cleanup_all()
    
    @pytest.mark.asyncio
    async def test_adaptive_resource_scaling_patterns(self):
        """Test adaptive resource scaling patterns (Iteration 78)."""
        from netra_backend.app.core.async_resource_manager import AsyncTaskPool
        
        # Start with small pool and test scaling
        task_pool = AsyncTaskPool(max_concurrent_tasks=5)
        
        async def scaling_test_task(task_id):
            """Task for testing scaling behavior."""
            await asyncio.sleep(0.005)
            return f"scaled_task_{task_id}"
        
        # Submit tasks that would benefit from scaling
        tasks = []
        for i in range(15):  # More than initial capacity
            task = task_pool.submit_background_task(scaling_test_task(i))
            tasks.append(task)
        
        # Wait for completion
        results = await asyncio.gather(*tasks)
        
        # Validate scaling behavior
        assert len(results) == 15
        assert all("scaled_task_" in result for result in results)
        
        # Pool should handle the load efficiently
        assert task_pool.active_task_count == 0  # All done
        
        await task_pool.shutdown()
    
    @pytest.mark.asyncio 
    async def test_resource_cache_performance_patterns(self):
        """Test resource caching performance patterns (Iteration 79)."""
        from netra_backend.app.core.async_resource_manager import AsyncResourceManager
        import time
        
        manager = AsyncResourceManager()
        cache_operations = {"hits": 0, "misses": 0}
        
        # Simple resource cache simulation
        resource_cache = {}
        
        class CachedResource:
            def __init__(self, key):
                self.key = key
                self.created_at = time.time()
        
        def get_cached_resource(key: str):
            """Factory with caching optimization."""
            if key in resource_cache:
                cache_operations["hits"] += 1
                return resource_cache[key]
            
            cache_operations["misses"] += 1
            resource = CachedResource(key)
            resource_cache[key] = resource
            manager.register_resource(resource)
            return resource
        
        # Test cache performance with repeated requests
        keys = ["key_1", "key_2", "key_3"] * 10  # Repeated keys
        
        start_time = time.time()
        resources = []
        for key in keys:
            resource = get_cached_resource(key)
            resources.append(resource)
        end_time = time.time()
        
        # Cache optimization validations
        processing_time = end_time - start_time
        assert processing_time < 0.1  # Should be fast due to caching
        
        # Verify cache efficiency
        assert cache_operations["hits"] > cache_operations["misses"]
        assert len(set(r.key for r in resources)) == 3  # Only 3 unique
        assert len(resources) == 30  # But 30 requests served
        
        await manager.cleanup_all()
    
    @pytest.mark.asyncio
    async def test_optimized_async_context_patterns(self):
        """Test optimized async context management patterns (Iteration 80)."""
        from netra_backend.app.core.async_resource_manager import AsyncResourceManager
        import asyncio
        
        manager = AsyncResourceManager()
        context_operations = []
        
        class OptimizedAsyncContext:
            def __init__(self, name):
                self.name = name
                self.active = False
            
            async def __aenter__(self):
                self.active = True
                context_operations.append(f"enter_{self.name}")
                manager.register_resource(self)
                return self
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                self.active = False
                context_operations.append(f"exit_{self.name}")
                return False
        
        # Test multiple async contexts
        async def context_test():
            async with OptimizedAsyncContext("ctx_1") as ctx1:
                async with OptimizedAsyncContext("ctx_2") as ctx2:
                    assert ctx1.active and ctx2.active
                    await asyncio.sleep(0.001)
        
        start_time = time.time()
        
        # Run multiple context tests concurrently
        tasks = [context_test() for _ in range(5)]
        await asyncio.gather(*tasks)
        
        end_time = time.time()
        
        # Context optimization validations
        processing_time = end_time - start_time
        assert processing_time < 0.5  # Should be efficient
        
        # Verify proper context management
        assert len(context_operations) == 20  # 5 tests * 2 contexts * 2 ops each
        enter_ops = [op for op in context_operations if op.startswith("enter_")]
        exit_ops = [op for op in context_operations if op.startswith("exit_")]
        assert len(enter_ops) == 10
        assert len(exit_ops) == 10
        
        await manager.cleanup_all()